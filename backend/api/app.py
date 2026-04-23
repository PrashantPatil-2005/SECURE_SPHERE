import os
import re
import sys
import time
import json
import uuid
import threading
import subprocess
import logging
from pathlib import Path
import redis
import requests
from datetime import datetime, timedelta
from collections import defaultdict, deque
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from gevent import monkey
# Patch gevent
monkey.patch_all()

from auth import auth_bp
from topology_checks import bp as topology_checks_bp

# --- MITRE ATT&CK static map (shared with correlation engine) ---------------
# Docker: copied to /app/mitre/; local: lives at backend/engine/mitre/.
_here = Path(__file__).resolve()
for _cand in (_here.parent, _here.parent.parent / "engine"):
    if (_cand / "mitre" / "mitre_map.py").exists():
        sys.path.insert(0, str(_cand))
        break
try:
    from mitre.mitre_map import MITRE_MAP, TACTIC_ORDER
except ImportError:
    MITRE_MAP, TACTIC_ORDER = {}, []


# ... (logging setup) ...

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SecuriSphereBackend")
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Flask Setup
if os.getenv("ALLOW_LOCALHOST_UPSTREAM", "0") == "1":
    logger.warning("ALLOW_LOCALHOST_UPSTREAM=1 — SSRF loopback guard disabled. Demo only; never in production.")

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(topology_checks_bp)

# Redis Config
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
APP_PORT = int(os.getenv('PORT', os.getenv('BACKEND_PORT', 8000)))
SERVER_START_TIME = datetime.utcnow()

# Redis Connection
redis_client = None
redis_available = False

def connect_redis():
    global redis_client, redis_available
    import sys
    
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

# --- Helper Functions ---

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


