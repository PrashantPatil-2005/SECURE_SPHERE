import os
import sys
import time
import json
import uuid
import threading
import subprocess
import logging
from pathlib import Path
import redis
from datetime import datetime
from collections import deque
from flask import Flask, jsonify, request
from flask_socketio import emit
from flask_cors import CORS
from gevent import monkey
# Patch gevent
monkey.patch_all()

# Docker: /app/ai; local dev: backend/ai (parent of backend/api).
_here = Path(__file__).resolve()
for _root in (_here.parent, _here.parent.parent):
    if (_root / "ai" / "client.py").exists():
        sys.path.insert(0, str(_root))
        break

from auth import auth_bp, token_required, role_required, _decode_token
from users_bp import users_bp
from topology_checks import bp as topology_checks_bp
from ai_endpoints import bp as ai_bp
from engine_proxy import engine_proxy_bp
from bff_proxy import bp as bff_proxy_bp
from topology_routes import bp as topology_routes_bp
from risk_routes import bp as risk_routes_bp
from events_routes import bp as events_routes_bp
from metrics_routes import bp as metrics_routes_bp
from incidents_routes import bp as incidents_routes_bp
from killchain_routes import bp as killchain_routes_bp
from mitre_routes import bp as mitre_routes_bp
from evaluation_routes import bp as evaluation_routes_bp
from campaign_routes import bp as campaign_routes_bp
from config_routes import bp as config_routes_bp
from search_routes import bp as search_routes_bp
from attack_simulator import SimulatorRuntime, detect_target_services_unreachable
# audit log_audit/query_audit usage moved to incidents_routes.py / evaluation_routes.py.

# MITRE ATT&CK static map + routes now live in mitre_routes.py blueprint.

# avg_mttd_seconds + redis data-service helpers now live in services.py.

# ... (logging setup) ...

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("SecuriSphereBackend")
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Flask Setup
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
IS_PRODUCTION = FLASK_ENV == "production"

if os.getenv("ALLOW_LOCALHOST_UPSTREAM", "0") == "1":
    logger.warning("ALLOW_LOCALHOST_UPSTREAM=1 — SSRF loopback guard disabled. Demo only; never in production.")
    if IS_PRODUCTION:
        raise RuntimeError("ALLOW_LOCALHOST_UPSTREAM=1 is forbidden when FLASK_ENV=production")

# Boot-time env validation
if IS_PRODUCTION:
    _required = ["JWT_SECRET"]
    _missing = [v for v in _required if not os.getenv(v)]
    if _missing:
        raise RuntimeError(f"Missing required env vars in production: {_missing}")
    if len(os.getenv("JWT_SECRET", "")) < 16:
        raise RuntimeError("JWT_SECRET must be at least 16 chars in production")
    if not os.getenv("POSTGRES_PASSWORD") and not os.getenv("DATABASE_URL"):
        raise RuntimeError("POSTGRES_PASSWORD or DATABASE_URL is required in production")

# CORS — explicit allowlist via env, wildcard only allowed outside production.
_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_raw == "*" and IS_PRODUCTION:
    raise RuntimeError("CORS_ORIGINS=* is forbidden in production. Set explicit origins.")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or ["*"]

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": _cors_origins}}, supports_credentials=True)

# socketio is constructed in extensions.py (no app) so blueprints can import it
# without a circular dependency, then bound to this app here.
from extensions import socketio
socketio.init_app(app, cors_allowed_origins=_cors_origins, async_mode="gevent")

# --- Rate limiting ----------------------------------------------------------
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    _limiter_storage = (
        f"redis://{os.getenv('REDIS_HOST','redis')}:{os.getenv('REDIS_PORT','6379')}"
    )
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "200/minute")],
        storage_uri=_limiter_storage,
        strategy="moving-window",
    )
