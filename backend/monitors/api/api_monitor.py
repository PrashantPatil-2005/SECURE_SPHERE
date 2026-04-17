"""
api_monitor.py — SecuriSphere API Monitor

Subscribes to the Redis ``api_logs`` channel published by the api-server,
applies detection rules (SQL injection, path traversal, rate abuse,
endpoint enumeration, sensitive-data access), and publishes normalised
security events to ``security_events`` + persists them in ``events:api``.

Enhancement: each event is enriched with ``source_service_name`` and
``destination_service_name`` by querying the topology-collector, giving the
correlation engine service-name-aware correlation without IP guessing.
"""

import os
import time
import json
import logging
import uuid
import re
import threading
import requests
import redis
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, jsonify

# ── Structured logging ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","service":"api-monitor","level":"%(levelname)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("APIMonitor")


class Colors:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    RESET  = "\033[0m"


# ── Topology enrichment helper ───────────────────────────────────────────────

TOPOLOGY_URL = os.getenv("TOPOLOGY_URL", "http://topology-collector:5080")
_topology_cache: dict = {}          # service_name → node dict
_topology_cache_ts: float = 0.0
_TOPOLOGY_TTL = 15.0                # seconds


def _get_service_metadata(service_name: str) -> dict:
    """Return topology metadata for a service; cached for 15 s."""
    global _topology_cache, _topology_cache_ts
    now = time.monotonic()
    if now - _topology_cache_ts > _TOPOLOGY_TTL:
        try:
            resp = requests.get(
                f"{TOPOLOGY_URL}/topology/services", timeout=1.5
            )
            if resp.status_code == 200:
                _topology_cache = {s["service_name"]: s for s in resp.json()}
                _topology_cache_ts = now
        except Exception:
            pass
    return _topology_cache.get(service_name, {})


# ── Monitor class ────────────────────────────────────────────────────────────