def _avg_mttd_from_postgres():
    """Pull AVG(mttd_seconds) from kill_chains. Returns None on failure."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor() as cur:
            cur.execute("SELECT AVG(mttd_seconds) FROM kill_chains WHERE mttd_seconds IS NOT NULL")
            row = cur.fetchone()
        conn.close()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    except Exception as exc:
        logger.debug("avg_mttd postgres lookup failed: %s", exc)
    return None


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

# --- Middleware ---

@app.before_request
def log_request():
    if request.path != '/api/health':
        pass # Too noisy

@app.after_request
def add_headers(response):
    response.headers['X-SecuriSphere-Version'] = '1.0.0'
    return response

# --- REST API Endpoints ---

@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "securisphere-backend",
        "redis_connected": redis_available,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

@app.route('/api/dashboard/summary')
def dashboard_summary():
    metrics = calculate_metrics()
    return jsonify({
        "status": "success",
        "data": {
            "summary": get_latest_summary(),
            "metrics": {
                "raw_events": metrics["raw_events"],
                "correlated_incidents": metrics["correlated_incidents"],
                "alert_reduction_percentage": metrics["alert_reduction_percentage"],
                "active_threats": metrics["active_risk_entities"],
                "critical_events": metrics["events_by_severity"]["critical"]
            },
            "recent_incidents": get_incidents(5),
            "risk_scores": get_risk_scores(),
            "events_by_layer": metrics["raw_events"], # simplified
            "timestamp": datetime.utcnow().isoformat()
        }
    })

@app.route('/api/events')
def get_events():
    layer = request.args.get('layer', 'all')
    limit = min(int(request.args.get('limit', 50)), 500)
    severity = request.args.get('severity', 'all')
    ev_type = request.args.get('event_type')
    
    if layer == 'all':
        events = get_all_events(limit) # This limits first, then filters. Might need optimization for deep filtering
        # Optimize: get more then filter? For now, fetch limit*2 to allow some filtering space
        if severity != 'all' or ev_type:
            events = get_all_events(limit * 5) 
    else:
        events = get_events_from_redis(f"events:{layer}", 0, limit * 5)
        
    # Filtering
    filtered = []
    for e in events:
        if severity != 'all' and e.get('severity', {}).get('level') != severity:
            continue
        if ev_type and e.get('event_type') != ev_type:
            continue
        filtered.append(e)
        
    # Apply limit after filtering
    final_events = filtered[:limit]
    
    return jsonify({
        "status": "success",
        "data": {
            "events": final_events,
            "count": len(final_events),
            "total_available": {
                "network": redis_client.llen("events:network") if redis_available else 0,
                "api": redis_client.llen("events:api") if redis_available else 0,
                "auth": redis_client.llen("events:auth") if redis_available else 0
            },
            "filters_applied": {
                "layer": layer,
                "severity": severity,
                "event_type": ev_type,
                "limit": limit
            },
            "stats": calculate_event_stats(final_events)
        }
    })

@app.route('/api/events/<event_id>')
def get_single_event(event_id):
    # Search in all lists (expensive but necessary without index)
    # Optimization: Search recent 1000 first
    all_ev = get_all_events(1000)
    for e in all_ev:
        if e.get('event_id') == event_id:
            return jsonify({"status": "success", "data": {"event": e}})
    return jsonify({"status": "error", "message": "Event not found"}), 404

def _read_incident_status_redis(incident_id):
    """Return (status, note, updated_at) from Redis hash, or (None, None, None)."""
    if not redis_available or not incident_id:
        return None, None, None
    try:
        raw = redis_client.hgetall(f"incident_status:{incident_id}")
        if not raw:
            return None, None, None
        return raw.get('status'), raw.get('note'), raw.get('updated_at')
    except Exception:
        return None, None, None


def _write_incident_status_redis(incident_id, status, note):
    updated_at = datetime.utcnow().isoformat()
    if redis_available:
        try:
            redis_client.hset(
                f"incident_status:{incident_id}",
                mapping={
                    "status": status,
                    "note": note or "",
                    "updated_at": updated_at,
                },
            )
        except Exception as exc:
            logger.warning("redis status write failed: %s", exc)
    return updated_at


@app.route('/api/incidents')
def list_incidents():
    limit = min(int(request.args.get('limit', 20)), 100)
    incidents = get_incidents(limit)

    # Batch read statuses from PostgreSQL kill_chains (legacy source of truth)
    pg_status_map, pg_note_map = {}, {}
    try:
        import psycopg2
        import psycopg2.extras
        incident_ids = [i.get('incident_id') for i in incidents if i.get('incident_id')]
        if incident_ids:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT incident_id, status, analyst_note FROM kill_chains "
                    "WHERE incident_id = ANY(%s)",
                    (incident_ids,),
                )
                for row in cur.fetchall():
                    key = str(row['incident_id'])
                    pg_status_map[key] = row['status']
                    pg_note_map[key] = row.get('analyst_note')
            conn.close()
    except Exception:
        pass

    # Merge in Redis override (PATCH writes to Redis hash incident_status:{id})
    for inc in incidents:
        iid = inc.get('incident_id')
        redis_status, redis_note, _ = _read_incident_status_redis(iid)
        inc['status'] = redis_status or pg_status_map.get(iid) or 'active'
        inc['analyst_note'] = redis_note or pg_note_map.get(iid) or inc.get('analyst_note')

    return jsonify({
        "status": "success",
        "data": {
            "incidents": incidents,
            "count": len(incidents),
            "total_available": redis_client.llen("incidents") if redis_available else 0
        }
    })

@app.route('/api/incidents/<incident_id>')
def get_incident(incident_id):
    incidents = get_incidents(100)
    for i in incidents:
        if i.get('incident_id') == incident_id:
            return jsonify({"status": "success", "data": {"incident": i}})
    return jsonify({"status": "error", "message": "Incident not found"}), 404

@app.route('/api/risk-scores')
def list_risk_scores():
    risks = get_risk_scores()

    # Normalise each entry so callers can rely on `entity` / `entity_type`
    # regardless of whether the key is a service name or a fallback IP.
    normalised = {}
    for key, r in risks.items():
        entity_type = r.get('entity_type') or ('service' if not _looks_like_ip(key) else 'ip')
        normalised[key] = {
            **r,
            "entity":      r.get('entity') or key,
            "entity_type": entity_type,
            "source_ip":   r.get('source_ip') or (key if entity_type == 'ip' else None),
        }

    summary = {
        "total_entities":   len(normalised),
        "service_count":    sum(1 for v in normalised.values() if v["entity_type"] == "service"),
        "ip_count":         sum(1 for v in normalised.values() if v["entity_type"] == "ip"),
        "critical_count":   0,
        "threatening_count":0,
        "suspicious_count": 0,
        "normal_count":     0,
    }

    for r in normalised.values():
        score = r.get('current_score', 0)
        if score >= 90: summary["critical_count"] += 1
        elif score >= 70: summary["threatening_count"] += 1
        elif score >= 30: summary["suspicious_count"] += 1
        else: summary["normal_count"] += 1

    return jsonify({
        "status": "success",
        "data": {
            "risk_scores": normalised,
            "summary": summary
        }
    })

@app.route('/api/risk-scores/<ip>')
def get_ip_risk(ip):
    risks = get_risk_scores()
    if ip in risks:
        return jsonify({"status": "success", "data": risks[ip]})
    return jsonify({"status": "error", "message": "Risk score not found"}), 404

@app.route('/api/metrics')
def system_metrics():
    return jsonify({
        "status": "success", 
        "data": calculate_metrics()
    })

@app.route('/api/metrics/timeline')
def metrics_timeline():
    # Mocking timeline for now as we don't have time-series DB
    # In real impl, we would bucket recent events
    minutes = int(request.args.get('minutes', 30))
    events = get_all_events(500) # Get recent
    
    timeline = defaultdict(lambda: {"timestamp": "", "network": 0, "api": 0, "auth": 0, "total": 0})
    now = datetime.utcnow()
    
    # Init buckets
    for i in range(minutes):
        t = (now - timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:00Z")
        timeline[t]["timestamp"] = t
        
    for e in events:
        ts_str = e.get('timestamp')
        if ts_str:
            try:
                # Truncate to minute
                ts = datetime.fromisoformat(ts_str.replace('Z', ''))
                key = ts.strftime("%Y-%m-%dT%H:%M:00Z")
                if key in timeline:
                    layer = e.get('source_layer', 'other')
                    timeline[key][layer] += 1
                    timeline[key]['total'] += 1
            except:
                pass
                
    return jsonify({
        "status": "success",
        "data": {
            "timeline": sorted([v for v in timeline.values()], key=lambda x: x['timestamp']),
            "time_range": {"minutes": minutes}
        }
    })

@app.route('/api/events/latest')
def latest_events():
    return jsonify({
        "status": "success",
        "data": {
            "latest": {
                "network": (get_events_from_redis("events:network", 0, 1) or [None])[0],
                "api": (get_events_from_redis("events:api", 0, 1) or [None])[0],
                "auth": (get_events_from_redis("events:auth", 0, 1) or [None])[0]
            }
        }
    })

@app.route('/api/events/clear', methods=['POST'])
def clear_events():
    if redis_available:
        redis_client.delete("events:network", "events:api", "events:auth", "incidents", "risk_scores_current", "latest_summary")
    
    # Also clear PostgreSQL incidents (kill_chains)
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE kill_chains RESTART IDENTITY")
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error clearing PostgreSQL kill_chains: {e}")

    return jsonify({
        "status": "success", 
        "message": "All events and incidents cleared (Redis + Postgres)",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/system/status')
def system_status():
    status = {
        "redis": {"connected": redis_available},
        "monitors": {},
        "correlation_engine": {"active": False, "incidents": 0},
        "total_events": 0,
        "uptime_seconds": (datetime.utcnow() - SERVER_START_TIME).seconds
    }

    if redis_available:
        status["redis"]["ping"] = "PONG"

        # Per-monitor liveness: count + latest-event freshness (<=120s => active)
        monitors = ["network", "api", "auth", "browser"]
        now_ts = datetime.utcnow()
        for m in monitors:
            last_list = get_events_from_redis(f"events:{m}", 0, 1) or []
            last = last_list[0] if last_list else {}
            last_ts_raw = last.get('timestamp') if isinstance(last, dict) else None
            fresh = False
            if last_ts_raw:
                try:
                    s = str(last_ts_raw)
                    dt = datetime.fromisoformat(s.replace('Z', '+00:00')) if ('Z' in s or '+' in s[10:]) else datetime.fromisoformat(s)
                    age = (now_ts - dt.replace(tzinfo=None)).total_seconds()
                    fresh = age <= 120
                except Exception:
                    fresh = False
            count = redis_client.llen(f"events:{m}")
            status["monitors"][m] = {
                "active": bool(fresh or count > 0),
                "last_event": last_ts_raw,
                "event_count": count,
            }
            status["total_events"] += count

        status["correlation_engine"]["incidents"] = redis_client.llen("incidents")

    # Ping correlation engine /health (container DNS name)
    try:
        engine_url = os.getenv("SECURISPHERE_ENGINE_URL", "http://correlation-engine:5070")
        r = requests.get(f"{engine_url}/engine/health", timeout=1.5)
        if r.ok:
            body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
            status["correlation_engine"]["active"] = True
            status["correlation_engine"]["uptime"] = body.get("uptime") or body.get("uptime_seconds")
        else:
            status["correlation_engine"]["active"] = False
            status["correlation_engine"]["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        status["correlation_engine"]["active"] = False
        status["correlation_engine"]["error"] = str(e)[:120]

    return jsonify({"status": "success", "data": status})

# ============================================================
# WAF / Reverse-proxy configuration
# ============================================================

from urllib.parse import urlparse

WAF_CONFIG_DIR     = os.getenv("WAF_CONFIG_DIR", "/etc/waf/conf.d")
WAF_CONFIG_FILE    = os.path.join(WAF_CONFIG_DIR, "runtime.json")
WAF_ADMIN_URL      = os.getenv("WAF_ADMIN_URL", "http://waf-proxy:8081")
WAF_PUBLIC_URL     = os.getenv("WAF_PUBLIC_URL", "http://localhost:8088")
WAF_PUBLIC_TLS_URL = os.getenv("WAF_PUBLIC_TLS_URL", "https://localhost:8443")

# Defaults applied on read; kept in sync with waf-proxy/lua/waf_config.lua
_WAF_DEFAULTS = {
    "upstream": "",
    "waf_enabled": True,
    "rate_limit_rpm": 600,
    "tls_enabled": False,
    "captcha_enabled": False,
    "geo_enabled": False,
    "ip_allowlist": [],
    "ip_blocklist": [],
    "geo_blocklist": [],
}

# Valid ISO 3166-1 alpha-2 country codes (compact superset commonly supported
# by Cloudflare / CloudFront country headers). Anything outside is rejected.
_ISO_CC_RE = re.compile(r"^[A-Z]{2}$")

# IPv4 CIDR validation — matches waf-proxy/lua/iputils.lua semantics.
_CIDR_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}(/\d{1,2})?$")


def _validate_cidr(s: str) -> str:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty CIDR")
    if not _CIDR_RE.match(s):
        raise ValueError(f"invalid CIDR: {s}")
    ip_part, _, bits_part = s.partition("/")
    octets = ip_part.split(".")
    for o in octets:
        n = int(o)
        if n < 0 or n > 255:
            raise ValueError(f"invalid octet in {s}")
    if bits_part:
        b = int(bits_part)
        if b < 0 or b > 32:
            raise ValueError(f"invalid prefix length in {s}")
    return s


def _validate_cc(s: str) -> str:
    s = (s or "").strip().upper()
    if not _ISO_CC_RE.match(s):
        raise ValueError(f"invalid country code: {s}")
    return s


def _coerce_str_list(value, validator, *, max_items=256):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected list")
    if len(value) > max_items:
        raise ValueError(f"too many items (max {max_items})")
    out = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("list items must be strings")
        out.append(validator(item))
    # de-dup preserving order
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _read_waf_config():
    cfg = dict(_WAF_DEFAULTS)
    try:
        with open(WAF_CONFIG_FILE, "r") as f:
            on_disk = json.load(f) or {}
            for k in _WAF_DEFAULTS:
                if k in on_disk:
                    cfg[k] = on_disk[k]
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Failed to read WAF config: %s", e)
    return cfg


def _validate_upstream(url: str) -> str:
    """Return scheme://host[:port] or '' if invalid. Strips path/query."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    p = urlparse(url)
    if not p.hostname:
        raise ValueError("Missing hostname")
    # Reject localhost / internal network targets to prevent SSRF pivots.
    # For local demos, set ALLOW_LOCALHOST_UPSTREAM=1 to opt in.
    host = p.hostname.lower()
    blocked_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    if host in blocked_hosts and os.getenv("ALLOW_LOCALHOST_UPSTREAM", "0") != "1":
        raise ValueError("Cannot protect localhost")
    port = f":{p.port}" if p.port else ""
    return f"{p.scheme}://{p.hostname}{port}"


