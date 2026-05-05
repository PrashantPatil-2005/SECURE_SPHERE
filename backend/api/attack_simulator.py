"""
attack_simulator.py — In-process attack scenario emitter.

Generates synthetic security events that mimic the kill chains in
`attacker/scenario_{a,b,c}.py` without requiring any target services.
Events are pushed to Redis (events:<layer>) and published on the
`security_events` channel so the existing correlation engine + SocketIO
fan-out treats them identically to real monitor traffic.

Used by `/api/attack/run` when the legacy subprocess + localhost-target
launcher is unavailable (e.g. single-container deploy on Render).
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional

SPEED_MAP = {"fast": 0.15, "normal": 0.6, "demo": 1.4, "slow": 3.0}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ev(
    *,
    layer: str,
    event_type: str,
    severity: str,
    src_ip: str,
    src_service: Optional[str],
    dst_service: str,
    dst_ip: Optional[str] = None,
    mitre: Optional[str] = None,
    details: Optional[dict] = None,
    confidence: float = 0.85,
) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _now_iso(),
        "source_layer": layer,
        "event_type": event_type,
        "severity": {"level": severity, "score": _sev_score(severity)},
        "source_entity": {"ip": src_ip, "service": src_service},
        "destination_entity": {"ip": dst_ip or "10.0.1.20", "service": dst_service},
        "mitre_technique": mitre or "",
        "confidence": confidence,
        "details": details or {},
    }


_SEV = {"critical": 95, "high": 75, "medium": 50, "low": 25, "info": 10}


def _sev_score(level: str) -> int:
    return _SEV.get(level.lower(), 30)


# ── Scenario definitions (returns list of event dicts) ─────────────────────


def _scenario_a(src_ip: str) -> List[dict]:
    """Brute force → credential reuse → exfiltration."""
    out: List[dict] = []
    out.append(_ev(
        layer="network", event_type="recon_probe", severity="low",
        src_ip=src_ip, src_service=None, dst_service="auth-service",
        mitre="T1595", details={"path": "/auth/health"},
    ))
    for i in range(50):
        out.append(_ev(
            layer="auth", event_type="login_failed",
            severity="medium" if i < 40 else "high",
            src_ip=src_ip, src_service=None, dst_service="auth-service",
            mitre="T1110",
            details={"username": f"user{i % 8}", "reason": "invalid_credentials"},
            confidence=0.92,
        ))
    out.append(_ev(
        layer="auth", event_type="login_success",
        severity="high", src_ip=src_ip, src_service=None,
        dst_service="auth-service", mitre="T1078",
        details={"username": "admin", "after_failures": 50},
        confidence=0.97,
    ))
    out.append(_ev(
        layer="api", event_type="data_access",
        severity="high", src_ip=src_ip, src_service="auth-service",
        dst_service="api-gateway", mitre="T1078",
        details={"path": "/api/users", "rows": 1240},
    ))
    out.append(_ev(
        layer="network", event_type="data_exfiltration",
        severity="critical", src_ip=src_ip, src_service="api-gateway",
        dst_service="external", dst_ip="203.0.113.42", mitre="T1041",
        details={"bytes_out": 18_400_000, "destination": "203.0.113.42:443"},
        confidence=0.95,
    ))
    return out


def _scenario_b(src_ip: str) -> List[dict]:
    """Recon → SQLi → privilege escalation → lateral."""
    out: List[dict] = []
    for port in (22, 80, 443, 5432, 8080):
        out.append(_ev(
            layer="network", event_type="port_scan",
            severity="low", src_ip=src_ip, src_service=None,
            dst_service="web-app", mitre="T1046",
            details={"port": port, "state": "open" if port in (80, 443, 8080) else "closed"},
        ))
    for payload in ("' OR '1'='1", "1; DROP TABLE users--", "UNION SELECT password FROM users"):
        out.append(_ev(
            layer="api", event_type="sql_injection",
            severity="high", src_ip=src_ip, src_service=None,
            dst_service="web-app", mitre="T1190",
            details={"path": "/search", "payload": payload},
            confidence=0.94,
        ))
    out.append(_ev(
        layer="api", event_type="privilege_escalation",
        severity="critical", src_ip=src_ip, src_service="web-app",
        dst_service="web-app", mitre="T1068",
        details={"cve": "CVE-2024-1086", "from_role": "user", "to_role": "root"},
        confidence=0.96,
    ))
    out.append(_ev(
        layer="network", event_type="lateral_movement",
        severity="high", src_ip=src_ip, src_service="web-app",
        dst_service="api-gateway", mitre="T1021",
        details={"protocol": "ssh", "auth": "key"},
    ))
    return out


def _scenario_c(src_ip: str) -> List[dict]:
    """Multi-hop lateral movement + bulk exfil."""
    out: List[dict] = []
    out.append(_ev(
        layer="auth", event_type="stolen_credential_use",
        severity="high", src_ip=src_ip, src_service=None,
        dst_service="auth-service", mitre="T1078",
        details={"key_id": "AKIA-LEAKED-1234", "method": "api_key"},
        confidence=0.93,
    ))
    hops = [("db-host", "api-host"), ("api-host", "payment-service"), ("payment-service", "warehouse")]
    for src, dst in hops:
        out.append(_ev(
            layer="network", event_type="lateral_movement",
            severity="high", src_ip=src_ip, src_service=src,
            dst_service=dst, mitre="T1021",
            details={"protocol": "smb", "from": src, "to": dst},
        ))
    out.append(_ev(
        layer="api", event_type="file_discovery",
        severity="medium", src_ip=src_ip, src_service="warehouse",
        dst_service="warehouse", mitre="T1083",
        details={"files": 8421, "mounted": ["/data", "/backup"]},
    ))
    out.append(_ev(
        layer="api", event_type="data_collection",
        severity="high", src_ip=src_ip, src_service="warehouse",
        dst_service="warehouse", mitre="T1530",
        details={"objects": 4200, "size_mb": 312},
    ))
    out.append(_ev(
        layer="network", event_type="bulk_exfiltration",
        severity="critical", src_ip=src_ip, src_service="warehouse",
        dst_service="external", dst_ip="198.51.100.7", mitre="T1048",
        details={"protocol": "dns_tunnel", "bytes_out": 312_000_000},
        confidence=0.97,
    ))
    return out


_SCENARIOS = {"a": _scenario_a, "b": _scenario_b, "c": _scenario_c}


# ── In-process kill-chain correlator ──────────────────────────────────────
#
# Mirrors `rule_full_kill_chain` from backend/engine/correlation/correlation_engine.py
# so kill-chain incidents fire even when the standalone engine container is
# not running. Tracks events from in-process simulator emits, fires once per
# IP+cooldown when network/api/auth all observed.

_REQUIRED_LAYERS = frozenset({"network", "api", "auth"})
_BUFFER_TTL_SECS = 900   # 15-min rolling window
_COOLDOWN_SECS   = 60    # short so back-to-back demo runs all emit


class MiniKillChainCorrelator:
    def __init__(self, redis_client=None, socketio=None, log_cb: Optional[Callable[[str], None]] = None):
        self._redis = redis_client
        self._socketio = socketio
        self._log = log_cb or (lambda _msg: None)
        self._lock = threading.Lock()
        self._buffer: List[dict] = []
        self._cooldowns: dict = {}

    def observe(self, event: dict) -> Optional[dict]:
        src_ip = (event.get("source_entity") or {}).get("ip")
        if not src_ip:
            return None
        now = datetime.now(timezone.utc)
        with self._lock:
            self._buffer.append(event)
            cutoff = now - timedelta(seconds=_BUFFER_TTL_SECS)
            self._buffer = [
                e for e in self._buffer
                if _parse_ts(e.get("timestamp")) >= cutoff
            ]
            if self._cooldowns.get(src_ip) and now < self._cooldowns[src_ip]:
                return None
            ip_events = [
                e for e in self._buffer
                if (e.get("source_entity") or {}).get("ip") == src_ip
            ]
            layers = {e.get("source_layer") for e in ip_events}
            if not _REQUIRED_LAYERS.issubset(layers):
                return None
            self._cooldowns[src_ip] = now + timedelta(seconds=_COOLDOWN_SECS)

        incident = self._build_incident(src_ip, ip_events, sorted(layers))
        self._publish(incident)
        return incident

    def _build_incident(self, src_ip: str, ip_events: List[dict], layers: list) -> dict:
        timestamps = [_parse_ts(e.get("timestamp")) for e in ip_events if e.get("timestamp")]
        time_span = int((max(timestamps) - min(timestamps)).total_seconds()) if timestamps else 0
        techniques = []
        for e in ip_events:
            t = e.get("mitre_technique")
            if t and t not in techniques:
                techniques.append(t)
        services = []
        for e in ip_events:
            s = (e.get("destination_entity") or {}).get("service") or (e.get("source_entity") or {}).get("service")
            if s and s not in services:
                services.append(s)
        return {
            "incident_id":            str(uuid.uuid4()),
            "incident_type":          "full_kill_chain",
            "is_kill_chain":          True,
            "title":                  "🚨 MULTI-VECTOR ATTACK CAMPAIGN",
            "description": (
                f"Source {src_ip} attacking across "
                f"{', '.join(layers)} layers. Correlated {len(ip_events)} events."
            ),
            "severity":               "critical",
            "confidence":             0.97,
            "source_ip":              src_ip,
            "target_username":        _extract_username(ip_events),
            "correlated_events":      [e.get("event_id") for e in ip_events if e.get("event_id")],
            "correlated_event_count": len(ip_events),
            "layers_involved":        layers,
            "mitre_techniques":       techniques or ["T1046", "T1595", "T1190", "T1110", "T1021"],
            "service_path":           services,
            "recommended_actions": [
                "ISOLATE HOST IMMEDIATELY",
                "Trigger incident response",
                "Capture forensic snapshot",
            ],
            "risk_score_at_time":     min(100, 40 + len(ip_events) * 3),
            "time_span_seconds":      time_span,
            "timestamp":              datetime.now(timezone.utc).isoformat(),
        }

    def _publish(self, incident: dict) -> None:
        payload = json.dumps(incident, default=str)
        try:
            if self._redis is not None:
                self._redis.lpush("incidents", payload)
                self._redis.ltrim("incidents", 0, 499)
                self._redis.publish("correlated_incidents", payload)
        except Exception as exc:
            self._log(f"[mini-correlator redis-error] {exc}")
        try:
            if self._socketio is not None:
                self._socketio.emit("new_incident", incident)
        except Exception as exc:
            self._log(f"[mini-correlator ws-error] {exc}")
        try:
            self._persist_postgres(incident)
        except Exception as exc:
            self._log(f"[mini-correlator pg-error] {exc}")
        self._log(
            f"[kill-chain] FIRED ip={incident['source_ip']} "
            f"events={incident['correlated_event_count']} "
            f"layers={','.join(incident['layers_involved'])}"
        )

    def _persist_postgres(self, incident: dict) -> None:
        """Write campaign + correlated_incident + kill_chain rows so /api/campaigns
        and /api/incidents return the kill chain. UPSERT on campaigns to merge
        repeated fires from same source_ip into one analyst-facing record.
        Best-effort — errors are logged and ignored so notification pipeline
        never blocks on DB hiccups.
        """
        try:
            import psycopg2
            import psycopg2.extras
        except ImportError:
            return
        if os.getenv("DATABASE_URL"):
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        else:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
        try:
            with conn:
                with conn.cursor() as cur:
                    src_ip = incident["source_ip"]
                    actor_id = f"ip:{src_ip}"
                    incident_id = incident["incident_id"]
                    now_iso = incident["timestamp"]
                    techniques = incident.get("mitre_techniques") or []
                    layers = incident.get("layers_involved") or []
                    services = incident.get("service_path") or []
                    target_users = (
                        [incident["target_username"]]
                        if incident.get("target_username") else []
                    )

                    # --- UPSERT campaign (one active per actor) -------------
                    cur.execute(
                        """
                        SELECT campaign_id FROM campaigns
                         WHERE actor_id = %s AND status = 'active'
                         LIMIT 1
                        """,
                        (actor_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        campaign_id = row[0]
                        cur.execute(
                            """
                            UPDATE campaigns
                               SET incident_ids   = array_append(incident_ids, %s::uuid),
                                   incident_count = incident_count + 1,
                                   service_path   = (
                                       SELECT ARRAY(SELECT DISTINCT unnest(service_path || %s::text[]))
                                   ),
                                   mitre_techniques = (
                                       SELECT ARRAY(SELECT DISTINCT unnest(mitre_techniques || %s::text[]))
                                   ),
                                   layers_involved  = (
                                       SELECT ARRAY(SELECT DISTINCT unnest(layers_involved || %s::text[]))
                                   ),
                                   target_usernames = (
                                       SELECT ARRAY(SELECT DISTINCT unnest(target_usernames || %s::text[]))
                                   ),
                                   severity         = 'critical',
                                   max_confidence   = GREATEST(max_confidence, %s),
                                   last_event_at    = NOW(),
                                   updated_at       = NOW()
                             WHERE campaign_id = %s
                            """,
                            (
                                incident_id, services, techniques, layers,
                                target_users, float(incident.get("confidence", 0.97)),
                                campaign_id,
                            ),
                        )
                    else:
                        campaign_id = str(uuid.uuid4())
                        stages = ["recon", "initial-access", "execution",
                                  "lateral-movement", "exfiltration"]
                        cur.execute(
                            """
                            INSERT INTO campaigns
                                (campaign_id, actor_id, source_ip, target_usernames,
                                 incident_ids, incident_count, service_path,
                                 mitre_techniques, layers_involved, stages_seen,
                                 severity, max_confidence, first_event_at, last_event_at)
                            VALUES (%s, %s, %s, %s, ARRAY[%s::uuid], 1, %s,
                                    %s, %s, %s, 'critical', %s, NOW(), NOW())
                            """,
                            (
                                campaign_id, actor_id, src_ip, target_users,
                                incident_id, services, techniques, layers, stages,
                                float(incident.get("confidence", 0.97)),
                            ),
                        )

                    # --- correlated_incidents row ---------------------------
                    cur.execute(
                        """
                        INSERT INTO correlated_incidents
                            (incident_id, incident_type, title, description,
                             severity, confidence, source_ip, target_username,
                             correlated_event_ids, layers_involved, event_types,
                             mitre_techniques, technique_id, technique_name, tactic,
                             recommended_actions, risk_score_at_time,
                             time_span_seconds, campaign_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                                %s::uuid[], %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s)
                        ON CONFLICT (incident_id) DO NOTHING
                        """,
                        (
                            incident_id, incident["incident_type"],
                            incident["title"], incident["description"],
                            incident["severity"], float(incident["confidence"]),
                            src_ip, incident.get("target_username"),
                            [e for e in incident.get("correlated_events", []) if _is_uuid(e)],
                            layers,
                            [],
                            techniques,
                            techniques[0] if techniques else None,
                            None, None,
                            incident.get("recommended_actions", []),
                            int(incident.get("risk_score_at_time", 90)),
                            float(incident.get("time_span_seconds", 0)),
                            campaign_id,
                        ),
                    )

                    # --- kill_chains row ------------------------------------
                    steps_json = json.dumps([
                        {
                            "service_name": (e.get("destination_entity") or {}).get("service"),
                            "event_type":   e.get("event_type"),
                            "timestamp":    e.get("timestamp"),
                            "severity":     (e.get("severity") or {}).get("level")
                                            if isinstance(e.get("severity"), dict)
                                            else e.get("severity"),
                            "mitre":        e.get("mitre_technique"),
                            "source_ip":    src_ip,
                            "layer":        e.get("source_layer"),
                        }
                        for e in self._buffer
                        if (e.get("source_entity") or {}).get("ip") == src_ip
                    ])
                    cur.execute(
                        """
                        INSERT INTO kill_chains
                            (incident_id, incident_type, source_ip, target_username,
                             steps, service_path, first_service, last_service,
                             mitre_techniques, first_event_at, severity, campaign_id)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                                NOW(), %s, %s)
                        ON CONFLICT (incident_id) DO NOTHING
                        """,
                        (
                            incident_id, incident["incident_type"], src_ip,
                            incident.get("target_username"),
                            steps_json, services,
                            services[0] if services else None,
                            services[-1] if services else None,
                            techniques, "critical", campaign_id,
                        ),
                    )
        finally:
            conn.close()

    def reset(self) -> None:
        with self._lock:
            self._buffer.clear()
            self._cooldowns.clear()

    def force_fire(self, src_ip: str) -> Optional[dict]:
        """Bypass cooldown + layer check. Build kill chain from whatever events
        exist for src_ip and publish. Used at end of 'Run All' to guarantee a
        consolidated incident regardless of correlator state."""
        with self._lock:
            ip_events = [
                e for e in self._buffer
                if (e.get("source_entity") or {}).get("ip") == src_ip
            ]
            if not ip_events:
                return None
            layers = sorted({e.get("source_layer") for e in ip_events if e.get("source_layer")})
            self._cooldowns[src_ip] = datetime.now(timezone.utc) + timedelta(seconds=_COOLDOWN_SECS)
        incident = self._build_incident(src_ip, ip_events, layers)
        self._publish(incident)
        return incident


def _parse_ts(raw) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        s = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _extract_username(events: List[dict]) -> Optional[str]:
    for e in events:
        u = (e.get("details") or {}).get("username")
        if u:
            return u
    return None


_UUID_RE = None


def _is_uuid(s) -> bool:
    global _UUID_RE
    if _UUID_RE is None:
        import re
        _UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
    return bool(s and _UUID_RE.match(str(s)))


# ── Runtime ───────────────────────────────────────────────────────────────


class SimulatorRuntime:
    """Owns a single concurrent simulation. Caller checks `is_running()`
    before launching another."""

    def __init__(self, redis_client=None, socketio=None, log_cb: Optional[Callable[[str], None]] = None):
        self._redis = redis_client
        self._socketio = socketio
        self._log = log_cb or (lambda _msg: None)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()
        self._correlator = MiniKillChainCorrelator(
            redis_client=redis_client, socketio=socketio, log_cb=self._log,
        )

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, scenario: str, speed: str = "demo") -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(scenario, speed), daemon=True
        )
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    def _emit(self, ev: dict) -> None:
        layer = ev.get("source_layer", "network")
        try:
            if self._redis is not None:
                payload = json.dumps(ev)
                self._redis.lpush(f"events:{layer}", payload)
                self._redis.ltrim(f"events:{layer}", 0, 999)
                self._redis.publish("security_events", payload)
        except Exception as exc:
            self._log(f"[redis-error] {exc}")
        try:
            if self._socketio is not None:
                self._socketio.emit("new_event", ev)
        except Exception as exc:
            self._log(f"[ws-error] {exc}")
        # Local kill-chain correlation — fires consolidated incident when
        # network/api/auth layers all observed for one source IP. Runs
        # independently of the standalone correlation-engine container.
        try:
            self._correlator.observe(ev)
        except Exception as exc:
            self._log(f"[correlator-error] {exc}")

    def _run(self, scenario: str, speed: str) -> None:
        delay = SPEED_MAP.get(speed, 1.0)
        scenarios = ["a", "b", "c"] if scenario == "all" else [scenario]
        src_ip = "10.0.2.4"
        try:
            for sc in scenarios:
                fn = _SCENARIOS.get(sc)
                if fn is None:
                    self._log(f"[skip] unknown scenario {sc!r}")
                    continue
                self._log(f"[stage] scenario={sc} speed={speed}")
                events = fn(src_ip)
                for i, ev in enumerate(events):
                    if self._cancel.is_set():
                        self._log("[cancel] simulation aborted")
                        return
                    self._emit(ev)
                    if i % 10 == 0 or i == len(events) - 1:
                        self._log(
                            f"[emit] {sc} {ev.get('event_type')} {ev.get('severity', {}).get('level')}"
                        )
                    jitter = random.uniform(0.6, 1.2)
                    time.sleep(max(0.05, delay * 0.05 * jitter))
                self._log(f"[done] scenario={sc} events={len(events)}")
            # Guarantee a consolidated kill chain incident at the end of a
            # full multi-scenario run. Bypasses cooldown so the demo always
            # produces the dashboard alert even if the natural correlator
            # already fired earlier in the run.
            if scenario == "all":
                fired = self._correlator.force_fire(src_ip)
                if fired:
                    self._log(
                        f"[kill-chain] FORCED end-of-run incident "
                        f"id={fired.get('incident_id')}"
                    )
                else:
                    self._log("[kill-chain] force_fire skipped (no events for IP)")
        except Exception as exc:
            self._log(f"[error] {exc}")
        finally:
            with self._lock:
                self._running = False


def detect_target_services_unreachable() -> bool:
    """Return True when the legacy attacker scenarios cannot work (no
    auth-service / api-server / web-app on this host). Used to default
    the launcher to in-process mode."""
    mode = os.environ.get("ATTACK_MODE", "auto").lower()
    if mode == "inprocess":
        return True
    if mode == "subprocess":
        return False
    # auto: in-process whenever localhost targets aren't reachable. Cheap
    # heuristic — Render free/starter has no extra services, so default
    # to in-process unless explicitly overridden.
    return os.environ.get("ATTACK_TARGETS_AVAILABLE", "0") != "1"
