"""
proxy_monitor.py — consumes `events:proxy` Redis list populated by waf-proxy
(openresty lua logger), normalises to SecuriSphere event schema, and
republishes to the `security_events` pub/sub channel so the existing
correlation engine ingests WAF blocks like any other signal.

Also pushes a copy to `events:proxy:normalised` for historical lookup.
"""

import os
import time
import json
import uuid
import logging
import redis
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("ProxyMonitor")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Map waf rule -> MITRE technique id
MITRE_BY_RULE = {
    "sqli":       "T1190",
    "xss":        "T1059.007",
    "traversal":  "T1083",
    "cmd_inj":    "T1059",
    "scanner":    "T1595",
    "rate_limit": "T1498",
}

SEVERITY_BY_RULE = {
    "sqli":       ("high",     80),
    "xss":        ("medium",   60),
    "traversal":  ("high",     75),
    "cmd_inj":    ("critical", 90),
    "scanner":    ("medium",   55),
    "rate_limit": ("low",      35),
}


def connect_redis():
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            r.ping()
            log.info("Connected to Redis %s:%s", REDIS_HOST, REDIS_PORT)
            return r
        except Exception as e:
            log.warning("Redis not ready (%s) — retrying", e)
            time.sleep(2)


def build_event(raw: dict) -> dict:
    rule = raw.get("rule") or "-"
    blocked = bool(raw.get("blocked"))
    sev_level, sev_score = SEVERITY_BY_RULE.get(rule, ("info", 20))
    if not blocked:
        sev_level, sev_score = "info", 10

    event_type = f"waf_{rule}_blocked" if blocked else "waf_allow"
    return {
        "event_id":        str(uuid.uuid4()),
        "timestamp":       raw.get("ts") or (datetime.utcnow().isoformat() + "Z"),
        "source_layer":    "proxy",
        "source_monitor":  "proxy_monitor_v1",
        "event_category":  "intrusion" if blocked else "traffic",
        "event_type":      event_type,
        "severity": {
            "level": sev_level,
            "score": sev_score,
        },
        "source_entity": {
            "ip":             raw.get("remote"),
            "container_id":   None,
            "container_name": None,
            "user_agent":     raw.get("ua"),
        },
        "target_entity": {
            "ip":       None,
            "port":     None,
            "service":  "waf-proxy",
            "endpoint": raw.get("uri"),
            "username": None,
        },
        "detection_details": {
            "method":      f"waf_rule_{rule}",
            "confidence":  0.95 if blocked else 0.2,
            "description": f"WAF {'blocked' if blocked else 'allowed'} request ({rule})",
            "evidence": {
                "method":   raw.get("method"),
                "uri":      raw.get("uri"),
                "status":   raw.get("status"),
                "referer":  raw.get("referer"),
                "host":     raw.get("host"),
                "upstream": raw.get("upstream"),
            },
        },
        "correlation_tags": ["waf", rule] + (["blocked"] if blocked else []),
        "mitre_technique":  MITRE_BY_RULE.get(rule),
    }


def run():
    r = connect_redis()
    log.info("proxy-monitor started. Tailing events:proxy …")
    blocked_seen = 0
    while True:
        try:
            # BRPOP blocks until item available
            item = r.brpop("events:proxy", timeout=5)
            if not item:
                continue
            _, raw_json = item
            try:
                raw = json.loads(raw_json)
            except Exception:
                continue

            evt = build_event(raw)

            # Publish on pub/sub + store in dedicated list
            r.publish("security_events", json.dumps(evt))
            r.lpush("events:proxy:normalised", json.dumps(evt))
            r.ltrim("events:proxy:normalised", 0, 999)

            if evt["severity"]["level"] in ("high", "critical", "medium"):
                blocked_seen += 1
                if blocked_seen % 10 == 0:
                    log.info("WAF blocks forwarded: %d", blocked_seen)

        except redis.ConnectionError:
            log.warning("Redis dropped — reconnecting")
            r = connect_redis()
        except Exception as e:
            log.error("proxy_monitor loop error: %s", e)
            time.sleep(1)


if __name__ == "__main__":
    run()