class APIMonitor:
    def __init__(self) -> None:
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.target_api = os.getenv("TARGET_API", "http://api-server:5000")

        self.redis_client   = None
        self.redis_available = False
        self._connect_redis()

        # ── Detection patterns ─────────────────────────────────────────────
        self.sql_injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in [
                r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE)\b)",
                r"(\b(UNION)\s+(ALL\s+)?SELECT\b)",
                r"(\b(OR|AND)\s+[\'\"]?\d+[\'\"]?\s*=\s*[\'\"]?\d+)",
                r"(\b(OR|AND)\s+[\'\"]?[a-zA-Z]+[\'\"]?\s*=\s*[\'\"]?[a-zA-Z]+)",
                r"([\'\"];?\s*--)",
                r"([\'\"];\s*(DROP|DELETE|INSERT|UPDATE))",
                r"(/\*.*\*/)",
                r"(\bEXEC\s+)",
                r"(\bxp_cmdshell\b)",
                r"(\bWAITFOR\s+DELAY\b)",
                r"(\bBENCHMARK\s*\()",
                r"(\bSLEEP\s*\()",
            ]
        ]

        self.path_traversal_patterns = [
            re.compile(p, re.IGNORECASE) for p in [
                r"(\.\.\/)", r"(\.\.\\)",
                r"(%2e%2e%2f)", r"(%2e%2e\/)",
                r"(\.\.%2f)", r"(%2e%2e%5c)",
                r"(\/etc\/passwd)", r"(\/etc\/shadow)",
                r"(\/proc\/self)", r"(C:\\Windows)",
                r"(\/var\/log)", r"(\.\.%252f)",
            ]
        ]

        # ── Rate tracking ──────────────────────────────────────────────────
        self.request_tracker = defaultdict(lambda: {
            "count": 0, "first_request": None,
            "endpoints": set(), "window_start": None,
        })
        self.rate_window     = timedelta(seconds=60)
        self.rate_threshold  = 100
        self.enum_threshold  = 20

        logger.info('"API Monitor initialised"')

    # ── Redis connection ────────────────────────────────────────────────────

    def _connect_redis(self) -> None:
        for i in range(5):
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host, port=self.redis_port,
                    decode_responses=True,
                )
                if self.redis_client.ping():
                    self.redis_available = True
                    return
            except redis.ConnectionError:
                logger.warning('"Redis not ready, retrying..."')
                time.sleep(3)
        logger.error('"Redis unavailable after 5 attempts"')

    # ── Event factory ───────────────────────────────────────────────────────

    def create_event(
        self, event_type: str, severity_level: str, source_ip: str,
        target_endpoint: str, description: str, evidence: dict,
        confidence: float, tags: list, mitre: str,
    ) -> dict:
        severity_map = {"low": 20, "medium": 50, "high": 75, "critical": 95}
        category_map = {
            "sql_injection":       "exploitation",
            "path_traversal":      "exploitation",
            "rate_abuse":          "abuse",
            "endpoint_enumeration":"reconnaissance",
            "parameter_tampering": "exploitation",
            "sensitive_access":    "abuse",
        }

        # Topology enrichment — destination service is always api-server
        dst_meta  = _get_service_metadata("api-server")
        dst_cid   = dst_meta.get("container_id")
        dst_cname = dst_meta.get("container_name", "api-server")

        event = {
            "event_id":             str(uuid.uuid4()),
            "timestamp":            datetime.utcnow().isoformat() + "Z",
            "source_layer":         "api",
            "source_monitor":       "api_monitor_v1",
            "event_category":       category_map.get(event_type, "abuse"),
            "event_type":           event_type,
            "severity":             {"level": severity_level, "score": severity_map.get(severity_level, 50)},
            "source_entity":        {"ip": source_ip, "container_id": None, "container_name": None},
            "target_entity":        {
                "ip":        self.target_api,
                "port":      5000,
                "service":   "api-server",
                "endpoint":  target_endpoint,
                "username":  None,
            },
            # Service-name fields for correlation-engine enrichment
            "source_service_name":      None,       # attacker has no service name
            "destination_service_name": "api-server",
            "destination_container_id": dst_cid,
            "destination_container_name": dst_cname,
            "detection_details": {
                "method":      f"check_{event_type}",
                "confidence":  confidence,
                "description": description,
                "evidence":    evidence,
            },
            "correlation_tags": tags,
            "mitre_technique":  mitre,
        }
        return event

    # ── Publisher ───────────────────────────────────────────────────────────

    def publish_event(self, event: dict) -> None:
        sev = event["severity"]["level"]
        color = {
            "low":      Colors.GREEN,
            "medium":   Colors.YELLOW,
            "high":     Colors.YELLOW,
            "critical": Colors.RED,
        }.get(sev, Colors.RESET)

        print(
            f"{color}[!] [{sev.upper()}] {event['event_type']} "
            f"from {event['source_entity']['ip']} — "
            f"{event['detection_details']['description']}{Colors.RESET}"
        )

        if self.redis_available:
            try:
                js = json.dumps(event)
                self.redis_client.publish("security_events", js)
                self.redis_client.lpush("events:api", js)
                self.redis_client.ltrim("events:api", 0, 999)
            except Exception as exc:
                logger.error(f'"Redis publish failed: {exc}"')

    # ── Detection rules ─────────────────────────────────────────────────────

    def check_sql_injection(self, source_ip: str, endpoint: str, params: dict) -> bool:
        if not params:
            return False
        for param_name, param_value in params.items():
            if not param_value:
                continue
            for pattern in self.sql_injection_patterns:
                if pattern.search(str(param_value)):
                    pv  = str(param_value).upper()
                    sev = "critical" if ("DROP" in pv or "UNION" in pv) else "high"
                    self.publish_event(self.create_event(
                        "sql_injection", sev, source_ip, endpoint,
                        f"SQL injection in parameter '{param_name}'",
                        {"parameter": param_name, "payload": str(param_value)[:500],
                         "matched_pattern": pattern.pattern, "endpoint": endpoint},
                        0.92, ["exploitation", "sqli", "owasp_top10"], "T1190",
                    ))
                    return True
        return False

    def check_path_traversal(self, source_ip: str, endpoint: str, params: dict) -> bool:
        values = list(params.values()) if params else []
        values.append(endpoint)
        for value in values:
            if not value:
                continue
            for pattern in self.path_traversal_patterns:
                if pattern.search(str(value)):
                    sev = "critical" if any(
                        x in str(value) for x in ("/etc/passwd", "/etc/shadow")
                    ) else "high"
                    self.publish_event(self.create_event(
                        "path_traversal", sev, source_ip, endpoint,
                        f"Path traversal targeting {endpoint}",
                        {"payload": str(value)[:500], "matched_pattern": pattern.pattern},
                        0.88, ["exploitation", "path_traversal", "file_access"], "T1083",
                    ))
                    return True
        return False

    def check_rate_abuse(self, source_ip: str, endpoint: str) -> None:
        now     = datetime.now()
        tracker = self.request_tracker[source_ip]

        if tracker["window_start"] is None or (now - tracker["window_start"]) > self.rate_window:
            if tracker["count"] > self.rate_threshold:
                sev = "medium" if tracker["count"] < 200 else "high"
                self.publish_event(self.create_event(
                    "rate_abuse", sev, source_ip, endpoint,
                    f"{tracker['count']} requests from {source_ip} in 1 minute",
                    {"request_count": tracker["count"], "time_window_seconds": 60,
                     "unique_endpoints": len(tracker["endpoints"])},
                    0.80, ["abuse", "rate_limit"], "T1071",
                ))
            elif len(tracker["endpoints"]) > self.enum_threshold:
                self.publish_event(self.create_event(
                    "endpoint_enumeration", "medium", source_ip, endpoint,
                    f"API enumeration: {len(tracker['endpoints'])} unique endpoints",
                    {"unique_endpoints": len(tracker["endpoints"]), "total_requests": tracker["count"]},
                    0.75, ["reconnaissance", "api_enumeration"], "T1595",
                ))
            tracker["count"]     = 0
            tracker["endpoints"] = set()
            tracker["window_start"] = now
            tracker["first_request"] = now

        if tracker["first_request"] is None:
            tracker["first_request"] = now
            tracker["window_start"]  = now
        tracker["count"] += 1
        tracker["endpoints"].add(endpoint)

    def check_sensitive_access(
        self, source_ip: str, endpoint: str, params: dict, status_code: int
    ) -> bool:
        sensitive = {"/api/admin/config", "/api/admin/users/export"}
        if endpoint in sensitive:
            self.publish_event(self.create_event(
                "sensitive_access", "high", source_ip, endpoint,
                f"Sensitive endpoint {endpoint} accessed by {source_ip}",
                {"endpoint": endpoint, "status_code": status_code, "params": params},
                0.85, ["abuse", "sensitive_data"], "T1530",
            ))
            return True
        return False

    # ── Main processing loop ────────────────────────────────────────────────

    def process_api_log(self, log_data: str) -> None:
        try:
            data        = json.loads(log_data)
            source_ip   = data.get("source_ip",   "unknown")
            endpoint    = data.get("endpoint",    "/")
            params      = data.get("params",      {})
            status_code = data.get("status_code", 0)

            self.check_sql_injection(source_ip, endpoint, params)
            self.check_path_traversal(source_ip, endpoint, params)
            self.check_rate_abuse(source_ip, endpoint)
            self.check_sensitive_access(source_ip, endpoint, params, status_code)
        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error(f'"Error processing log: {exc}"')

    def run_monitor(self) -> None:
        logger.info('"Subscribing to Redis channel: api_logs"')
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("api_logs")
        for message in pubsub.listen():
            if message["type"] == "message":
                self.process_api_log(message["data"])


# ── Flask health endpoint ────────────────────────────────────────────────────

flask_app = Flask(__name__)
_monitor  = APIMonitor()


@flask_app.route("/monitor/health")
def health():
    return jsonify({
        "status":          "running",
        "service":         "api-monitor",
        "redis_connected": _monitor.redis_available,
        "timestamp":       datetime.utcnow().isoformat() + "Z",
    })


def _run_flask() -> None:
    flask_app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)


if __name__ == "__main__":
    threading.Thread(target=_run_flask, daemon=True).start()
    _monitor.run_monitor()
