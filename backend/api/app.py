import os
import time
import json
import uuid
import threading
import logging
from pathlib import Path
import redis
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from gevent import monkey
# Patch gevent
monkey.patch_all()

from auth import auth_bp
from topology_checks import bp as topology_checks_bp


# ... (logging setup) ...

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SecuriSphereBackend")
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Flask Setup
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

def calculate_metrics():
    metrics = {
        "raw_events": {"network": 0, "api": 0, "auth": 0, "total": 0},
        "correlated_incidents": 0,
        "alert_reduction_percentage": 0,
        "active_risk_entities": 0,
        "events_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "events_by_type": defaultdict(int),
        "system_uptime": str(datetime.utcnow() - SERVER_START_TIME),
        "timestamp": datetime.utcnow().isoformat()
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

@app.route('/api/incidents')
def list_incidents():
    limit = min(int(request.args.get('limit', 20)), 100)
    incidents = get_incidents(limit)

    # Enrich incidents with status from PostgreSQL (batch query)
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
                    "SELECT incident_id, status FROM kill_chains WHERE incident_id = ANY(%s)",
                    (incident_ids,),
                )
                status_map = {str(row['incident_id']): row['status'] for row in cur.fetchall()}
            conn.close()
            for inc in incidents:
                inc['status'] = status_map.get(inc.get('incident_id'), 'active')
        else:
            for inc in incidents:
                inc['status'] = 'active'
    except Exception:
        for inc in incidents:
            inc.setdefault('status', 'active')

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
    
    # Calculate summary
    summary = {
        "total_entities": len(risks),
        "critical_count": 0, 
        "threatening_count": 0,
        "suspicious_count": 0,
        "normal_count": 0
    }
    
    for r in risks.values():
        score = r.get('current_score', 0)
        if score >= 90: summary["critical_count"] += 1
        elif score >= 70: summary["threatening_count"] += 1
        elif score >= 30: summary["suspicious_count"] += 1
        else: summary["normal_count"] += 1
            
    return jsonify({
        "status": "success",
        "data": {
            "risk_scores": risks,
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
    return jsonify({
        "status": "success", 
        "message": "All events and incidents cleared",
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
        
        # Check monitors
        monitors = ["network", "api", "auth"]
        for m in monitors:
            last = (get_events_from_redis(f"events:{m}", 0, 1) or [{}])[0]
            status["monitors"][m] = {
                "active": last is not None,
                "last_event": last.get('timestamp'),
                "event_count": redis_client.llen(f"events:{m}")
            }
            status["total_events"] += status["monitors"][m]["event_count"]
            
        status["correlation_engine"]["incidents"] = redis_client.llen("incidents")
        
    return jsonify({"status": "success", "data": status})

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
    sql_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.sql"
    if not sql_path.exists():
        logger.warning("DB bootstrap skipped: %s not found", sql_path)
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


@app.route('/api/incidents/<incident_id>/status', methods=['PATCH'])
def update_incident_status(incident_id):
    """Update the triage status of an incident."""
    try:
        data = request.get_json()
        status = data.get('status')
        note = data.get('note', '')

        valid_statuses = ('active', 'acknowledged', 'escalated', 'suppressed')
        if status not in valid_statuses:
            return jsonify({"status": "error", "message": "Invalid status value"}), 400

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
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT source_ip FROM kill_chains WHERE incident_id = %s", (incident_id,))
                    row = cur.fetchone()
                if row and row[0] and redis_available:
                    redis_client.setex(f"suppressed:{row[0]}", 1800, "1")
            except Exception:
                pass

        conn.close()

        socketio.emit('incident_status_change',
                      {"incident_id": incident_id, "status": status})

        return jsonify({"status": "success", "data": {"incident_id": incident_id, "status": status}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


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
    Return MITRE ATT&CK technique frequency across all correlated incidents.

    Aggregates techniques from the in-Redis incident list so no DB dependency.
    """
    technique_counts: dict = defaultdict(int)
    technique_incidents: dict = defaultdict(list)

    incidents = get_incidents(100)
    for inc in incidents:
        for technique in (inc.get("mitre_techniques") or []):
            if technique:
                technique_counts[technique] += 1
                technique_incidents[technique].append(inc.get("incident_id"))

    # Augment with descriptions
    technique_info = {
        "T1046":     "Network Service Scanning",
        "T1595":     "Active Scanning",
        "T1190":     "Exploit Public-Facing Application",
        "T1110":     "Brute Force",
        "T1110.004": "Credential Stuffing",
        "T1078":     "Valid Accounts",
        "T1003":     "OS Credential Dumping",
        "T1021":     "Remote Services / Lateral Movement",
        "T1071":     "Application Layer Protocol (C2 over HTTP)",
        "T1530":     "Data from Cloud Storage Object",
        "T1083":     "File and Directory Discovery",
        "T1048":     "Exfiltration Over Alternative Protocol",
    }

    result = []
    for technique, count in sorted(technique_counts.items(), key=lambda x: -x[1]):
        result.append({
            "technique_id":   technique,
            "name":           technique_info.get(technique, "Unknown Technique"),
            "hit_count":      count,
            "incident_ids":   technique_incidents[technique][:10],  # truncate
        })

    # Also try to pull enriched data from the correlation engine
    try:
        eng_resp = requests.get("http://correlation-engine:5070/engine/mitre-mapping", timeout=2)
        if eng_resp.status_code == 200:
            eng_data = eng_resp.json().get("data", {})
            # Merge engine hits into our result
            for tech, hits in eng_data.get("technique_hits", {}).items():
                existing = next((r for r in result if r["technique_id"] == tech), None)
                if existing:
                    existing["engine_hit_count"] = hits
                else:
                    result.append({
                        "technique_id": tech,
                        "name": technique_info.get(tech, "Unknown Technique"),
                        "hit_count": 0,
                        "engine_hit_count": hits,
                        "incident_ids": [],
                    })
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "data": {
            "techniques":       result,
            "total_unique":     len(result),
            "total_incidents":  len(incidents),
            "coverage_percent": round(len(result) / len(technique_info) * 100, 1),
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