except Exception as _exc:  # graceful degradation
    logger.warning("Rate limiter disabled: %s", _exc)
    class _NoopLimiter:
        def limit(self, *a, **kw):
            def deco(f): return f
            return deco
        def exempt(self, f): return f
    limiter = _NoopLimiter()

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(topology_checks_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(engine_proxy_bp)
app.register_blueprint(bff_proxy_bp)
app.register_blueprint(topology_routes_bp)
app.register_blueprint(risk_routes_bp)
app.register_blueprint(events_routes_bp)
app.register_blueprint(metrics_routes_bp)
app.register_blueprint(incidents_routes_bp)
app.register_blueprint(killchain_routes_bp)
app.register_blueprint(mitre_routes_bp)
app.register_blueprint(evaluation_routes_bp)
app.register_blueprint(campaign_routes_bp)
app.register_blueprint(config_routes_bp)
app.register_blueprint(search_routes_bp)

# Rate-limit login route after blueprint registration
try:
    limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "10/minute"))(
        app.view_functions["auth.login"]
    )
except Exception:
    pass

# Redis / data-service layer now lives in services.py (shared with blueprints).
# Access mutable redis state via attribute (services.redis_client /
# services.redis_available) so the live connection is always observed.
import services
from services import (
    connect_redis,
    get_events_from_redis,
    get_all_events,
    get_incidents,
    get_risk_scores,
    get_latest_summary,
    calculate_metrics,
)

APP_PORT = int(os.getenv('PORT', os.getenv('BACKEND_PORT', 8000)))

# --- Middleware ---

@app.before_request
def log_request():
    if request.path != '/api/health':
        pass # Too noisy

@app.after_request
def add_headers(response):
    response.headers['X-SecuriSphere-Version'] = '1.0.0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    if IS_PRODUCTION:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Remove server fingerprint
    response.headers.pop('Server', None)
    return response

# --- REST API Endpoints ---

@app.route('/api/health')
@limiter.exempt
def health():
    return jsonify({
        "status": "healthy",
        "service": "securisphere-backend",
        "redis_connected": services.redis_available,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })

# DASHBOARD / METRICS / SYSTEM / DEMO-STATUS routes live in metrics_routes.py blueprint.

# EVENT routes (/api/events*) live in events_routes.py blueprint.

# INCIDENT routes (/api/incidents*, including status PATCH/GET) live in incidents_routes.py blueprint.

# RISK-SCORE routes (/api/risk-scores, /api/v2/risk/accounts) live in risk_routes.py blueprint.

# EVENT clear/latest routes live in events_routes.py blueprint.

# SYSTEM STATUS route lives in metrics_routes.py blueprint.

# ============================================================
# WAF / Reverse-proxy configuration
# ============================================================

# WAF / proxy + Discord config routes live in config_routes.py blueprint.


# ============================================================
# FULL-TEXT SEARCH  (/api/search)
# ============================================================

# FULL-TEXT SEARCH route (/api/search) lives in search_routes.py blueprint.


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

# WebSocket auth: by default every Socket.IO handshake must present a valid
# access JWT (handshake `auth: {token}` or `?token=` query param). This mirrors
# the REST `@token_required` hardening so the realtime channel can't be tapped
# anonymously. For local demos only, set ALLOW_WS_ANONYMOUS=1 (ignored in prod).
def _ws_extract_token(auth):
    if isinstance(auth, dict):
        tok = auth.get('token') or auth.get('access_token')
        if tok:
            return tok.replace('Bearer ', '').strip()
    # Fallbacks: Authorization header or query string on the handshake request.
    hdr = request.headers.get('Authorization', '')
    if hdr.startswith('Bearer '):
        return hdr[7:].strip()
    return (request.args.get('token') or '').strip()


