"""
auth_monitor.py — SecuriSphere Auth Monitor

Subscribes to the Redis ``auth_events`` channel published by the auth-service
and detects: brute force, credential stuffing, suspicious logins (post-failure
success), and lockout storms.

Enhancement: each event carries ``source_service_name`` / ``destination_service_name``
fields populated from the topology-collector so the correlation engine can
build service-level kill-chain paths.
"""

import os
import time
import json
import logging
import uuid
import threading
import requests
import redis
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, jsonify

# ── Structured logging ──────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","service":"auth-monitor","level":"%(levelname)s","msg":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("AuthMonitor")


class Colors:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    RESET  = "\033[0m"


# ── Topology enrichment helper ───────────────────────────────────────────────

TOPOLOGY_URL = os.getenv("TOPOLOGY_URL", "http://topology-collector:5080")
_topology_cache: dict = {}
_topology_cache_ts: float = 0.0
_TOPOLOGY_TTL = 15.0


def _get_service_metadata(service_name: str) -> dict:
    global _topology_cache, _topology_cache_ts
    now = time.monotonic()
    if now - _topology_cache_ts > _TOPOLOGY_TTL:
        try:
            resp = requests.get(f"{TOPOLOGY_URL}/topology/services", timeout=1.5)
            if resp.status_code == 200:
                _topology_cache = {s["service_name"]: s for s in resp.json()}
                _topology_cache_ts = now
        except Exception:
            pass
    return _topology_cache.get(service_name, {})


# ── Monitor class ────────────────────────────────────────────────────────────

