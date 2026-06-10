"""
SecuriSphere — Data Service Layer
=================================
Owns the Redis connection state and the read/aggregation helpers shared by the
Flask app (``app.py``) and its blueprints. Centralising them here breaks the
historical ``from app import ...`` coupling and gives route modules a single
import surface for live data.

IMPORTANT — mutable globals:
    ``redis_client`` / ``redis_available`` are reassigned at runtime by
    ``connect_redis()``. Always access them by attribute (``services.redis_client``),
    never ``from services import redis_client`` — the latter captures the initial
    ``None`` and never observes the live connection.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import redis

logger = logging.getLogger("SecuriSphereBackend")

# --- Config -----------------------------------------------------------------
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
SERVER_START_TIME = datetime.utcnow()

# --- Shared engine helper (avg_mttd_seconds) --------------------------------
# Docker copies engine/ → /app/; local path is backend/engine/.
_here = Path(__file__).resolve()
for _cand in (_here.parent, _here.parent.parent / "engine"):
    if (_cand / "shared" / "pg_helpers.py").exists():
        sys.path.insert(0, str(_cand))
        break
try:
    from shared.pg_helpers import avg_mttd_seconds as _avg_mttd_from_postgres
except ImportError:
    def _avg_mttd_from_postgres():
        return None

# --- Redis connection state (mutated by connect_redis) ----------------------
redis_client = None
redis_available = False


def connect_redis():
    global redis_client, redis_available

    retry_count = 0
    while not redis_available:
        try:
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            if redis_client.ping():
                redis_available = True
                logger.info(f"✅ Connected to Redis at {REDIS_HOST}:{REDIS_PORT} successfully.")
        except redis.ConnectionError:
            retry_count += 1
            logger.warning(f"⏳ Redis not ready yet. Retrying in 2 seconds... (Attempt {retry_count})")
            time.sleep(2)


def _looks_like_ip(s: str) -> bool:
    if not s or not isinstance(s, str):
        return False
    parts = s.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


# --- Helper Functions -------------------------------------------------------

def get_events_from_redis(list_name, start=0, count=50):
    if not redis_available: return []
    try:
        raw_events = redis_client.lrange(list_name, start, start + count - 1)
        return [json.loads(e) for e in raw_events]
    except Exception as e:
        logger.error(f"Error reading {list_name}: {e}")
        return []

def get_all_events(limit=100):
    if not redis_available: return []
    # Merge events from all layers
    network = get_events_from_redis("events:network", 0, limit)
    api = get_events_from_redis("events:api", 0, limit)
    auth = get_events_from_redis("events:auth", 0, limit)

    all_events = network + api + auth
    # Sort by timestamp descending
    all_events.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return all_events[:limit]

def get_incidents(limit=50):
    if not redis_available: return []
    try:
        raw = redis_client.lrange('incidents', 0, limit - 1)
        return [json.loads(i) for i in raw]
    except Exception as e:
        logger.error(f"Error reading incidents: {e}")
        return []

def get_risk_scores():
    if not redis_available: return {}
    try:
        raw = redis_client.hgetall('risk_scores_current')
        return {k: json.loads(v) for k, v in raw.items()}
    except Exception as e:
        logger.error(f"Error reading risk scores: {e}")
        return {}

def get_latest_summary():
    default_summary = {
        "total_events_in_window": 0,
        "events_by_layer": {"network": 0, "api": 0, "auth": 0},
        "events_by_type": {},
        "top_sources": {},
        "active_incidents": 0,
        "risk_scores": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    if not redis_available: return default_summary
    try:
        raw = redis_client.get('latest_summary')
        return json.loads(raw) if raw else default_summary
    except:
        return default_summary

def _events_in_last_seconds(events, seconds=60):
    """Count events with timestamp inside the last N seconds."""
    cutoff = datetime.utcnow() - timedelta(seconds=seconds)
    n = 0
    for e in events:
        ts_str = e.get('timestamp')
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(str(ts_str).replace('Z', ''))
            if ts >= cutoff:
                n += 1
        except Exception:
            continue
    return n


def calculate_metrics():
    metrics = {
        "raw_events": {"network": 0, "api": 0, "auth": 0, "total": 0},
        "correlated_incidents": 0,
        "alert_reduction_percentage": 0,
        "active_risk_entities": 0,
        "events_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "events_by_type": defaultdict(int),
        "system_uptime": str(datetime.utcnow() - SERVER_START_TIME),
        "timestamp": datetime.utcnow().isoformat(),
        # Additional flat fields consumed by AlertReductionCard
        "total_raw_events": 0,
        "total_incidents": 0,
        "alert_reduction_ratio": 0.0,
        "events_per_minute": 0.0,
        "incidents_per_hour": 0.0,
        "avg_mttd_seconds": None,
        "detection_rate": 100.0,
        "active_campaigns": 0,
        "campaign_dedup_ratio": 0.0,
        "churn_scenario_completeness": None,
    }

    if not redis_available: return metrics

    try:
        # Counts
        metrics["raw_events"]["network"] = redis_client.llen('events:network')
        metrics["raw_events"]["api"] = redis_client.llen('events:api')
        metrics["raw_events"]["auth"] = redis_client.llen('events:auth')
        metrics["raw_events"]["total"] = sum(metrics["raw_events"].values())

        metrics["correlated_incidents"] = redis_client.llen('incidents')

        if metrics["raw_events"]["total"] > 0:
            metrics["alert_reduction_percentage"] = round(
                (1 - metrics["correlated_incidents"] / metrics["raw_events"]["total"]) * 100, 1
            )

        # Risk Entities
        risks = get_risk_scores()
        metrics["active_risk_entities"] = len([r for r in risks.values() if r.get('current_score', 0) > 30])

        # Severity & Types (Sample last 200 events)
        sample = get_all_events(200)
        for e in sample:
            sev = e.get('severity', {}).get('level', 'low')
            metrics["events_by_severity"][sev] += 1
            metrics["events_by_type"][e.get('event_type', 'unknown')] += 1

        # --- Flat KPI fields for AlertReductionCard -----------------------
        total_raw = metrics["raw_events"]["total"]
        total_inc = metrics["correlated_incidents"]
        metrics["total_raw_events"] = total_raw
        metrics["total_incidents"] = total_inc
        metrics["alert_reduction_ratio"] = (
            round((1 - total_inc / total_raw) * 100, 2) if total_raw > 0 else 0.0
        )

        # events per minute (last 60s across all layers)
        epm_sample = get_all_events(500)
        metrics["events_per_minute"] = round(_events_in_last_seconds(epm_sample, 60), 1)

        # incidents per hour — simple uptime projection from raw count
        uptime_sec = max((datetime.utcnow() - SERVER_START_TIME).total_seconds(), 1.0)
        metrics["incidents_per_hour"] = round(total_inc * 3600 / uptime_sec, 2)

        # average MTTD from Postgres kill_chains
        avg_mttd = _avg_mttd_from_postgres()
        if avg_mttd is not None:
            metrics["avg_mttd_seconds"] = avg_mttd

        # Campaign-level alert reduction (incidents collapsed into campaigns)
        try:
            import psycopg2
            pg_url = os.getenv("DATABASE_URL")
            if pg_url:
                conn = psycopg2.connect(pg_url)
            else:
                conn = psycopg2.connect(
                    host=os.getenv("POSTGRES_HOST", "database"),
                    port=int(os.getenv("POSTGRES_PORT", 5432)),
                    dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                    user=os.getenv("POSTGRES_USER", "securisphere_user"),
                    password=os.getenv("POSTGRES_PASSWORD", ""),
                )
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM campaigns WHERE status = 'active'")
                    active_camps = int(cur.fetchone()[0])
                    cur.execute("SELECT COALESCE(SUM(incident_count), 0) FROM campaigns")
                    camp_incidents = int(cur.fetchone()[0])
            conn.close()
            metrics["active_campaigns"] = active_camps
            if camp_incidents > 0 and total_inc > 0:
                metrics["campaign_dedup_ratio"] = round(
                    (1 - active_camps / max(total_inc, 1)) * 100, 1
                )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")

    return metrics

def calculate_event_stats(events):
    stats = {
        "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "by_type": defaultdict(int),
        "unique_sources": set()
    }
    for e in events:
        sev = e.get('severity', {}).get('level', 'low')
        if sev in stats["by_severity"]:
            stats["by_severity"][sev] += 1
        stats["by_type"][e.get('event_type', 'unknown')] += 1
        stats["unique_sources"].add(e.get('source_entity', {}).get('ip'))

    stats["unique_sources"] = len(stats["unique_sources"])
    return stats