@app.route('/api/config/proxy', methods=['GET'])
def get_proxy_config():
    cfg = _read_waf_config()
    # Live stats from waf-proxy admin endpoint
    stats = {}
    try:
        r = requests.get(f"{WAF_ADMIN_URL}/waf/stats", timeout=1.5)
        if r.ok:
            stats = r.json()
    except Exception as e:
        stats = {"error": str(e)[:120]}
    return jsonify({
        "status": "success",
        "data": {
            "config":        cfg,
            "stats":         stats,
            "public_url":    WAF_PUBLIC_URL,
            "public_tls_url":WAF_PUBLIC_TLS_URL,
        }
    })


@app.route('/api/config/proxy', methods=['POST'])
def set_proxy_config():
    body = request.get_json(silent=True) or {}

    # Load existing config so callers can PATCH partial updates.
    new_cfg = _read_waf_config()

    try:
        if "upstream" in body:
            new_cfg["upstream"] = _validate_upstream(body.get("upstream") or "")
        if "waf_enabled" in body:
            new_cfg["waf_enabled"] = bool(body.get("waf_enabled"))
        if "rate_limit_rpm" in body:
            rl = int(body.get("rate_limit_rpm") or 600)
            new_cfg["rate_limit_rpm"] = max(10, min(rl, 60000))
        if "tls_enabled" in body:
            new_cfg["tls_enabled"] = bool(body.get("tls_enabled"))
        if "captcha_enabled" in body:
            new_cfg["captcha_enabled"] = bool(body.get("captcha_enabled"))
        if "geo_enabled" in body:
            new_cfg["geo_enabled"] = bool(body.get("geo_enabled"))
        if "ip_allowlist" in body:
            new_cfg["ip_allowlist"] = _coerce_str_list(body.get("ip_allowlist"), _validate_cidr)
        if "ip_blocklist" in body:
            new_cfg["ip_blocklist"] = _coerce_str_list(body.get("ip_blocklist"), _validate_cidr)
        if "geo_blocklist" in body:
            new_cfg["geo_blocklist"] = _coerce_str_list(body.get("geo_blocklist"), _validate_cc, max_items=64)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    try:
        os.makedirs(WAF_CONFIG_DIR, exist_ok=True)
        tmp = WAF_CONFIG_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(new_cfg, f, indent=2)
        os.replace(tmp, WAF_CONFIG_FILE)
    except Exception as e:
        return jsonify({"status": "error", "message": f"write failed: {e}"}), 500

    reload_err = None
    try:
        requests.get(f"{WAF_ADMIN_URL}/waf/reload", timeout=2)
    except Exception as e:
        reload_err = str(e)[:120]

    return jsonify({
        "status":         "success",
        "data":           new_cfg,
        "public_url":     WAF_PUBLIC_URL,
        "public_tls_url": WAF_PUBLIC_TLS_URL,
        "reload_err":     reload_err,
    })