@socketio.on('connect')
def ws_connect(auth=None):
    allow_anon = (not IS_PRODUCTION) and os.getenv('ALLOW_WS_ANONYMOUS', '0') == '1'
    token = _ws_extract_token(auth)
    payload = _decode_token(token) if token else None

    if payload is None and not allow_anon:
        logger.warning("[WS] Rejected unauthenticated connection: %s", request.sid)
        return False  # reject the handshake

    user = payload.get('username') if payload else 'anonymous'
    logger.info(f"[WS] Client connected: {request.sid} (user={user})")
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
            r = redis.Redis(host=services.REDIS_HOST, port=services.REDIS_PORT, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe(
                "security_events", "correlated_incidents", "risk_scores",
                "correlation_summary", "campaign_escalated",
            )
            
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
                    elif channel == "campaign_escalated":
                        socketio.emit('campaign_escalated', data)
                        
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

# TOPOLOGY routes (/api/topology) live in topology_routes.py blueprint.


# ============================================================
# KILL CHAINS  (/api/kill-chains)
# ============================================================

# KILL-CHAIN routes (/api/kill-chains*) live in killchain_routes.py blueprint.


# ============================================================
# Kill-chain schema bootstrap (runs at startup, not a route)
# ============================================================

def _ensure_kill_chain_status_columns():
    """Add status and analyst_note columns to kill_chains if they don't exist."""
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
        conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_path.read_text(encoding="utf-8"))
        # Apply numbered migrations sitting next to init_db.sql so newer
        # tables (campaigns, etc.) exist even when only init_db.sql ships
        # in the deployment image.
        migrations_dir = sql_path.parent / "migrations"
        if migrations_dir.is_dir():
            for mig in sorted(migrations_dir.glob("*.sql")):
                try:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute(mig.read_text(encoding="utf-8"))
                    logger.info("Applied migration %s", mig.name)
                except Exception as mig_exc:
                    logger.warning("Migration %s skipped: %s", mig.name, mig_exc)
        conn.close()
        logger.info("Database bootstrap completed from %s", sql_path)
    except Exception as exc:
        logger.warning("Database bootstrap skipped due to error: %s", exc)


# INCIDENT status PATCH/GET routes live in incidents_routes.py blueprint.


# ============================================================
# DEMO STATUS  (/api/demo-status)
# ============================================================

# DEMO STATUS route lives in metrics_routes.py blueprint.


# ============================================================
# Engine reverse proxy (/api/engine/*)
# Phase 13 dashboards (Replay, MITRE heatmap, Predict-next, Anomalies,
# Threat-intel, Explain, YAML rules) hit the correlation engine via this
# proxy so the frontend doesn't need direct network access to :5070 and
# auth/cors stays handled in the API layer.
# ============================================================

# /api/engine/* proxy now lives in engine_proxy.py blueprint (token-required,
# Authorization passthrough, graceful 503 envelope on engine outage).


# MITRE routes (/api/mitre-mapping, /api/v2/mitre/coverage) live in mitre_routes.py blueprint.


# ACCOUNT RISK routes (/api/v2/risk/accounts) live in risk_routes.py blueprint.


# EVALUATION / AUDIT / MTTD routes live in evaluation_routes.py blueprint.


# ============================================================
# CAMPAIGN AGGREGATION ROUTES
# ============================================================
# Campaigns group multiple correlated incidents from one attacker into a
# single analyst-facing record. See backend/engine/correlation/campaign_aggregator.py
# for the aggregation logic.

# CAMPAIGN routes (/api/campaigns*) live in campaign_routes.py blueprint.


# ============================================================
# DISCORD WEBHOOK CONFIGURATION ROUTES
# ============================================================

# Discord config routes live in config_routes.py blueprint.

# --- Attack console (spawns attacker scenarios) -----------------------------

_ATTACK_VALID_SCENARIOS = {"a", "b", "c", "all"}
_ATTACK_VALID_SPEEDS = {"demo", "normal", "fast"}

_attack_lock = threading.Lock()
_attack_log = deque(maxlen=100)
_attack_state = {"running": False, "scenario": None, "pid": None, "proc": None, "mode": None}

_simulator_runtime = None


def _get_simulator():
    global _simulator_runtime
    if _simulator_runtime is None:
        _simulator_runtime = SimulatorRuntime(
            redis_client=services.redis_client if services.redis_available else None,
            socketio=socketio,
            log_cb=_attack_append,
        )
    return _simulator_runtime


