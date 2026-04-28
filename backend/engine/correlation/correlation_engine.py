"""
correlation_engine.py — SecuriSphere Correlation Engine

Consumes normalised security events from the ``security_events`` Redis
pub/sub channel, applies 9 heuristic correlation rules, maintains per-IP
risk scores with time-based decay, reconstructs kill chains (service
traversal paths), persists kill chains to PostgreSQL, and exposes a Flask
health/stats API on port 5070.

Enhancements over baseline
--------------------------
- Service-name aware correlation: events carry ``source_service_name``
  when enriched by the topology collector.
- Kill chain reconstruction via ``engine.kill_chain.reconstructor``:
  every incident gets ``first_event_at``, ``detected_at``, ``mttd_seconds``,
  ``service_path``, and ``kill_chain_steps``.
- Complete MITRE ATT&CK for Containers mapping (T1046, T1595, T1021,
  T1078, T1110, T1190, T1003, T1071, T1083, T1530, T1110.004, T1048).
- Discord rich-embed alerting with retry / rate-limit logic.
- ``/api/mitre-mapping`` endpoint returning technique frequency map.
"""

import os
import sys
import time
import json
import redis
import requests
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from uuid import uuid4
from flask import Flask, jsonify

# Kill-chain reconstructor (sibling package)
# Support both Docker layout (/app/kill_chain/) and local layout (../kill_chain/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from kill_chain.reconstructor import reconstruct, persist as persist_kc, ensure_schema, fetch_mttd_report
    _KC_AVAILABLE = True
except Exception as _kc_err:
    logging.warning("Kill chain module unavailable: %s", _kc_err)
    _KC_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("CorrelationEngine")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REDIS_HOST         = os.getenv("REDIS_HOST", "redis")
REDIS_PORT         = int(os.getenv("REDIS_PORT", 6379))
CORRELATION_WINDOW = int(os.getenv("CORRELATION_WINDOW", 900))   # 15 min
RISK_DECAY_RATE    = int(os.getenv("RISK_DECAY_RATE", 5))
RISK_DECAY_INTERVAL= int(os.getenv("RISK_DECAY_INTERVAL", 60))

# Discord rate-limit: max 1 alert per incident_type per this many seconds
DISCORD_RATE_LIMIT = 60
# Max retries for Discord webhook delivery
DISCORD_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Topology enrichment (module-level, called per event before correlation)
# ---------------------------------------------------------------------------

_topology_cache = {}  # service_name → {"data": ..., "ts": float}
_TOPOLOGY_CACHE_TTL = 30  # seconds


def enrich_event(event):
    """Enrich *event* with topology metadata from the topology-collector.

    - Tries GET http://topology-collector:5080/topology/service/{name} (2 s timeout).
    - Caches per service name for 30 s.
    - On failure uses cache; if no cache leaves the field unchanged.
    - Tags ``enrichment_source``: ``"live"`` | ``"cached"`` | ``"none"``.
    """
    svc = event.get("source_service_name")
    if not svc:
        event["enrichment_source"] = "none"
        return event

    now = time.time()

    # Check cache freshness
    cached = _topology_cache.get(svc)
    cache_fresh = cached and (now - cached["ts"]) < _TOPOLOGY_CACHE_TTL

    # Attempt live fetch
    try:
        resp = requests.get(
            f"http://topology-collector:5080/topology/service/{svc}",
            timeout=2,
        )
        resp.raise_for_status()
        data = resp.json()
        _topology_cache[svc] = {"data": data, "ts": now}
        event["topology_info"] = data
        event["enrichment_source"] = "live"
    except requests.exceptions.RequestException:
        if cached:
            age_seconds = now - cached["ts"]
            if age_seconds > 300:
                event["enrichment_source"] = "none"
                logger.warning("Topology cache expired (%.0fs old) for service: %s — proceeding without enrichment", age_seconds, svc)
            else:
                event["topology_info"] = cached["data"]
                event["enrichment_source"] = "cached"
        else:
            event["enrichment_source"] = "none"

    return event