# ============================================================
# FULL-TEXT SEARCH  (/api/search)
# ============================================================

@app.route('/api/search')
def search_events():
    """
    Lightweight substring search across the last 1 000 events.

    Query params
    ------------
    q        : required — search term (case-insensitive)
    layer    : optional filter by source_layer
    limit    : max results to return (default 50, max 200)

    This is a Redis-based fallback; replace with Elasticsearch for
    production-scale full-text search.
    """
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({"status": "error", "message": "Query parameter 'q' is required"}), 400

    layer = request.args.get('layer', 'all')
    limit = min(int(request.args.get('limit', 50)), 200)

    # Gather events to search across
    if layer == 'all':
        pool = get_all_events(1000)
    else:
        pool = get_events_from_redis(f'events:{layer}', 0, 1000)

    # Case-insensitive substring match against the JSON serialisation
    # (cheap but effective for up to ~1 000 events)
    matches = []
    for event in pool:
        haystack = json.dumps(event).lower()
        if q in haystack:
            matches.append(event)
        if len(matches) >= limit:
            break

    return jsonify({
        "status": "success",
        "data": {
            "query":   q,
            "results": matches,
            "count":   len(matches),
            "searched_events": len(pool),
            "note": "Redis substring search — deploy Elasticsearch for production full-text search",
        }
    })


# --- Error Handling ---

@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found", "code": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"status": "error", "message": "Internal server error", "code": 500}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {e}")
    return jsonify({"status": "error", "message": "Unexpected error", "code": 500}), 500

# --- WebSocket ---

@socketio.on('connect')
def ws_connect():
    logger.info(f"[WS] Client connected: {request.sid}")
    # Send initial state
    emit('initial_state', {
        "summary": get_latest_summary(),
        "metrics": calculate_metrics(),
        "recent_events": get_all_events(20),
        "recent_incidents": get_incidents(10),
        "risk_scores": get_risk_scores()
    })

@socketio.on('disconnect')
def ws_disconnect():
    logger.info(f"[WS] Client disconnected: {request.sid}")

@socketio.on('request_refresh')
def ws_refresh():
    emit('full_refresh', {
        "summary": get_latest_summary(),
        "metrics": calculate_metrics(),
        "recent_events": get_all_events(20),
        "recent_incidents": get_incidents(10),
        "risk_scores": get_risk_scores()
    })

# --- Background Threads ---

