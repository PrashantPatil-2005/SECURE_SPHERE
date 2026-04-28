"""
browser_monitor.py — SecuriSphere Browser Monitor (Phase 1)

Receives browser-side events from the ShopSphere agent.js, validates the
schema, looks up the source ``site_id`` against the ``registered_sites``
table, enriches each event into a normalized SecuriSphere security event,
and publishes to the ``security_events`` Redis channel consumed by the
correlation engine.

Runs as a Flask app on port 5090 with permissive CORS so the browser
agent (served by the nginx web-app at :8080) can POST directly. This
module is the new fourth monitor layer alongside network / api / auth.
"""

import os
import json
import logging
import uuid
from datetime import datetime

import redis
import psycopg2
from flask import Flask, request, jsonify

from register_site import bp as register_bp, init_db

# ── logging (matches existing monitors' pseudo-JSON format) ────────────────

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","service":"browser-monitor","level":"%(levelname)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("BrowserMonitor")


# ── config ─────────────────────────────────────────────────────────────────

REDIS_HOST    = os.getenv("REDIS_HOST", "redis")
REDIS_PORT    = int(os.getenv("REDIS_PORT", 6379))
REDIS_CHANNEL = os.getenv("BROWSER_EVENTS_CHANNEL", "security_events")
MONITOR_PORT  = int(os.getenv("BROWSER_MONITOR_PORT", 5090))

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "database")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.getenv("POSTGRES_USER", "securisphere")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "securisphere")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "securisphere")


# ── validation contract ───────────────────────────────────────────────────

REQUIRED_FIELDS  = {"event_type", "source_layer", "site_id", "target_entity", "severity"}
ALLOWED_SEVERITY = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}


# ── connection helpers ─────────────────────────────────────────────────────

def get_redis() -> redis.Redis:
    """Return a connected (decoded) Redis client. Raises on failure so the
    caller can return 503 rather than silently dropping events."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_pg_conn():
    """Open a new PostgreSQL connection for a single lookup. Kept short-lived
    to avoid holding pool state inside this lightweight monitor."""
    return psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
    )


# ── validation ─────────────────────────────────────────────────────────────

def validate_event(ev: dict):
    """Return (ok, error_msg). Checks required fields and severity enum.
    Does not verify the site_id here — that's a DB lookup, done separately."""
    if not isinstance(ev, dict):
        return False, "event must be a JSON object"
    missing = REQUIRED_FIELDS - ev.keys()
    if missing:
        return False, f"missing fields: {sorted(missing)}"
    if ev["severity"] not in ALLOWED_SEVERITY:
        return False, f"invalid severity: {ev['severity']}"
    if ev.get("correlation_tags") is not None and not isinstance(ev["correlation_tags"], list):
        return False, "correlation_tags must be a list"
    return True, ""


def site_is_registered(site_id: str) -> bool:
    """Look up a site_id in registered_sites. Returns False on any DB error
    so unknown sites are dropped rather than crashing the monitor."""
    try:
        with get_pg_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM registered_sites WHERE site_id = %s LIMIT 1",
                (site_id,),
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.warning(f"site registry lookup failed: {e}")
        return False


# ── enrichment ─────────────────────────────────────────────────────────────

def enrich(ev: dict, source_ip: str) -> dict:
    """Normalize a raw browser event into a SecuriSphere security event.

    Adds event_id / timestamp / source_monitor / source_ip and the standard
    ``publisher`` + ``published`` bookkeeping fields. The ``source_layer``
    stays as ``browser-agent`` so the correlation engine can key on it.
    """
    return {
        **ev,
        "event_id":                 str(uuid.uuid4()),
        "timestamp":                ev.get("timestamp") or datetime.utcnow().isoformat() + "Z",
        "source_monitor":           "browser-monitor",
        "source_ip":                source_ip,
        "target_service":           "web-app",
        "destination_service_name": "web-app",
        "publisher":                "events-api",
        "published":                True,
    }


# ── Flask app ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.register_blueprint(register_bp)


@app.after_request
def _cors(resp):
    """Permissive CORS so the browser agent (served from :8080) can POST
    events cross-origin to the monitor on :5090."""
    resp.headers["Access-Control-Allow-Origin"]  = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/health", methods=["GET"])
def health():
    """Liveness probe used by ``make health`` and docker-compose healthchecks."""
    return jsonify({"status": "ok", "service": "browser-monitor", "port": MONITOR_PORT})


@app.route("/api/ingest", methods=["POST", "OPTIONS"])
def ingest():
    """Accept a batch of browser events.

    Body: ``{"events": [ {...}, {...} ]}`` or a bare list.
    Returns: ``{"published": N, "skipped": M}``.
    """
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    if isinstance(payload, list):
        events = payload
    else:
        events = payload.get("events") or []

    if not isinstance(events, list):
        return jsonify({"error": "events must be a list"}), 400

    try:
        r = get_redis()
        r.ping()
    except Exception as e:
        logger.error(f"redis unavailable: {e}")
        return jsonify({"error": "redis unavailable"}), 503

    source_ip = request.headers.get(
        "X-Forwarded-For", request.remote_addr or "unknown"
    ).split(",")[0].strip()

    published, skipped = 0, 0
    for ev in events:
        ok, err = validate_event(ev)
        if not ok:
            logger.info(f"skipped event: {err}")
            skipped += 1
            continue
        if not site_is_registered(ev["site_id"]):
            logger.info(f"unregistered site_id: {ev['site_id']}")
            skipped += 1
            continue

        enriched = enrich(ev, source_ip)
        try:
            r.publish(REDIS_CHANNEL, json.dumps(enriched))
            r.lpush("events:browser", json.dumps(enriched))
            r.ltrim("events:browser", 0, 999)
            published += 1
        except Exception as e:
            logger.error(f"redis publish failed: {e}")
            skipped += 1

    logger.info(f"ingest batch complete: published={published} skipped={skipped}")
    return jsonify({"published": published, "skipped": skipped})


if __name__ == "__main__":
    try:
        init_db()
    except Exception as e:
        logger.warning(f"init_db failed (will retry on register): {e}")
    app.run(host="0.0.0.0", port=MONITOR_PORT)