class CorrelationEngine:
    # -----------------------------------------------------------------------
    # Initialisation
    # -----------------------------------------------------------------------

    def __init__(self) -> None:
        self.connect_redis()

        # Initialise PostgreSQL kill-chain schema if module available
        if _KC_AVAILABLE:
            try:
                ensure_schema()
            except Exception as exc:
                logger.warning("Could not ensure kill_chain schema: %s", exc)

        # Event buffer: all events within the correlation window
        self.event_buffer: list = []
        self.buffer_lock  = threading.Lock()

        # Per-service (or fallback per-IP) risk state.
        # Keys are source_service_name when available, else source_ip.
        self.risk_scores = defaultdict(lambda: {
            "score": 0,
            "events": [],
            "layers_involved": set(),
            "last_update": None,
            "peak_score": 0,
            "event_count": 0,
            "last_event_type": None,
            "threat_level": "normal",
            "entity_type": "ip",
            "source_ip": None,
        })

        self.recent_incidents: list = []
        self.incident_cooldowns: dict = {}
        self.cooldown_duration = timedelta(minutes=5)

        # Discord per-type rate limiting
        self._discord_last_sent: dict = {}   # incident_type → datetime

        # Ordered rule list (run against every new event)
        self.rules = [
            self.rule_recon_to_exploit,
            self.rule_credential_compromise,
            self.rule_full_kill_chain,
            self.rule_api_auth_combined,
            self.rule_distributed_attack,
            self.rule_data_exfiltration,
            self.rule_persistent_threat,
            self.rule_brute_force_attempt,
            self.rule_critical_exploit_attempt,
            # Browser-layer rules (Phase 2) — all gated on source_layer=='browser-agent'
            self.rule_browser_sqli,
            self.rule_browser_path_traversal,
            self.rule_browser_brute_force,
            self.rule_browser_recon_scan,
            self.rule_browser_bruteforce_to_exfil,
            self.rule_browser_recon_to_privesc,
            self.rule_browser_multi_hop,
        ]

        self.stats = {
            "events_processed": 0,
            "incidents_created": 0,
            "rules_triggered": defaultdict(int),
            "mitre_hits": defaultdict(int),   # technique → frequency
            "start_time": datetime.now(),
        }

        # Flask health/stats API
        self.app = Flask(__name__)
        self._setup_routes()

    # -----------------------------------------------------------------------
    # Redis connection
    # -----------------------------------------------------------------------

    def connect_redis(self) -> None:
        retry = 0
        while True:
            try:
                self.redis = redis.Redis(
                    host=REDIS_HOST, port=REDIS_PORT, decode_responses=True
                )
                self.redis.ping()
                self.pubsub = self.redis.pubsub()
                self.pubsub.subscribe("security_events")
                logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
                return
            except redis.ConnectionError:
                retry += 1
                logger.warning("Redis not ready, retry %d …", retry)
                time.sleep(2)

    # -----------------------------------------------------------------------
    # Risk scoring
    # -----------------------------------------------------------------------

    _SEVERITY_POINTS = {"low": 10, "medium": 25, "high": 50, "critical": 100}

    def update_risk_score(self, service_key: str, event: dict,
                           entity_type: str = "ip") -> None:
        if not service_key:
            return

        severity  = event.get("severity", {}).get("level", "low")
        points    = self._SEVERITY_POINTS.get(severity, 10)
        data      = self.risk_scores[service_key]
        layer     = event.get("source_layer")
        src_ip    = event.get("source_entity", {}).get("ip") or event.get("source_ip")

        if layer:
            data["layers_involved"].add(layer)
        if len(data["layers_involved"]) > 1:
            points = int(points * 1.5)   # cross-layer bonus

        data["score"]           += points
        data["peak_score"]       = max(data["peak_score"], data["score"])
        data["event_count"]     += 1
        data["last_event_type"]  = event.get("event_type")
        data["last_update"]      = datetime.now().isoformat()
        data["threat_level"]     = self._threat_level(data["score"])
        data["entity_type"]      = entity_type
        if src_ip:
            data["source_ip"] = src_ip
        data["events"].append({
            "event_id":  event.get("event_id"),
            "type":      event.get("event_type"),
            "layer":     layer,
            "severity":  severity,
            "points":    points,
            "timestamp": event.get("timestamp"),
        })
        data["events"] = data["events"][-50:]

        self._publish_risk(service_key, data, points)

    @staticmethod
    def _threat_level(score: int) -> str:
        if score > 150: return "critical"
        if score > 70:  return "threatening"
        if score > 30:  return "suspicious"
        return "normal"

    def _publish_risk(self, service_key: str, data: dict, points: int) -> None:
        entity_type = data.get("entity_type", "ip")
        payload = {
            "entity":          service_key,
            "entity_type":     entity_type,
            "entity_ip":       data.get("source_ip") if entity_type == "service" else service_key,
            "source_ip":       data.get("source_ip"),
            "current_score":   data["score"],
            "peak_score":      data["peak_score"],
            "threat_level":    data["threat_level"],
            "layers_involved": list(data["layers_involved"]),
            "event_count":     data["event_count"],
            "last_event_type": data["last_event_type"],
            "last_update":     data["last_update"],
            "points_added":    points,
        }
        try:
            self.redis.publish("risk_scores", json.dumps(payload))
            self.redis.hset("risk_scores_current", service_key, json.dumps(payload))
        except Exception as exc:
            logger.error("Failed to publish risk score: %s", exc)

        colors = {
            "normal":     "\033[92m",
            "suspicious": "\033[93m",
            "threatening":"\033[91m",
            "critical":   "\033[95m",
        }
        c = colors.get(data["threat_level"], "\033[0m")
        logger.info(
            "%s[RISK] %s (%s): %d (%s) | +%d pts\033[0m",
            c, service_key, entity_type, data["score"], data["threat_level"], points,
        )

    def decay_risk_scores_loop(self) -> None:
        while True:
            time.sleep(RISK_DECAY_INTERVAL)
            try:
                to_remove = []
                for key, data in self.risk_scores.items():
                    if data["score"] > 0:
                        data["score"] = max(0, data["score"] - RISK_DECAY_RATE)
                        data["threat_level"] = self._threat_level(data["score"])
                        self._publish_risk(key, data, -RISK_DECAY_RATE)
                    if data["score"] == 0:
                        last_up = (
                            datetime.fromisoformat(data["last_update"])
                            if data["last_update"] else datetime.min
                        )
                        if (datetime.now() - last_up).total_seconds() > 1800:
                            to_remove.append(key)
                for key in to_remove:
                    del self.risk_scores[key]
                    self.redis.hdel("risk_scores_current", key)
            except Exception as exc:
                logger.error("Decay loop error: %s", exc)

    # -----------------------------------------------------------------------
    # Incident helpers
    # -----------------------------------------------------------------------

    def _check_cooldown(self, rule: str, key: str) -> bool:
        ck = f"{rule}:{key}"
        if ck in self.incident_cooldowns:
            return datetime.now() < self.incident_cooldowns[ck] + self.cooldown_duration
        return False

    def _set_cooldown(self, rule: str, key: str) -> None:
        self.incident_cooldowns[f"{rule}:{key}"] = datetime.now()

    def create_incident(
        self,
        incident_type: str,
        title: str,
        description: str,
        severity: str,
        confidence: float,
        source_ip: str,
        correlated_events: list,
        layers: list,
        mitre: list,
        actions: list,
        extra: dict = None,
    ) -> dict:
        """Build an incident dict and immediately reconstruct the kill chain."""
        timestamps = [e.get("timestamp") for e in correlated_events if e.get("timestamp")]
        time_span  = 0
        if timestamps:
            times     = [datetime.fromisoformat(t.replace("Z", "")) for t in timestamps]
            time_span = (max(times) - min(times)).total_seconds()

        risk_key = next(
            (e.get("source_service_name") for e in correlated_events
             if e.get("source_service_name")),
            None,
        ) or source_ip
        current_risk = self.risk_scores[risk_key]["score"] if risk_key in self.risk_scores else 0

        incident = {
            "incident_id":            str(uuid4()),
            "incident_type":          incident_type,
            "title":                  title,
            "description":            description,
            "severity":               severity,
            "confidence":             confidence,
            "source_ip":              source_ip,
            "correlated_events":      [e.get("event_id") for e in correlated_events],
            "correlated_event_count": len(correlated_events),
            "layers_involved":        list(set(layers)),
            "mitre_techniques":       mitre,
            "recommended_actions":    actions,
            "risk_score_at_time":     current_risk,
            "time_span_seconds":      int(time_span),
            "timestamp":              datetime.now().isoformat(),
        }

        if extra:
            incident.update(extra)

        # --- Kill chain reconstruction ---
        if _KC_AVAILABLE:
            try:
                incident = reconstruct(incident, correlated_events)
            except Exception as exc:
                logger.warning("Kill chain reconstruction failed: %s", exc)

        # Track MITRE technique frequency
        for technique in mitre:
            if technique:
                self.stats["mitre_hits"][technique] += 1

        return incident

    def publish_incident(self, incident: dict) -> None:
        js = json.dumps(incident)
        try:
            self.redis.publish("correlated_incidents", js)
            self.redis.lpush("incidents", js)
            self.redis.ltrim("incidents", 0, 99)
            # Fast-path queue for the backend WS layer — decouples delivery
            # from pub/sub subscriber liveness.
            self.redis.lpush("ws_push_queue", js)
            self.redis.ltrim("ws_push_queue", 0, 199)
        except Exception as exc:
            logger.error("Failed to publish incident: %s", exc)

        self.recent_incidents.append(incident)
        if len(self.recent_incidents) > 50:
            self.recent_incidents.pop(0)

        self.stats["incidents_created"]                       += 1
        self.stats["rules_triggered"][incident["incident_type"]] += 1

        # Persist to PostgreSQL — kill_chains table (full service path + steps)
        if _KC_AVAILABLE:
            try:
                persist_kc(incident)
            except Exception as exc:
                logger.warning("PostgreSQL kill_chain persist failed: %s", exc)

            # Kick off AI narration in the background so the main event loop
            # is never blocked by the LLM call.
            try:
                t = threading.Thread(
                    target=self._narrate_and_save,
                    args=(incident,),
                    daemon=True,
                )
                t.start()
            except Exception as exc:
                logger.warning("Failed to spawn narration thread: %s", exc)

        # Persist to PostgreSQL — correlated_incidents table (incident summary)
        self._persist_incident_pg(incident)

        # Terminal banner
        print("\033[91m")
        print("════════════════════════════════════════════")
        print(f"[INCIDENT] [{incident['severity'].upper()}] {incident['title']}")
        print(f"  Type:     {incident['incident_type']}")
        print(f"  Source:   {incident['source_ip']}")
        print(f"  MITRE:    {incident.get('mitre_techniques', [])}")
        if incident.get("service_path"):
            print(f"  Path:     {' → '.join(incident['service_path'])}")
        if incident.get("mttd_seconds") is not None:
            print(f"  MTTD:     {incident['mttd_seconds']:.2f}s")
        print("════════════════════════════════════════════")
        print("\033[0m")

        if incident.get("severity") in ("high", "critical"):
            # Run in a daemon thread so the up-to-8s narrative poll inside
            # _send_discord_alert never blocks the main event loop.
            try:
                threading.Thread(
                    target=self._send_discord_alert,
                    args=(incident,),
                    daemon=True,
                ).start()
            except Exception as exc:
                logger.warning("Failed to spawn Discord alert thread: %s", exc)

    # -----------------------------------------------------------------------
    # Discord alerting (with retry + rate-limit)
    # -----------------------------------------------------------------------

    _DISCORD_COLORS = {
        "critical": 15548997,   # Red
        "high":     15105570,   # Orange
        "medium":   16776960,   # Yellow
        "low":      5763719,    # Green
    }

    def _persist_incident_pg(self, incident: dict) -> None:
        """Write incident summary to PostgreSQL correlated_incidents table."""
        try:
            import psycopg2
            conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO correlated_incidents (
                            incident_id, incident_type, title, description, severity,
                            confidence, source_ip, target_username,
                            correlated_event_ids, layers_involved, mitre_techniques,
                            recommended_actions, risk_score_at_time, time_span_seconds
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        ) ON CONFLICT (incident_id) DO NOTHING
                        """,
                        (
                            incident.get("incident_id"),
                            incident.get("incident_type"),
                            incident.get("title"),
                            incident.get("description"),
                            incident.get("severity"),
                            incident.get("confidence"),
                            incident.get("source_ip"),
                            incident.get("target_username"),
                            incident.get("correlated_events", []),
                            incident.get("layers_involved", []),
                            incident.get("mitre_techniques", []),
                            incident.get("recommended_actions", []),
                            incident.get("risk_score_at_time", 0),
                            incident.get("time_span_seconds", 0),
                        ),
                    )
            conn.close()
        except Exception as exc:
            # DB unavailability is non-fatal; Redis is the primary store
            logger.debug("correlated_incidents PG persist skipped: %s", exc)

    def _poll_narrative(self, incident_id, timeout: float = 8.0,
                        interval: float = 1.5):
        """
        Poll kill_chains.narrative for up to `timeout` seconds, waiting for
        the background narration thread to finish. Returns the narrative
        string if found, or None on timeout / any error.
        """
        if not incident_id:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                import psycopg2
                conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
                    host=os.getenv("POSTGRES_HOST", "database"),
                    port=int(os.getenv("POSTGRES_PORT", 5432)),
                    dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                    user=os.getenv("POSTGRES_USER", "securisphere_user"),
                    password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
                )
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT narrative FROM kill_chains WHERE incident_id = %s LIMIT 1",
                            (incident_id,),
                        )
                        row = cur.fetchone()
                finally:
                    conn.close()
                if row and row[0]:
                    return row[0]
            except Exception as exc:
                logger.debug("Narrative poll error: %s", exc)
            time.sleep(interval)
        return None

    def _narrate_and_save(self, incident: dict) -> None:
        """
        Background task: generate an AI narrative for a kill chain and
        persist it to the kill_chains row. Never raises.
        """
        try:
            from narration.narrator import generate_narrative
            from kill_chain.reconstructor import update_narrative
        except Exception as exc:
            logger.debug("Narration modules unavailable: %s", exc)
            return

        try:
            narrative = generate_narrative(incident)
            if not narrative:
                return
            update_narrative(incident.get("incident_id"), narrative)
        except Exception as exc:
            logger.warning("Narration task failed for %s: %s",
                           incident.get("incident_id"), exc)

    def _send_discord_alert(self, incident: dict) -> None:
        """Send a rich-embed Discord notification with exponential-backoff retry."""
        try:
            webhook_url = self.redis.get("config:discord_webhook")
            if not webhook_url:
                return
        except Exception:
            return

        # Per-type rate limit: skip if same type alerted within DISCORD_RATE_LIMIT seconds
        now = datetime.now()
        last = self._discord_last_sent.get(incident["incident_type"])
        if last and (now - last).total_seconds() < DISCORD_RATE_LIMIT:
            return
        self._discord_last_sent[incident["incident_type"]] = now

        color     = self._DISCORD_COLORS.get(incident.get("severity", "low"), 15548997)
        mitre_str = ", ".join(incident.get("mitre_techniques", [])) or "N/A"
        path_str  = " → ".join(incident.get("service_path", [])) or "N/A"
        actions   = "\n".join(
            f"• {a}" for a in (incident.get("recommended_actions") or [])
        ) or "N/A"

        fields = [
            {"name": "Severity",          "value": incident.get("severity", "?").upper(), "inline": True},
            {"name": "Source IP",          "value": incident.get("source_ip", "?"),        "inline": True},
            {"name": "Type",               "value": incident.get("incident_type", "?"),    "inline": True},
            {"name": "MITRE Techniques",   "value": mitre_str,                             "inline": False},
            {"name": "Service Attack Path","value": path_str,                              "inline": False},
            {"name": "MTTD",               "value": f"{incident.get('mttd_seconds', 'N/A')}s", "inline": True},
            {"name": "Recommended Actions","value": actions,                               "inline": False},
        ]

        # Poll kill_chains.narrative up to 8s for the AI narration that is
        # being generated in a background thread. If it shows up in time,
        # attach it to the embed; otherwise send the alert without it.
        narrative = self._poll_narrative(incident.get("incident_id"), timeout=8.0, interval=1.5)
        if narrative:
            fields.append({
                "name":   "🤖 AI Analysis",
                "value":  narrative[:1024],
                "inline": False,
            })

        payload = {
            "embeds": [{
                "title":       f"🚨 {incident.get('title', 'Security Incident')}",
                "description": incident.get("description", "No details"),
                "color":       color,
                "fields":      fields,
                "footer": {
                    "text": f"SecuriSphere • {incident.get('timestamp', '')} • http://localhost:3000"
                },
            }]
        }

        delay = 1
        for attempt in range(1, DISCORD_MAX_RETRIES + 1):
            try:
                resp = requests.post(webhook_url, json=payload, timeout=5)
                if resp.status_code in (200, 204):
                    logger.info("Discord alert sent for %s", incident["incident_type"])
                    return
                logger.warning(
                    "Discord returned %d (attempt %d/%d)",
                    resp.status_code, attempt, DISCORD_MAX_RETRIES,
                )
            except Exception as exc:
                logger.warning("Discord request error (attempt %d): %s", attempt, exc)

            if attempt < DISCORD_MAX_RETRIES:
                time.sleep(delay)
                delay *= 2   # exponential backoff: 1 → 2 → 4 s

    # -----------------------------------------------------------------------
    # Correlation Rules
    # -----------------------------------------------------------------------

    def rule_recon_to_exploit(self, new_event: dict, buffer: list):
        if new_event.get("event_type") not in ("sql_injection", "path_traversal"):
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("recon_to_exploit", source_ip):
            return None
        scans = [
            e for e in buffer
            if e.get("source_entity", {}).get("ip") == source_ip
            and e.get("event_type") == "port_scan"
        ]
        if not scans:
            return None
        try:
            t1 = datetime.fromisoformat(scans[-1]["timestamp"].replace("Z", ""))
            t2 = datetime.fromisoformat(new_event["timestamp"].replace("Z", ""))
            if (t2 - t1).total_seconds() > 600:
                return None
        except Exception:
            return None
        self._set_cooldown("recon_to_exploit", source_ip)
        return self.create_incident(
            "recon_to_exploitation",
            "Reconnaissance → Exploitation Chain Detected",
            f"Source {source_ip} performed port recon followed by {new_event['event_type']}.",
            "critical", 0.92, source_ip,
            [scans[-1], new_event], ["network", "api"],
            ["T1046", "T1595", "T1190", "T1526"],
            ["Block IP at firewall", "Audit API logs", "Apply WAF rules"],
        )

    def rule_credential_compromise(self, new_event: dict, buffer: list):
        if new_event.get("event_type") != "suspicious_login":
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        username  = new_event.get("target_entity", {}).get("username")
        if not source_ip or self._check_cooldown("credential_compromise", source_ip):
            return None
        attacks = [
            e for e in buffer
            if e.get("source_entity", {}).get("ip") == source_ip
            and e.get("event_type") in ("brute_force", "credential_stuffing")
        ]
        if not attacks:
            return None
        self._set_cooldown("credential_compromise", source_ip)
        return self.create_incident(
            "credential_compromise",
            "🔓 Credential Compromise Detected",
            f"Account '{username}' accessed from {source_ip} after {len(attacks)} failed attempts.",
            "critical", 0.95, source_ip,
            [attacks[-1], new_event], ["auth"],
            ["T1110", "T1078", "T1003"],
            ["Force password reset", "Revoke active sessions", "Enable MFA"],
            {"target_username": username},
        )

    def rule_full_kill_chain(self, new_event: dict, buffer: list):
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("full_kill_chain", source_ip):
            return None
        ip_events = [e for e in buffer if e.get("source_entity", {}).get("ip") == source_ip]
        layers    = {e.get("source_layer") for e in ip_events}
        if not {"network", "api", "auth"}.issubset(layers):
            return None
        self._set_cooldown("full_kill_chain", source_ip)

        # Build service traversal path for this multi-vector campaign
        return self.create_incident(
            "full_kill_chain",
            "🚨 MULTI-VECTOR ATTACK CAMPAIGN",
            (
                f"Source {source_ip} attacking across Network, API, and Auth layers. "
                f"Correlated {len(ip_events)} events."
            ),
            "critical", 0.97, source_ip,
            ip_events, list(layers),
            ["T1046", "T1595", "T1190", "T1110", "T1021", "T1570"],
            ["ISOLATE HOST IMMEDIATELY", "Trigger incident response", "Capture forensic snapshot"],
        )

    def rule_api_auth_combined(self, new_event: dict, buffer: list):
        if new_event.get("event_type") not in (
            "rate_abuse", "sql_injection", "credential_stuffing", "brute_force"
        ):
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("api_auth_combined", source_ip):
            return None
        ip_events = [e for e in buffer if e.get("source_entity", {}).get("ip") == source_ip]
        has_api  = any(e for e in ip_events if e.get("source_layer") == "api")
        has_auth = any(e for e in ip_events if e.get("source_layer") == "auth")
        if not (has_api and has_auth):
            return None
        self._set_cooldown("api_auth_combined", source_ip)
        return self.create_incident(
            "automated_attack_tool",
            "🤖 Automated Attack Tool Detected",
            f"Source {source_ip} targeting API and Auth endpoints simultaneously.",
            "high", 0.88, source_ip,
            ip_events, ["api", "auth"],
            ["T1110", "T1190", "T1071", "T1078"],
            ["Rate limit IP", "Deploy CAPTCHA", "Block at load-balancer"],
        )

    def rule_distributed_attack(self, new_event: dict, buffer: list):
        if new_event.get("event_type") not in ("brute_force", "credential_stuffing"):
            return None
        username = new_event.get("target_entity", {}).get("username")
        if not username or self._check_cooldown("distributed_attack", username):
            return None
        targeting = [e for e in buffer if e.get("target_entity", {}).get("username") == username]
        unique_ips = {
            e.get("source_entity", {}).get("ip") for e in targeting
            if e.get("source_entity", {}).get("ip")
        }
        if len(unique_ips) < 3:
            return None
        self._set_cooldown("distributed_attack", username)
        return self.create_incident(
            "distributed_credential_attack",
            "🌐 Distributed Credential Attack",
            f"Account '{username}' targeted from {len(unique_ips)} distinct IPs.",
            "critical", 0.90, list(unique_ips)[0],
            targeting, ["auth"],
            ["T1110.004", "T1078"],
            ["Lock account", "Block all attacking IPs", "Alert user"],
            {"target_username": username, "attacking_ips": list(unique_ips)},
        )

    def rule_data_exfiltration(self, new_event: dict, buffer: list):
        if new_event.get("event_type") != "sensitive_access":
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("data_exfiltration", source_ip):
            return None
        exploits = [
            e for e in buffer
            if e.get("source_entity", {}).get("ip") == source_ip
            and e.get("event_type") in ("sql_injection", "path_traversal")
        ]
        if not exploits:
            return None
        self._set_cooldown("data_exfiltration", source_ip)
        return self.create_incident(
            "data_exfiltration_risk",
            "📤 Data Exfiltration Risk Detected",
            f"Source {source_ip} accessed sensitive endpoints after exploitation attempt.",
            "high", 0.85, source_ip,
            [exploits[-1], new_event], ["api"],
            ["T1530", "T1190", "T1041", "T1048"],
            ["Audit access logs", "Restrict sensitive endpoints", "Rotate exposed secrets"],
        )

    def rule_persistent_threat(self, new_event: dict, buffer: list):
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("persistent_threat", source_ip):
            return None
        ip_events = [e for e in buffer if e.get("source_entity", {}).get("ip") == source_ip]
        if len(ip_events) < 10:
            return None
        try:
            times = [datetime.fromisoformat(e["timestamp"].replace("Z", "")) for e in ip_events]
            duration = (max(times) - min(times)).total_seconds()
        except Exception:
            return None
        if duration < 300:
            return None
        unique_types = len({e.get("event_type") for e in ip_events})
        if unique_types < 3:
            return None
        self._set_cooldown("persistent_threat", source_ip)
        return self.create_incident(
            "persistent_threat",
            "⏱️ Persistent Threat Actor",
            (
                f"Source {source_ip} generated {len(ip_events)} events "
                f"over {duration / 60:.1f} minutes ({unique_types} distinct attack types)."
            ),
            "high", 0.82, source_ip,
            ip_events, list({e.get("source_layer") for e in ip_events}),
            ["T1595", "T1071"],
            ["Block IP", "Enrich via threat intelligence", "Enable full packet capture"],
        )

    def rule_brute_force_attempt(self, new_event: dict, buffer: list):
        if new_event.get("event_type") not in ("brute_force", "credential_stuffing"):
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("brute_force_attempt", source_ip):
            return None
        self._set_cooldown("brute_force_attempt", source_ip)
        return self.create_incident(
            "brute_force_attempt",
            "🔐 Brute Force / Stuffing Attempt",
            f"Source {source_ip} performing {new_event['event_type']}.",
            "medium", 0.80, source_ip,
            [new_event], ["auth"],
            ["T1110"],
            ["Block IP", "Force password reset for targeted account"],
        )

    def rule_critical_exploit_attempt(self, new_event: dict, buffer: list):
        if (
            new_event.get("severity", {}).get("level") != "critical"
            and new_event.get("event_type") not in ("sql_injection", "xss", "path_traversal")
        ):
            return None
        source_ip = new_event.get("source_entity", {}).get("ip")
        if not source_ip or self._check_cooldown("critical_exploit", source_ip):
            return None
        same_type = [
            e for e in buffer
            if e.get("source_entity", {}).get("ip") == source_ip
            and e.get("event_type") == new_event.get("event_type")
        ]
        if len(same_type) < 2:
            return None
        self._set_cooldown("critical_exploit", source_ip)
        return self.create_incident(
            "critical_exploit_attempt",
            "🛡️ Critical Exploit Attempt",
            f"Source {source_ip} performing {new_event['event_type']} ({len(same_type)} times).",
            "high", 0.90, source_ip,
            same_type, ["api"],
            ["T1190", "T1068"],
            ["Block IP", "Apply virtual patch", "Review WAF ruleset"],
        )

    # -----------------------------------------------------------------------
    # Phase 2 — Browser-layer detection & kill-chain rules
    # -----------------------------------------------------------------------
    #
    # All rules in this block ONLY fire when the incoming event has
    # source_layer == "browser-agent". They correlate by ``site_id``
    # (populated by the browser_monitor on ingest) rather than by IP,
    # though the client's source_ip is still used for risk scoring and
    # Discord alert display via create_incident().

    def _browser_window(
        self,
        buffer: list,
        site_id: str,
        seconds: int,
        event_type: str = None,
        tag: str = None,
    ) -> list:
        """Return buffer entries for *site_id* within the last *seconds*,
        optionally filtered by ``event_type`` or a ``correlation_tags`` entry.

        Only considers events whose ``source_layer`` is ``browser-agent``,
        so cross-layer noise cannot accidentally satisfy a browser rule.
        """
        now = datetime.now()
        matches = []
        for e in buffer:
            if e.get("site_id") != site_id:
                continue
            if e.get("source_layer") != "browser-agent":
                continue
            if event_type and e.get("event_type") != event_type:
                continue
            if tag:
                tags = e.get("correlation_tags") or []
                if tag not in tags:
                    continue
            ts = e.get("timestamp")
            if not ts:
                continue
            try:
                t = datetime.fromisoformat(
                    ts.replace("Z", "").replace("+00:00", "")
                )
            except Exception:
                continue
            if (now - t).total_seconds() <= seconds:
                matches.append(e)
        return matches

    @staticmethod
    def _browser_source_ip(event: dict) -> str:
        """Best-effort client IP for a browser event (nested or flat)."""
        return (
            event.get("source_entity", {}).get("ip")
            or event.get("source_ip")
            or "unknown"
        )

    # ---- single-event detection rules -------------------------------------

    def rule_browser_sqli(self, new_event: dict, buffer: list):
        """Rule 2 — SQLInjectionAttempt. Fires on any browser-agent event
        whose ``correlation_tags`` advertise a SQL injection payload."""
        if new_event.get("source_layer") != "browser-agent":
            return None
        tags = new_event.get("correlation_tags") or []
        if not any(t in tags for t in ("sql-injection", "sqli")):
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_sqli", site_id):
            return None
        self._set_cooldown("browser_sqli", site_id)
        return self.create_incident(
            "browser_sql_injection_attempt",
            "💉 Browser-Layer SQL Injection Attempt",
            (
                f"Browser agent on site {site_id} captured a SQL injection payload "
                f"in a request to {new_event.get('target_url') or '?'}."
            ),
            "critical", 0.92, self._browser_source_ip(new_event),
            [new_event], ["browser"],
            ["T1190"],
            [
                "Block source IP",
                "Audit recent DB queries for this endpoint",
                "Deploy a WAF rule for the matched parameter",
            ],
            {"site_id": site_id, "stage_labels": ["initial_access"]},
        )

    def rule_browser_path_traversal(self, new_event: dict, buffer: list):
        """Rule 3 — PathTraversal. Fires when a browser-agent event carries
        a ``../`` / ``%2e%2e`` payload in ``target_url`` or is tagged as
        ``path-traversal`` by the agent's client-side detector."""
        if new_event.get("source_layer") != "browser-agent":
            return None
        url = (new_event.get("target_url") or "").lower()
        tags = new_event.get("correlation_tags") or []
        if "../" not in url and "%2e%2e" not in url and "path-traversal" not in tags:
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_path_traversal", site_id):
            return None
        self._set_cooldown("browser_path_traversal", site_id)
        return self.create_incident(
            "browser_path_traversal_attempt",
            "📂 Browser-Layer Path Traversal Attempt",
            (
                f"Browser agent on site {site_id} observed a traversal payload "
                f"in {new_event.get('target_url') or '?'}."
            ),
            "high", 0.88, self._browser_source_ip(new_event),
            [new_event], ["browser"],
            ["T1083"],
            [
                "Block source IP",
                "Validate path handling in the targeted endpoint",
                "Review file-serving rules on the web-app",
            ],
            {"site_id": site_id, "stage_labels": ["discovery"]},
        )

    def rule_browser_brute_force(self, new_event: dict, buffer: list):
        """Rule 1 — BruteForce. Fires when ≥5 ``auth_failure`` events are
        seen from the same site_id within the last 60 seconds."""
        if new_event.get("source_layer") != "browser-agent":
            return None
        if new_event.get("event_type") != "auth_failure":
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_brute_force", site_id):
            return None
        failures = self._browser_window(
            buffer, site_id, seconds=60, event_type="auth_failure"
        )
        if len(failures) < 5:
            return None
        self._set_cooldown("browser_brute_force", site_id)
        return self.create_incident(
            "browser_brute_force",
            "🔐 Browser-Layer Brute Force",
            (
                f"Site {site_id} received {len(failures)} auth_failure events "
                f"from the browser agent within 60 seconds."
            ),
            "high", 0.90, self._browser_source_ip(new_event),
            failures, ["browser"],
            ["T1110"],
            [
                "Rate-limit the login form",
                "Enable CAPTCHA on repeated failures",
                "Lock affected accounts temporarily",
            ],
            {"site_id": site_id, "stage_labels": ["credential_access"]},
        )

    def rule_browser_recon_scan(self, new_event: dict, buffer: list):
        """Rule 4 — ReconScan. Fires when ≥10 distinct ``target_entity``
        values are probed from the same site_id within the last 30 seconds."""
        if new_event.get("source_layer") != "browser-agent":
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_recon_scan", site_id):
            return None
        recent = self._browser_window(buffer, site_id, seconds=30)
        distinct = {e.get("target_entity") for e in recent if e.get("target_entity")}
        if len(distinct) < 10:
            return None
        self._set_cooldown("browser_recon_scan", site_id)
        return self.create_incident(
            "browser_recon_scan",
            "🔎 Browser-Layer Reconnaissance Scan",
            (
                f"Site {site_id} was probed on {len(distinct)} distinct entities "
                f"in the last 30 seconds from the browser layer."
            ),
            "medium", 0.82, self._browser_source_ip(new_event),
            recent, ["browser"],
            ["T1046", "T1526"],
            [
                "Rate-limit source IP",
                "Review URL enumeration logs",
                "Inspect the robots.txt / site index being harvested",
            ],
            {
                "site_id": site_id,
                "distinct_target_count": len(distinct),
                "stage_labels": ["reconnaissance"],
            },
        )

    # ---- multi-stage kill-chain rules -------------------------------------

    def rule_browser_bruteforce_to_exfil(self, new_event: dict, buffer: list):
        """Kill Chain A — BruteForce → Data Access within 5 minutes.

        Triggered by a ``data_access`` browser event if at least 5
        ``auth_failure`` events were observed for the same site_id in
        the preceding 5 minutes.
        """
        if new_event.get("source_layer") != "browser-agent":
            return None
        if new_event.get("event_type") != "data_access":
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_bf_to_exfil", site_id):
            return None
        failures = self._browser_window(
            buffer, site_id, seconds=300, event_type="auth_failure"
        )
        if len(failures) < 5:
            return None
        self._set_cooldown("browser_bf_to_exfil", site_id)
        return self.create_incident(
            "browser_bruteforce_to_exfiltration",
            "🚨 Kill Chain A: Brute Force → Data Access",
            (
                f"Site {site_id}: {len(failures)} auth_failures were followed by "
                f"a data_access event within 5 minutes — likely successful compromise."
            ),
            "critical", 0.95, self._browser_source_ip(new_event),
            failures + [new_event], ["browser"],
            ["T1110", "T1530", "T1041"],
            [
                "Revoke the active session immediately",
                "Audit every record touched in the data_access",
                "Force password reset and notify the user",
            ],
            {
                "site_id": site_id,
                "stage_labels": ["initial_access", "exfiltration"],
            },
        )

    def rule_browser_recon_to_privesc(self, new_event: dict, buffer: list):
        """Kill Chain B — ReconScan → privilege_change within 3 minutes."""
        if new_event.get("source_layer") != "browser-agent":
            return None
        if new_event.get("event_type") != "privilege_change":
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_recon_to_privesc", site_id):
            return None
        recent = self._browser_window(buffer, site_id, seconds=180)
        distinct = {e.get("target_entity") for e in recent if e.get("target_entity")}
        if len(distinct) < 10:
            return None
        self._set_cooldown("browser_recon_to_privesc", site_id)
        return self.create_incident(
            "browser_recon_to_privilege_escalation",
            "🚨 Kill Chain B: Recon → Privilege Escalation",
            (
                f"Site {site_id} saw reconnaissance across {len(distinct)} entities "
                f"followed by a privilege_change within 3 minutes."
            ),
            "high", 0.90, self._browser_source_ip(new_event),
            recent + [new_event], ["browser"],
            ["T1046", "T1078", "T1548", "T1068"],
            [
                "Revoke elevated session",
                "Audit the privilege change event in auth logs",
                "Block source IP pending review",
            ],
            {
                "site_id": site_id,
                "stage_labels": ["reconnaissance", "privilege_escalation"],
            },
        )

    def rule_browser_multi_hop(self, new_event: dict, buffer: list):
        """Kill Chain C — MultiHopLateralMovement: ≥3 distinct target_entity
        values hit in sequence within 2 minutes from the same site_id.

        Note: this rule is deliberately noisy on high-traffic sites — tune
        the threshold or cooldown in production if it raises false positives.
        """
        if new_event.get("source_layer") != "browser-agent":
            return None
        site_id = new_event.get("site_id")
        if not site_id or self._check_cooldown("browser_multi_hop", site_id):
            return None
        recent = self._browser_window(buffer, site_id, seconds=120)
        seen_in_order: list = []
        for e in recent:
            t = e.get("target_entity")
            if t and t not in seen_in_order:
                seen_in_order.append(t)
        if len(seen_in_order) < 3:
            return None
        self._set_cooldown("browser_multi_hop", site_id)
        return self.create_incident(
            "browser_multi_hop_lateral_movement",
            "🔀 Kill Chain C: Multi-Hop Lateral Movement",
            (
                f"Site {site_id} traversed {len(seen_in_order)} distinct entities "
                f"within 2 minutes: {seen_in_order[:5]}"
            ),
            "high", 0.85, self._browser_source_ip(new_event),
            recent, ["browser"],
            ["T1021", "T1570"],
            [
                "Audit the traversal path across the hit entities",
                "Block source IP pending review",
                "Review access control on each hit entity",
            ],
            {
                "site_id": site_id,
                "stage_labels": ["lateral_movement"],
                "hops": seen_in_order,
            },
        )

    # -----------------------------------------------------------------------
    # Event processing
    # -----------------------------------------------------------------------

    def process_event(self, event_data) -> None:
        try:
            event = json.loads(event_data) if isinstance(event_data, str) else event_data
        except json.JSONDecodeError:
            logger.error("Failed to parse event data")
            return

        self.stats["events_processed"] += 1

        # Enrich with topology metadata before correlation
        event = enrich_event(event)

        # Browser-layer normalization (Phase 2): browser_monitor publishes a
        # flat source_ip; promote it into the nested source_entity.ip shape so
        # IP-keyed rules and risk scoring keep working uniformly.
        if event.get("source_layer") == "browser-agent" and not event.get("source_entity"):
            event["source_entity"] = {"ip": event.get("source_ip", "unknown")}

        source_ip = event.get("source_entity", {}).get("ip")

        # Add to rolling buffer, prune stale entries
        with self.buffer_lock:
            self.event_buffer.append(event)
            cutoff = datetime.now() - timedelta(seconds=CORRELATION_WINDOW)
            self.event_buffer = [
                e for e in self.event_buffer
                if datetime.fromisoformat(e["timestamp"].replace("Z", "")) > cutoff
            ]
            buffer_copy = list(self.event_buffer)

        service_name = event.get("source_service_name")
        service_key = service_name or source_ip
        entity_type = "service" if service_name else "ip"
        if service_key:
            self.update_risk_score(service_key, event, entity_type=entity_type)

        for rule in self.rules:
            try:
                incident = rule(event, buffer_copy)
                if incident:
                    self.publish_incident(incident)
            except Exception as exc:
                logger.error("Rule %s error: %s", rule.__name__, exc)

        logger.info(
            "[EVENT] %s | %s | %s",
            event.get("source_layer"), event.get("event_type"), source_ip,
        )

    # -----------------------------------------------------------------------
    # Summary loop
    # -----------------------------------------------------------------------

    def publish_summary_loop(self) -> None:
        while True:
            time.sleep(30)
            try:
                with self.buffer_lock:
                    count  = len(self.event_buffer)
                    layers = Counter(e.get("source_layer") for e in self.event_buffer)
                    types  = Counter(e.get("event_type")   for e in self.event_buffer)

                risk_summary = {
                    key: {
                        "score":       d["score"],
                        "level":       d["threat_level"],
                        "entity_type": d.get("entity_type", "ip"),
                        "source_ip":   d.get("source_ip"),
                    }
                    for key, d in self.risk_scores.items()
                    if d["score"] > 0
                }

                summary = {
                    "total_events_in_window": count,
                    "events_by_layer":        dict(layers),
                    "events_by_type":         dict(types),
                    "active_incidents":       len(self.recent_incidents),
                    "total_incidents":        self.stats["incidents_created"],
                    "risk_scores":            risk_summary,
                    "timestamp":              datetime.now().isoformat(),
                }
                self.redis.publish("correlation_summary", json.dumps(summary))
                self.redis.set("latest_summary", json.dumps(summary))
            except Exception as exc:
                logger.error("Summary loop error: %s", exc)

    # -----------------------------------------------------------------------
    # Flask routes
    # -----------------------------------------------------------------------

    def _setup_routes(self) -> None:
        app = self.app

        @app.route("/engine/health")
        def health():
            return jsonify({
                "status":            "running",
                "events_processed":  self.stats["events_processed"],
                "incidents_created": self.stats["incidents_created"],
                "active_risks":      len(self.risk_scores),
                "active_rules":      len(self.rules),
                "uptime":            (datetime.now() - self.stats["start_time"]).total_seconds(),
            })

        @app.route("/engine/stats")
        def stats():
            stats_data = dict(self.stats)
            stats_data["risk_scores"] = {
                key: {
                    "score":           d["score"],
                    "peak_score":      d["peak_score"],
                    "threat_level":    d["threat_level"],
                    "entity_type":     d.get("entity_type", "ip"),
                    "source_ip":       d.get("source_ip"),
                    "event_count":     d["event_count"],
                    "last_event_type": d["last_event_type"],
                    "last_update":     d["last_update"],
                    "layers_involved": list(d["layers_involved"]),
                }
                for key, d in self.risk_scores.items()
            }
            return jsonify({"status": "success", "data": stats_data})

        @app.route("/engine/risk-scores")
        def risk_scores():
            out = {}
            for key, d in self.risk_scores.items():
                out[key] = {
                    **{k: v for k, v in d.items() if k != "layers_involved"},
                    "layers_involved": list(d["layers_involved"]),
                }
            return jsonify({"status": "success", "data": out})

        @app.route("/engine/mitre-mapping")
        def mitre_mapping():
            """Return MITRE technique frequency map from all processed incidents."""
            return jsonify({
                "status": "success",
                "data": {
                    "technique_hits":  dict(self.stats["mitre_hits"]),
                    "total_techniques": len(self.stats["mitre_hits"]),
                    "total_incidents":  self.stats["incidents_created"],
                },
            })

        @app.route("/engine/mttd-report")
        def mttd_report():
            """Return per-incident-type MTTD statistics from PostgreSQL."""
            if not _KC_AVAILABLE:
                return jsonify({"status": "error", "message": "Kill chain module not available"}), 503
            try:
                rows = fetch_mttd_report()
                return jsonify({"status": "success", "data": rows})
            except Exception as exc:
                return jsonify({"status": "error", "message": str(exc)}), 500

        @app.route("/engine/reset", methods=["POST"])
        def reset():
            """
            Hard reset for between-scenario runs in reproducibility experiments.
            Clears:
              - event_buffer (correlation window)
              - risk_scores (per-IP state)
              - recent_incidents (in-memory list)
              - incident_cooldowns (per-rule, per-key 5-min gate)
              - Redis risk_scores_current hash
            Preserves: cumulative stats start_time (uptime).
            """
            buf_size   = len(self.event_buffer)
            cd_count   = len(self.incident_cooldowns)
            risk_count = len(self.risk_scores)

            with self.buffer_lock:
                self.event_buffer = []
            self.risk_scores.clear()
            try:
                self.redis.delete("risk_scores_current")
            except Exception as exc:
                logger.warning("Reset: redis delete failed: %s", exc)
            self.recent_incidents  = []
            self.incident_cooldowns = {}

            logger.info(
                "[RESET] Engine state cleared — buf=%d events, %d cooldowns, %d risk entries",
                buf_size, cd_count, risk_count,
            )
            return jsonify({
                "status":           "reset_complete",
                "cleared_events":   buf_size,
                "cleared_cooldowns": cd_count,
                "cleared_risks":    risk_count,
            })

    def _run_flask(self) -> None:
        self.app.run(host="0.0.0.0", port=5070, use_reloader=False)

    # -----------------------------------------------------------------------
    # Entry point
    # -----------------------------------------------------------------------

    def start(self) -> None:
        logger.info("Starting SecuriSphere Correlation Engine …")
        threading.Thread(target=self._run_flask,              daemon=True).start()
        threading.Thread(target=self.decay_risk_scores_loop,  daemon=True).start()
        threading.Thread(target=self.publish_summary_loop,    daemon=True).start()

        while True:
            try:
                for message in self.pubsub.listen():
                    if message["type"] == "message":
                        self.process_event(message["data"])
            except Exception as exc:
                logger.error("Redis listen loop error: %s", exc)
                time.sleep(1)
                self.connect_redis()


if __name__ == "__main__":
    CorrelationEngine().start()