def redis_subscriber():
    # Separate connection for PubSub
    while True:
        try:
            r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe("security_events", "correlated_incidents", "risk_scores", "correlation_summary")
            
            logger.info("[WS] Subscribed to Redis channels")
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    channel = message['channel']
                    
                    if channel == "security_events":
                        socketio.emit('new_event', data)
                    elif channel == "correlated_incidents":
                        socketio.emit('new_incident', data)
                    elif channel == "risk_scores":
                        socketio.emit('risk_update', data)
                    elif channel == "correlation_summary":
                        socketio.emit('summary_update', data)
                        
        except Exception as e:
            logger.error(f"[WS] Redis subscriber error: {e}")
            time.sleep(5)

def periodic_metrics():
    while True:
        try:
            time.sleep(10)
            socketio.emit('metrics_update', calculate_metrics())
            
            if int(time.time()) % 30 == 0:
                # Re-use logic from endpoint (simplified)
                # Ideally refactor to shared func
                pass 
        except Exception as e:
            logger.error(f"Metrics thread error: {e}")

# ============================================================
# TOPOLOGY  (/api/topology)
# ============================================================

@app.route('/api/topology')
def get_topology():
    """
    Proxy the live service-dependency graph from the topology-collector.
    Falls back to a static description if the collector is not reachable.
    """
    try:
        resp = requests.get('http://topology-collector:5080/topology/graph', timeout=3)
        if resp.status_code == 200:
            return jsonify({"status": "success", "data": resp.json()})
    except Exception:
        pass  # fall through to static fallback

    # Static fallback: return known services without live enrichment
    static_nodes = [
        {"service_name": svc, "status": "unknown", "threat_level": "normal",
         "container_id": "", "container_name": svc, "image": "",
         "network_aliases": [], "exposed_ports": [], "labels": {}, "ip_addresses": {},
         "last_seen": datetime.utcnow().isoformat() + "Z"}
        for svc in [
            "redis", "database", "api-server", "auth-service",
            "network-monitor", "api-monitor", "auth-monitor",
            "backend", "dashboard", "correlation-engine", "web-app",
            "topology-collector",
        ]
    ]
    static_edges = [
        {"source": "api-server",    "target": "redis",       "edge_type": "event_bus"},
        {"source": "auth-service",  "target": "redis",       "edge_type": "event_bus"},
        {"source": "api-monitor",   "target": "api-server",  "edge_type": "monitors"},
        {"source": "auth-monitor",  "target": "auth-service","edge_type": "monitors"},
        {"source": "backend",       "target": "redis",       "edge_type": "event_bus"},
        {"source": "dashboard",     "target": "backend",     "edge_type": "api"},
        {"source": "web-app",       "target": "api-server",  "edge_type": "proxy"},
        {"source": "web-app",       "target": "auth-service","edge_type": "proxy"},
        {"source": "correlation-engine","target":"redis",    "edge_type": "event_bus"},
    ]
    return jsonify({
        "status": "success",
        "data": {
            "nodes": static_nodes,
            "edges": static_edges,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_services": len(static_nodes),
            "note": "topology-collector unavailable; static fallback returned",
        }
    })


@app.route('/api/topology/service/<service_name>')
def get_topology_service(service_name):
    """Proxy a single service lookup from the topology-collector."""
    try:
        resp = requests.get(
            f'http://topology-collector:5080/topology/service/{service_name}', timeout=3
        )
        if resp.status_code == 200:
            return jsonify({"status": "success", "data": resp.json()})
        return jsonify({"status": "error", "message": "Service not found"}), 404
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503


# ============================================================
# KILL CHAINS  (/api/kill-chains)
# ============================================================

def _fetch_kill_chain_from_pg(incident_id: str):
    """Attempt to read kill chain detail from PostgreSQL."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM kill_chains WHERE incident_id = %s LIMIT 1",
                (incident_id,),
            )
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("PostgreSQL kill chain lookup error: %s", exc)
        return None


@app.route('/api/kill-chains')
def list_kill_chains():
    """
    List recent kill chains from PostgreSQL.

    Query params:
        limit   (int, default 20, max 200) — max rows to return
        site_id (str, optional)            — filter to chains whose JSONB
                                              ``steps`` reference this site_id
                                              (browser-layer incidents)

    Returns: {"status": "success", "data": {"kill_chains": [...], "count": N}}
    """
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
    except (TypeError, ValueError):
        limit = 20
    site_id = request.args.get('site_id')

    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            base = (
                "SELECT incident_id, incident_type, source_ip, service_path, "
                "first_service, last_service, mitre_techniques, "
                "first_event_at, detected_at, duration_seconds, mttd_seconds, "
                "severity, steps, created_at, "
                "scenario_label, narrative, status, analyst_note "
                "FROM kill_chains"
            )
            if site_id:
                cur.execute(
                    base + " WHERE steps::text ILIKE %s "
                           "ORDER BY created_at DESC LIMIT %s",
                    (f'%"site_id": "{site_id}"%', limit),
                )
            else:
                cur.execute(base + " ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        for kc in rows:
            for field in ("first_event_at", "detected_at", "created_at"):
                if hasattr(kc.get(field), "isoformat"):
                    kc[field] = kc[field].isoformat()
            if isinstance(kc.get("steps"), str):
                try:
                    kc["steps"] = json.loads(kc["steps"])
                except Exception:
                    pass

        return jsonify({
            "status": "success",
            "data": {"kill_chains": rows, "count": len(rows)},
        })
    except Exception as exc:
        logger.error("Kill chain list error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route('/api/kill-chains/<incident_id>')
def get_kill_chain(incident_id):
    """
    Drill-down into a specific kill chain.
    First tries PostgreSQL (full steps/path); falls back to Redis incident store.
    """
    # Try PostgreSQL first for full kill-chain detail
    kc = _fetch_kill_chain_from_pg(incident_id)
    if kc:
        # Deserialise JSONB steps field if needed
        if isinstance(kc.get("steps"), str):
            try:
                kc["steps"] = json.loads(kc["steps"])
            except Exception:
                pass
        # Convert datetime objects to ISO strings for JSON serialisation
        for field in ("first_event_at", "detected_at", "created_at"):
            if hasattr(kc.get(field), "isoformat"):
                kc[field] = kc[field].isoformat()
        kc["source"] = "postgres"
        return jsonify({"status": "success", "data": {"kill_chain": kc}})

    # Fall back to Redis incident list
    incidents = get_incidents(100)
    for inc in incidents:
        if inc.get("incident_id") == incident_id:
            inc["source"] = "redis_fallback"
            return jsonify({"status": "success", "data": {"kill_chain": inc}})

    return jsonify({"status": "error", "message": "Kill chain not found", "source": "none"}), 404


# ============================================================
# INCIDENT STATUS (PATCH /api/incidents/<id>/status)
# ============================================================

def _ensure_kill_chain_status_columns():
    """Add status and analyst_note columns to kill_chains if they don't exist."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';")
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS analyst_note TEXT;")
        conn.close()
        logger.info("kill_chains status columns ensured")
    except Exception as exc:
        logger.warning("Could not ensure kill_chains status columns: %s", exc)