def _resolve_attacker_root():
    """Locate dir containing the `attacker` package.

    Works in three layouts:
    - Docker image: /app/attacker
    - Local repo: <repo_root>/attacker (one level up from backend/api)
    - Render native build (rootDir=backend/api): /opt/render/project/src/attacker
    """
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        "/app",
        os.path.abspath(os.path.join(here, "..", "..")),
        os.path.abspath(os.path.join(here, "..")),
        os.environ.get("REPO_ROOT", ""),
        os.environ.get("PROJECT_ROOT", ""),
    ]
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, "attacker")):
            return c
    return here


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


def _attack_public_mode():
    explicit = os.getenv("ATTACK_PUBLIC")
    if explicit is not None:
        return explicit == "1"
    # Default: public outside production so local dev (`python app.py` or
    # `docker compose up`) never trips on the auth wall. In prod, opt-in only.
    return os.getenv("FLASK_ENV", "development").lower() != "production"


def _attack_auth_guard(view):
    """Apply @token_required + @role_required('admin') unless ATTACK_PUBLIC=1."""
    from functools import wraps

    @wraps(view)
    def wrapper(*args, **kwargs):
        if _attack_public_mode():
            return view(*args, **kwargs)
        guarded = token_required(role_required('admin')(view))
        return guarded(*args, **kwargs)

    return wrapper


@app.route('/api/attack/run', methods=['POST'])
@_attack_auth_guard
@limiter.limit(os.getenv("RATE_LIMIT_ATTACK", "5/hour"))
def api_attack_run():
    body = request.get_json(silent=True) or {}
    scenario = str(body.get("scenario", "")).lower().strip()
    speed = str(body.get("speed", "demo")).lower().strip()

    if scenario not in _ATTACK_VALID_SCENARIOS:
        return jsonify({"status": "error", "message": f"scenario must be one of {sorted(_ATTACK_VALID_SCENARIOS)}"}), 400
    if speed not in _ATTACK_VALID_SPEEDS:
        return jsonify({"status": "error", "message": f"speed must be one of {sorted(_ATTACK_VALID_SPEEDS)}"}), 400

    sim = _get_simulator()
    with _attack_lock:
        if _attack_state["running"] or sim.is_running():
            return jsonify({
                "status": "busy",
                "message": "attack already running",
                "scenario": _attack_state["scenario"],
                "pid": _attack_state["pid"],
                "mode": _attack_state.get("mode"),
            }), 409

    if detect_target_services_unreachable():
        if not sim.start(scenario, speed):
            return jsonify({"status": "busy", "message": "simulator already running"}), 409
        with _attack_lock:
            _attack_log.clear()
            _attack_state.update({"running": True, "scenario": scenario, "pid": None, "proc": None, "mode": "inprocess"})
        _attack_append(f"[launch] mode=inprocess scenario={scenario} speed={speed}")

        def _watch_inprocess():
            while sim.is_running():
                time.sleep(0.5)
            with _attack_lock:
                _attack_state["running"] = False
            _attack_append(f"[done] scenario={scenario} mode=inprocess")

        threading.Thread(target=_watch_inprocess, daemon=True).start()
        return jsonify({"status": "started", "scenario": scenario, "mode": "inprocess"})

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

    attacker_root = _resolve_attacker_root()
    sub_env = os.environ.copy()
    existing_pp = sub_env.get("PYTHONPATH", "")
    sub_env["PYTHONPATH"] = (
        f"{attacker_root}{os.pathsep}{existing_pp}" if existing_pp else attacker_root
    )

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=attacker_root,
            env=sub_env,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": f"spawn failed: {e}"}), 500

    with _attack_lock:
        _attack_log.clear()
        _attack_state.update({"running": True, "scenario": scenario, "pid": proc.pid, "proc": proc, "mode": "subprocess"})

    _attack_append(f"[launch] mode=subprocess scenario={scenario} speed={speed} pid={proc.pid}")
    t = threading.Thread(target=_attack_reader, args=(proc, scenario), daemon=True)
    t.start()

    return jsonify({"status": "started", "scenario": scenario, "pid": proc.pid, "mode": "subprocess"})