class AuthMonitor:
    def __init__(self) -> None:
        self.redis_host = os.getenv("REDIS_HOST", "redis")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))

        self.redis_client    = None
        self.redis_available = False
        self._connect_redis()

        # Per-IP failure state
        self.ip_failures = defaultdict(lambda: {
            "count": 0, "usernames": set(),
            "first_attempt": None, "last_attempt": None,
        })
        # Per-user failure state
        self.user_failures = defaultdict(lambda: {
            "count": 0, "source_ips": set(), "first_attempt": None,
        })
        # Tracks failures preceding a success (for suspicious_login detection)
        self.success_after_failure = defaultdict(lambda: {
            "previous_failures": 0, "failure_ips": set(),
        })
        # Per-IP lockout storm tracking
        self.lockout_tracker = defaultdict(lambda: {
            "count": 0, "first_lockout": None, "usernames": set(),
        })
        # Alert cooldowns keyed by "<ip>_<detection_type>"
        self.alert_cooldowns: dict = defaultdict(lambda: None)

        logger.info('"Auth Monitor initialised"')

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
        username: str, description: str, evidence: dict,
        confidence: float, tags: list, mitre: str,
    ) -> dict:
        severity_map = {"low": 20, "medium": 50, "high": 75, "critical": 95}

        # Topology enrichment — destination service is always auth-service
        dst_meta  = _get_service_metadata("auth-service")
        dst_cid   = dst_meta.get("container_id")
        dst_cname = dst_meta.get("container_name", "auth-service")

        event = {
            "event_id":       str(uuid.uuid4()),
            "timestamp":      datetime.utcnow().isoformat() + "Z",
            "source_layer":   "auth",
            "source_monitor": "auth_monitor_v1",
            "event_category": "credential_attack",
            "event_type":     event_type,
            "severity":       {"level": severity_level, "score": severity_map.get(severity_level, 50)},
            "source_entity":  {"ip": source_ip, "container_id": None, "container_name": None},
            "target_entity":  {
                "ip":       None,
                "port":     5001,
                "service":  "auth-service",
                "endpoint": "/auth/login",
                "username": username,
            },
            # Service-name fields for correlation-engine enrichment
            "source_service_name":        None,
            "destination_service_name":   "auth-service",
            "destination_container_id":   dst_cid,
            "destination_container_name": dst_cname,
            "detection_details": {
                "method":      f"detect_{event_type}",
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
            f"for user {event['target_entity']['username']} — "
            f"{event['detection_details']['description']}{Colors.RESET}"
        )

        if self.redis_available:
            try:
                js = json.dumps(event)
                self.redis_client.publish("security_events", js)
                self.redis_client.lpush("events:auth", js)
                self.redis_client.ltrim("events:auth", 0, 999)
            except Exception as exc:
                logger.error(f'"Redis publish failed: {exc}"')

    # ── Detection logic ─────────────────────────────────────────────────────

    def detect_brute_force(self, source_ip: str, username: str) -> None:
        now     = datetime.now()
        tracker = self.ip_failures[source_ip]

        if tracker["first_attempt"] and (now - tracker["first_attempt"]).total_seconds() > 120:
            tracker["count"]     = 0
            tracker["usernames"] = set()
            tracker["first_attempt"] = now

        if not tracker["first_attempt"]:
            tracker["first_attempt"] = now

        tracker["count"] += 1
        tracker["usernames"].add(username)
        tracker["last_attempt"] = now

        if tracker["count"] < 5:
            return

        ck = f"{source_ip}_brute_force"
        if self.alert_cooldowns[ck] and (now - self.alert_cooldowns[ck]).total_seconds() < 60:
            return

        time_span = (now - tracker["first_attempt"]).total_seconds()
        sev = "high" if tracker["count"] < 10 else "critical"

        self.publish_event(self.create_event(
            "brute_force", sev, source_ip, username,
            f"Brute force: {tracker['count']} failed attempts from {source_ip}",
            {
                "failed_attempts":    tracker["count"],
                "time_window_seconds": round(time_span, 1),
                "targeted_usernames": list(tracker["usernames"]),
            },
            min(0.7 + tracker["count"] * 0.03, 0.98),
            ["credential_attack", "brute_force"], "T1110",
        ))
        self.alert_cooldowns[ck] = now

    def detect_credential_stuffing(self, source_ip: str, username: str) -> None:
        tracker = self.ip_failures[source_ip]
        now     = datetime.now()

        if len(tracker["usernames"]) < 5:
            return

        ck = f"{source_ip}_cred_stuffing"
        if self.alert_cooldowns[ck] and (now - self.alert_cooldowns[ck]).total_seconds() < 300:
            return

        if not tracker["first_attempt"]:
            return
        time_span = (now - tracker["first_attempt"]).total_seconds()
        if time_span > 300:
            return

        self.publish_event(self.create_event(
            "credential_stuffing", "high", source_ip, username,
            f"Credential stuffing: {len(tracker['usernames'])} users tried from {source_ip}",
            {
                "unique_usernames": len(tracker["usernames"]),
                "usernames":        sorted(list(tracker["usernames"])),
                "total_attempts":   tracker["count"],
            },
            0.88, ["credential_attack", "credential_stuffing", "automated"], "T1110.004",
        ))
        self.alert_cooldowns[ck] = now

    def detect_suspicious_login(self, source_ip: str, username: str) -> None:
        saf = self.success_after_failure[username]
        if saf["previous_failures"] >= 3:
            self.publish_event(self.create_event(
                "suspicious_login", "critical", source_ip, username,
                f"Suspicious login for '{username}' after {saf['previous_failures']} failures",
                {
                    "previous_failures": saf["previous_failures"],
                    "failure_ips":       sorted(list(saf["failure_ips"])),
                    "success_ip":        source_ip,
                    "possible_compromise": True,
                },
                0.95, ["credential_attack", "account_takeover"], "T1078",
            ))
        # Always reset tracking after a successful login
        saf["previous_failures"] = 0
        saf["failure_ips"]       = set()

    def detect_lockout_storm(self, source_ip: str, username: str) -> None:
        now     = datetime.now()
        tracker = self.lockout_tracker[source_ip]

        if tracker["first_lockout"] and (now - tracker["first_lockout"]).total_seconds() > 300:
            tracker["count"]     = 0
            tracker["usernames"] = set()
            tracker["first_lockout"] = now

        if not tracker["first_lockout"]:
            tracker["first_lockout"] = now

        tracker["count"] += 1
        tracker["usernames"].add(username)

        if tracker["count"] >= 3:
            self.publish_event(self.create_event(
                "lockout_storm", "critical", source_ip, username,
                f"Lockout storm: {tracker['count']} accounts locked by {source_ip}",
                {
                    "lockout_count":    tracker["count"],
                    "locked_accounts":  sorted(list(tracker["usernames"])),
                },
                0.93, ["credential_attack", "lockout_storm", "denial_of_service"], "T1110",
            ))
            tracker["count"] = 0   # reset to allow re-alerting on next batch

    # ── Main processing loop ────────────────────────────────────────────────

    def process_event(self, event_data: str) -> None:
        try:
            data       = json.loads(event_data)
            source_ip  = data.get("source_ip", "unknown")
            username   = data.get("username",  "unknown")
            event_type = data.get("event_type")

            if event_type == "login_failure":
                self.success_after_failure[username]["previous_failures"] += 1
                self.success_after_failure[username]["failure_ips"].add(source_ip)
                self.detect_brute_force(source_ip, username)
                self.detect_credential_stuffing(source_ip, username)

            elif event_type == "login_success":
                self.detect_suspicious_login(source_ip, username)

            elif event_type == "account_lockout":
                self.detect_lockout_storm(source_ip, username)

        except json.JSONDecodeError:
            pass
        except Exception as exc:
            logger.error(f'"Error processing event: {exc}"')

    def run_monitor(self) -> None:
        logger.info('"Subscribing to Redis channel: auth_events"')
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("auth_events")
        for message in pubsub.listen():
            if message["type"] == "message":
                self.process_event(message["data"])


# ── Flask health endpoint ────────────────────────────────────────────────────

flask_app = Flask(__name__)
_monitor  = AuthMonitor()


@flask_app.route("/monitor/health")
def health():
    return jsonify({
        "status":          "running",
        "service":         "auth-monitor",
        "redis_connected": _monitor.redis_available,
        "timestamp":       datetime.utcnow().isoformat() + "Z",
    })


@flask_app.route("/monitor/reset", methods=["POST"])
def reset():
    """
    Flush in-memory per-IP brute-force tracker + alert cooldowns. Used by
    the Phase 16 trial runner so each scenario trial starts with a clean
    detector state; otherwise the 60 s brute_force alert cooldown + 120 s
    failure window carry state across trials and produce flaky results.
    """
    _monitor.ip_failures.clear()
    _monitor.alert_cooldowns.clear()
    return jsonify({"status": "reset", "service": "auth-monitor"})


def _run_flask() -> None:
    flask_app.run(host="0.0.0.0", port=5060, debug=False, use_reloader=False)


if __name__ == "__main__":
    threading.Thread(target=_run_flask, daemon=True).start()
    _monitor.run_monitor()