def _bootstrap_database_schema():
    """
    Initialize required PostgreSQL tables on first boot.
    This keeps cloud deployments (e.g., Render managed Postgres) from
    failing when the database starts empty.
    """
    here = Path(__file__).resolve()
    candidates = []
    for depth in range(1, min(len(here.parents), 4)):
        candidates.append(here.parents[depth - 1] / "scripts" / "init_db.sql")
    candidates.extend([
        Path("/app/scripts/init_db.sql"),
        Path("/scripts/init_db.sql"),
    ])
    sql_path = next((p for p in candidates if p.exists()), None)
    if sql_path is None:
        logger.warning("DB bootstrap skipped: init_db.sql not found in %s", candidates)
        return

    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_path.read_text(encoding="utf-8"))
        conn.close()
        logger.info("Database bootstrap completed from %s", sql_path)
    except Exception as exc:
        logger.warning("Database bootstrap skipped due to error: %s", exc)


VALID_INCIDENT_STATUSES = (
    'open', 'active',
    'acknowledged', 'investigating',
    'resolved',
    'escalated', 'suppressed',
)


@app.route('/api/incidents/<incident_id>/status', methods=['PATCH'])
def update_incident_status(incident_id):
    """Update the triage status of an incident (Redis-backed, mirrored to Postgres)."""
    try:
        data = request.get_json() or {}
        status = data.get('status')
        note = data.get('note', '') or ''

        if status not in VALID_INCIDENT_STATUSES:
            return jsonify({"status": "error", "message": "Invalid status value"}), 400

        # Primary store: Redis hash (per spec)
        updated_at = _write_incident_status_redis(incident_id, status, note)

        # Mirror to Postgres kill_chains for legacy readers
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE kill_chains SET status = %s, analyst_note = %s WHERE incident_id = %s",
                        (status, note, incident_id),
                    )
                    if status == 'suppressed':
                        cur.execute("SELECT source_ip FROM kill_chains WHERE incident_id = %s", (incident_id,))
                        row = cur.fetchone()
                        if row and row[0] and redis_available:
                            redis_client.setex(f"suppressed:{row[0]}", 1800, "1")
            conn.close()
        except Exception as exc:
            logger.warning("postgres status mirror failed: %s", exc)

        socketio.emit('incident_status_change', {
            "type": "incident_status_change",
            "incident_id": incident_id,
            "status": status,
            "note": note,
            "updated_at": updated_at,
        })

        return jsonify({
            "status": "success",
            "incident_id": incident_id,
            "updated_at": updated_at,
            "data": {"incident_id": incident_id, "status": status, "updated_at": updated_at},
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/incidents/<incident_id>/status', methods=['GET'])
def get_incident_status(incident_id):
    """Return the current status for an incident (Redis hash, fallback open)."""
    status, note, updated_at = _read_incident_status_redis(incident_id)
    return jsonify({
        "incident_id": incident_id,
        "status": status or "open",
        "note": note or "",
        "updated_at": updated_at or "",
    })


# ============================================================
# DEMO STATUS  (/api/demo-status)
# ============================================================

@app.route('/api/demo-status')
def demo_status():
    """Return whether a demo scenario is currently running."""
    try:
        active_val = redis_client.get('demo:active') if redis_available else None
        scenario_val = redis_client.get('demo:scenario') if redis_available else None
        return jsonify({"status": "success", "data": {
            "active": active_val is not None,
            "scenario": scenario_val if isinstance(scenario_val, str) else (scenario_val.decode() if scenario_val else None)
        }})
    except Exception as e:
        return jsonify({"status": "success", "data": {"active": False, "scenario": None}})


# ============================================================
# MITRE ATT&CK MAPPING  (/api/mitre-mapping)
# ============================================================

@app.route('/api/mitre-mapping')
def mitre_mapping():
    """
    Merge the static MITRE_MAP (every technique SecuriSphere can detect)
    with live hit counts derived from Redis incidents and the correlation
    engine stats. Returns a full coverage breakdown suitable for the
    MITRE page.
    """
    # ---- 1. Aggregate live hit counts -----------------------------------
    hit_counts: dict = defaultdict(int)
    incident_ids: dict = defaultdict(list)

    incidents = get_incidents(100)
    for inc in incidents:
        for technique in (inc.get("mitre_techniques") or []):
            if technique:
                hit_counts[technique] += 1
                incident_ids[technique].append(inc.get("incident_id"))

    # Engine stats (in-memory mitre_hits counter) — merges even if the
    # Redis incident list has been trimmed.
    try:
        eng_resp = requests.get(
            "http://correlation-engine:5070/engine/mitre-mapping", timeout=2,
        )
        if eng_resp.status_code == 200:
            eng_hits = (eng_resp.json().get("data") or {}).get("technique_hits") or {}
            for tech, hits in eng_hits.items():
                # Prefer the larger of the two counters
                hit_counts[tech] = max(hit_counts[tech], int(hits or 0))
    except Exception:
        pass

    # Optional Redis hash `mitre_hits` — reserved for future direct writes
    if redis_available:
        try:
            redis_hits = redis_client.hgetall("mitre_hits") or {}
            for tech, hits in redis_hits.items():
                try:
                    hit_counts[tech] = max(hit_counts[tech], int(hits))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

    # ---- 2. Compose technique rows from MITRE_MAP -----------------------
    techniques = []
    coverage_tally = {"full": 0, "partial": 0, "theoretical": 0}
    tactics_summary: dict = defaultdict(int)

    for tid, entry in MITRE_MAP.items():
        row = {
            "technique_id":      entry["technique_id"],
            "technique_name":    entry["technique_name"],
            "tactic":            entry["tactic"],
            "tactic_id":         entry["tactic_id"],
            "hit_count":         int(hit_counts.get(tid, 0)),
            "coverage":          entry["coverage"],
            "scenarios":         list(entry.get("scenarios", [])),
            "detected_by":       list(entry.get("detected_by", [])),
            "correlation_rules": list(entry.get("correlation_rules", [])),
            "container_context": entry.get("container_context", ""),
            "description":       entry.get("description", ""),
            "incident_ids":      incident_ids.get(tid, [])[:10],
        }
        techniques.append(row)
        coverage_tally[entry["coverage"]] = coverage_tally.get(entry["coverage"], 0) + 1
        tactics_summary[entry["tactic"]] += 1

    # Sort by hit_count desc, then by technique_id for stable ordering
    techniques.sort(key=lambda r: (-r["hit_count"], r["technique_id"]))

    return jsonify({
        "status": "success",
        "data": {
            "techniques":            techniques,
            "tactics_summary":       dict(tactics_summary),
            "total_techniques":      len(techniques),
            "full_coverage":         coverage_tally.get("full", 0),
            "partial_coverage":      coverage_tally.get("partial", 0),
            "theoretical_coverage":  coverage_tally.get("theoretical", 0),
            "total_incidents":       len(incidents),
            "tactic_order":          TACTIC_ORDER,
        }
    })


# ============================================================
# MTTD REPORT  (/api/mttd/report)
# ============================================================

@app.route('/api/mttd/report')
def mttd_report():
    """
    Return per-scenario / per-incident-type MTTD statistics.

    Tries PostgreSQL kill_chains table first (accurate), then falls back to
    approximating from the Redis incident list (time_span_seconds + 1.5s).
    """
    # Try PostgreSQL
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    incident_type,
                    COUNT(*)                         AS incident_count,
                    AVG(mttd_seconds)                AS avg_mttd_seconds,
                    MIN(mttd_seconds)                AS min_mttd_seconds,
                    MAX(mttd_seconds)                AS max_mttd_seconds,
                    AVG(duration_seconds)            AS avg_attack_duration_seconds
                FROM kill_chains
                GROUP BY incident_type
                ORDER BY avg_mttd_seconds ASC NULLS LAST
            """)
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if rows:
            # Convert Decimal / None to plain Python types for JSON
            for row in rows:
                for k, v in row.items():
                    if hasattr(v, "__float__"):
                        row[k] = round(float(v), 3) if v is not None else None
            return jsonify({"status": "success", "source": "postgresql", "data": rows})
    except Exception as exc:
        logger.warning("MTTD PostgreSQL fallback: %s", exc)

    # Redis approximation fallback
    incidents = get_incidents(100)
    from collections import defaultdict as _dd
    buckets: dict = _dd(lambda: {"count": 0, "total_mttd": 0.0, "values": []})
    for inc in incidents:
        mttd = inc.get("mttd_seconds")
        if mttd is None:
            mttd = (inc.get("time_span_seconds") or 0) + 1.5  # approximation
        t = inc.get("incident_type", "unknown")
        buckets[t]["count"]      += 1
        buckets[t]["total_mttd"] += mttd
        buckets[t]["values"].append(mttd)

    result = []
    for t, b in buckets.items():
        avg = b["total_mttd"] / b["count"] if b["count"] else None
        result.append({
            "incident_type":             t,
            "incident_count":            b["count"],
            "avg_mttd_seconds":          round(avg, 3) if avg is not None else None,
            "min_mttd_seconds":          round(min(b["values"]), 3) if b["values"] else None,
            "max_mttd_seconds":          round(max(b["values"]), 3) if b["values"] else None,
            "avg_attack_duration_seconds": None,
        })
    result.sort(key=lambda x: (x["avg_mttd_seconds"] or float("inf")))

    return jsonify({"status": "success", "source": "redis_approximation", "data": result})


# ============================================================
# DISCORD WEBHOOK CONFIGURATION ROUTES
# ============================================================

# GET Endpoint to retrieve current config
@app.route('/api/config/discord', methods=['GET'])
def get_discord_config():
    try:
        # Fetch from Redis key 'config:discord_webhook'
        url = redis_client.get('config:discord_webhook')
        return jsonify({
            "status": "success", 
            "url": url if url else "" 
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# POST Endpoint to save config
@app.route('/api/config/discord', methods=['POST'])
def set_discord_config():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if url:
            # Basic validation: must start with http
            if not url.startswith('http'):
                 return jsonify({"status": "error", "message": "Invalid URL format"}), 400
            redis_client.set('config:discord_webhook', url)
        else:
            # If empty string provided, delete the key (disable feature)
            redis_client.delete('config:discord_webhook')
            
        return jsonify({"status": "success", "message": "Configuration saved"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# POST Endpoint to test the webhook immediately
@app.route('/api/config/discord/test', methods=['POST'])
def test_discord_config():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"status": "error", "message": "No URL provided"}), 400
            
        import requests
        payload = {
            "content": "✅ **SecuriSphere Test:** Notification system is operational."
        }
        # Send actual request to Discord
        resp = requests.post(url, json=payload, timeout=5)
        
        if resp.status_code in [200, 204]:
            return jsonify({"status": "success", "message": "Test message sent!"})
        else:
            return jsonify({"status": "error", "message": f"Discord returned {resp.status_code}"}), 400
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Attack console (spawns attacker scenarios) -----------------------------

_ATTACK_VALID_SCENARIOS = {"a", "b", "c", "all"}
_ATTACK_VALID_SPEEDS = {"demo", "normal", "fast"}

_attack_lock = threading.Lock()
_attack_log = deque(maxlen=100)
_attack_state = {"running": False, "scenario": None, "pid": None, "proc": None}


def _attack_append(line: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    with _attack_lock:
        _attack_log.append(f"[{ts}] {line.rstrip()}")


def _attack_reader(proc, scenario):
    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            _attack_append(line)
    except Exception as e:
        _attack_append(f"[reader-error] {e}")
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        rc = proc.wait()
        _attack_append(f"[done] scenario={scenario} exit={rc}")
        with _attack_lock:
            if _attack_state.get("pid") == proc.pid:
                _attack_state["running"] = False
                _attack_state["proc"] = None


@app.route('/api/attack/run', methods=['POST'])
def api_attack_run():
    body = request.get_json(silent=True) or {}
    scenario = str(body.get("scenario", "")).lower().strip()
    speed = str(body.get("speed", "demo")).lower().strip()

    if scenario not in _ATTACK_VALID_SCENARIOS:
        return jsonify({"status": "error", "message": f"scenario must be one of {sorted(_ATTACK_VALID_SCENARIOS)}"}), 400
    if speed not in _ATTACK_VALID_SPEEDS:
        return jsonify({"status": "error", "message": f"speed must be one of {sorted(_ATTACK_VALID_SPEEDS)}"}), 400

    with _attack_lock:
        if _attack_state["running"]:
            return jsonify({
                "status": "busy",
                "message": "attack already running",
                "scenario": _attack_state["scenario"],
                "pid": _attack_state["pid"],
            }), 409

    if scenario == "all":
        runner = (
            "from attacker.scenario_a import run as ra;"
            "from attacker.scenario_b import run as rb;"
            "from attacker.scenario_c import run as rc;"
            f"print('>>> scenario A'); ra(speed={speed!r});"
            f"print('>>> scenario B'); rb(speed={speed!r});"
            f"print('>>> scenario C'); rc(speed={speed!r})"
        )
        cmd = [sys.executable, "-u", "-c", runner]
    else:
        cmd = [sys.executable, "-u", "-m", f"attacker.scenario_{scenario}", "--speed", speed]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd="/app",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"spawn failed: {e}"}), 500

    with _attack_lock:
        _attack_log.clear()
        _attack_state.update({"running": True, "scenario": scenario, "pid": proc.pid, "proc": proc})

    _attack_append(f"[launch] scenario={scenario} speed={speed} pid={proc.pid}")
    t = threading.Thread(target=_attack_reader, args=(proc, scenario), daemon=True)
    t.start()

    return jsonify({"status": "started", "scenario": scenario, "pid": proc.pid})


@app.route('/api/attack/status', methods=['GET'])
def api_attack_status():
    with _attack_lock:
        return jsonify({
            "running": bool(_attack_state["running"]),
            "scenario": _attack_state["scenario"],
            "pid": _attack_state["pid"],
            "log_lines": list(_attack_log),
        })


# --- Startup ---

def _heartbeat_loop():
    while True:
        socketio.sleep(15)
        socketio.emit('heartbeat', {'ts': time.time()})


if __name__ == '__main__':
    connect_redis()
    _bootstrap_database_schema()
    _ensure_kill_chain_status_columns()

    # Start threads
    t1 = threading.Thread(target=redis_subscriber)
    t1.daemon = True
    t1.start()

    t2 = threading.Thread(target=periodic_metrics)
    t2.daemon = True
    t2.start()

    socketio.start_background_task(_heartbeat_loop)
    
    print("========================================")
    print("  SecuriSphere Backend API v1.0.0")
    print("========================================")
    print(f"  REST API:   http://0.0.0.0:{APP_PORT}")
    print(f"  WebSocket:  ws://0.0.0.0:{APP_PORT}")
    print(f"  Redis:      {REDIS_HOST}:{REDIS_PORT}")
    print("========================================")
    
    socketio.run(app, host='0.0.0.0', port=APP_PORT, debug=False, allow_unsafe_werkzeug=True)