@app.route('/api/dev/fire-kill-chain', methods=['POST', 'GET'])
@token_required
def api_dev_fire_kill_chain():
    """Demo + debug endpoint. Synthesizes a full kill chain incident and
    pushes it through the same publish path as the simulator. Verifies
    Redis → socket.io → CriticalAlertModal end-to-end without needing the
    correlation-engine container."""
    sim = _get_simulator()
    src_ip = request.args.get("ip") or "10.0.2.4"
    # Seed buffer with one event per required layer so the synthetic
    # incident has realistic fields. Idempotent — re-firing just adds more.
    seed_events = [
        {
            "event_id":     str(uuid.uuid4()),
            "timestamp":    datetime.utcnow().isoformat() + "Z",
            "source_layer": layer,
            "event_type":   etype,
            "severity":     {"level": "high"},
            "source_entity": {"ip": src_ip, "service": svc},
            "destination_entity": {"ip": "10.0.1.20", "service": dst},
            "mitre_technique": mitre,
        }
        for layer, etype, svc, dst, mitre in [
            ("network", "port_scan",       None,           "web-app",      "T1046"),
            ("auth",    "login_failed",    None,           "auth-service", "T1110"),
            ("api",     "data_access",     "auth-service", "api-gateway",  "T1078"),
        ]
    ]
    for ev in seed_events:
        sim._correlator.observe(ev)
    incident = sim._correlator.force_fire(src_ip)
    return jsonify({
        "status": "ok" if incident else "skipped",
        "incident_id": incident.get("incident_id") if incident else None,
        "source_ip":   src_ip,
        "buffer_size": len(sim._correlator._buffer),
    })


@app.route('/api/attack/status', methods=['GET'])
@_attack_auth_guard
def api_attack_status():
    with _attack_lock:
        return jsonify({
            "running": bool(_attack_state["running"]),
            "scenario": _attack_state["scenario"],
            "pid": _attack_state["pid"],
            "mode": _attack_state.get("mode"),
            "public_mode": _attack_public_mode(),
            "launch_mode": os.getenv("ATTACK_MODE", "auto"),
            "log_lines": list(_attack_log),
        })


# --- Startup ---

def _heartbeat_loop():
    while True:
        socketio.sleep(15)
        socketio.emit('heartbeat', {'ts': time.time()})


def _bootstrap_runtime():
    """Initialise Redis + Postgres + background threads. Called by both
    `python app.py` (dev) and the gunicorn entrypoint (prod)."""
    connect_redis()
    _bootstrap_database_schema()
    _ensure_kill_chain_status_columns()

    t1 = threading.Thread(target=redis_subscriber)
    t1.daemon = True
    t1.start()

    t2 = threading.Thread(target=periodic_metrics)
    t2.daemon = True
    t2.start()

    socketio.start_background_task(_heartbeat_loop)


# When loaded by gunicorn, bootstrap immediately on import.
if os.getenv("GUNICORN_BOOT", "0") == "1":
    _bootstrap_runtime()


if __name__ == '__main__':
    _bootstrap_runtime()

    print("========================================")
    print("  SecuriSphere Backend API v1.0.0")
    print(f"  Mode:       {FLASK_ENV}")
    print("========================================")
    print(f"  REST API:   http://0.0.0.0:{APP_PORT}")
    print(f"  WebSocket:  ws://0.0.0.0:{APP_PORT}")
    print(f"  Redis:      {services.REDIS_HOST}:{services.REDIS_PORT}")
    print("========================================")

    if IS_PRODUCTION:
        # Refuse to start the Flask dev server in production. Use gunicorn.
        raise RuntimeError(
            "Refusing to start Flask dev server in production. "
            "Use gunicorn: gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker "
            "-w 1 -b 0.0.0.0:8000 app:app"
        )

    socketio.run(app, host='0.0.0.0', port=APP_PORT, debug=False)
