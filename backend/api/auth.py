"""
SecuriSphere — Authentication Blueprint
========================================
POST /api/auth/login   → Validate credentials, return JWT
POST /api/auth/verify  → Validate an existing JWT token
GET  /api/auth/me      → Return current user info from token

Security:
  • JWT_SECRET is REQUIRED in production (FLASK_ENV=production); boot fails otherwise.
  • Passwords are stored as Werkzeug pbkdf2/scrypt hashes. Plaintext passwords
    are accepted ONLY when ALLOW_PLAINTEXT_LOGIN=1 (legacy seed migration).
  • Default behaviour rejects any non-hashed password.
"""

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock

import jwt
import psycopg2
import psycopg2.extras
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from .audit import log_audit
except Exception:
    def log_audit(*_a, **_kw):
        return None

logger = logging.getLogger("SecuriSphereAuth")

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ── Configuration ───────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "1"))
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
ALLOW_PLAINTEXT_LOGIN = os.getenv("ALLOW_PLAINTEXT_LOGIN", "0") == "1"
ALLOW_PUBLIC_REGISTRATION = os.getenv("ALLOW_PUBLIC_REGISTRATION", "1") == "1"

# In-memory token blocklist for /logout. Process-local; fine for single worker.
_blocklist: set[str] = set()
_blocklist_lock = Lock()

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# In-memory active session table — process-local; OK for demo.
# token (jti-like) -> { user_id, username, role, issued_at, last_seen, ua, ip }
_sessions: dict[str, dict] = {}
_sessions_lock = Lock()


def _validate_password(pw: str):
    if len(pw) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Za-z]", pw):
        return "Password must contain at least one letter"
    if not re.search(r"\d", pw):
        return "Password must contain at least one digit"
    return None

if not JWT_SECRET or len(JWT_SECRET) < 16:
    if FLASK_ENV == "production":
        raise RuntimeError(
            "JWT_SECRET environment variable is required in production "
            "and must be at least 16 characters. Generate with: "
            "openssl rand -hex 32"
        )
    JWT_SECRET = JWT_SECRET or "dev-only-not-for-production"
    logger.warning(
        "JWT_SECRET is unset or weak — running in development fallback mode."
    )

# ── Database helper ─────────────────────────────────────────────────────────

def _get_db_connection():
    """Open a PostgreSQL connection using environment variables."""
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    pwd = os.getenv("POSTGRES_PASSWORD")
    if not pwd:
        raise RuntimeError("POSTGRES_PASSWORD is required")
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=pwd,
    )


def _ensure_audit_schema():
    """Create login_audit table. Append-only audit log for sign-in events."""
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS login_audit (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) NOT NULL,
                        success BOOLEAN NOT NULL,
                        reason VARCHAR(80),
                        ip VARCHAR(45),
                        user_agent VARCHAR(255),
                        at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    CREATE INDEX IF NOT EXISTS login_audit_username_idx ON login_audit(username);
                    CREATE INDEX IF NOT EXISTS login_audit_at_idx ON login_audit(at DESC);
                    """
                )
    except psycopg2.Error as exc:
        logger.error("Could not ensure login_audit schema: %s", exc)
    finally:
        if conn:
            conn.close()


def _record_audit(username, success, reason=""):
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        ua = request.headers.get("User-Agent", "")[:255]
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO login_audit (username, success, reason, ip, user_agent) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (username, success, reason[:80], ip[:45], ua),
                )
        conn.close()
    except Exception as exc:
        logger.warning("Could not record audit row: %s", exc)


def _track_session(token, payload):
    try:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
        ua = request.headers.get("User-Agent", "")[:255]
        with _sessions_lock:
            _sessions[token] = {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role"),
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "ip": ip,
                "user_agent": ua,
            }
            # Cap to last 1000 entries to avoid unbounded growth.
            if len(_sessions) > 1000:
                # Drop oldest by insertion order.
                first = next(iter(_sessions))
                _sessions.pop(first, None)
    except Exception:
        pass


def _ensure_auth_schema():
    """Create auth table for fresh deployments. NEVER seeds plaintext."""
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        email VARCHAR(100) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) DEFAULT 'user',
                        failed_attempts INTEGER NOT NULL DEFAULT 0,
                        locked_until TIMESTAMPTZ,
                        last_login_at TIMESTAMPTZ,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INTEGER NOT NULL DEFAULT 0;"
                )
                cur.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;"
                )
                cur.execute(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;"
                )

                # Bootstrap admin from env vars only — no hardcoded plaintext.
                bootstrap_user = os.getenv("ADMIN_BOOTSTRAP_USER")
                bootstrap_pwd = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
                if bootstrap_user and bootstrap_pwd:
                    cur.execute("SELECT 1 FROM users WHERE username=%s", (bootstrap_user,))
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO users (username,email,password_hash,role) "
                            "VALUES (%s,%s,%s,'admin')",
                            (bootstrap_user,
                             os.getenv("ADMIN_BOOTSTRAP_EMAIL", f"{bootstrap_user}@local"),
                             generate_password_hash(bootstrap_pwd)),
                        )
                        logger.info("Bootstrapped admin user '%s' from env", bootstrap_user)
    except psycopg2.Error as exc:
        logger.error("Could not ensure auth schema: %s", exc)
    finally:
        if conn:
            conn.close()


def _fetch_user_by_username(username):
    conn = None
    try:
        conn = _get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, role, failed_attempts, locked_until "
                "FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()
    finally:
        if conn:
            conn.close()


def _record_login_failure(username):
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET failed_attempts = failed_attempts + 1, "
                    "locked_until = CASE WHEN failed_attempts + 1 >= 5 "
                    "THEN NOW() + INTERVAL '15 minutes' ELSE locked_until END "
                    "WHERE username = %s",
                    (username,),
                )
    except Exception as exc:
        logger.warning("Could not record login failure: %s", exc)
    finally:
        if conn:
            conn.close()


def _record_login_success(user_id):
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET failed_attempts = 0, locked_until = NULL, "
                    "last_login_at = NOW() WHERE id = %s",
                    (user_id,),
                )
    except Exception as exc:
        logger.warning("Could not record login success: %s", exc)
    finally:
        if conn:
            conn.close()


# ── JWT helpers ─────────────────────────────────────────────────────────────

def _generate_token(user_row):
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_row["id"],
        "username": user_row["username"],
        "role": user_row["role"],
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token):
    try:
        with _blocklist_lock:
            if token in _blocklist:
                return None
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"status": "error", "message": "Missing or invalid Authorization header"}), 401
        payload = _decode_token(auth_header[7:])
        if payload is None:
            return jsonify({"status": "error", "message": "Invalid or expired token"}), 401
        request.current_user = payload
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Decorator to gate a route by user role. Apply after token_required."""
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user or user.get("role") not in allowed_roles:
                return jsonify({"status": "error", "message": "Forbidden"}), 403
            return f(*args, **kwargs)
        return decorated
    return wrapper


# ── Routes ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT."""
    _ensure_auth_schema()

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400

    try:
        user = _fetch_user_by_username(username)
    except psycopg2.Error as db_err:
        logger.error("Database error during login: %s", db_err)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    if user is None:
        # Constant-time-ish: still compute a dummy hash check
        check_password_hash(
            "pbkdf2:sha256:600000$dummy$0000000000000000000000000000000000000000000000000000000000000000",
            password,
        )
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    # Lockout enforcement
    locked_until = user.get("locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc):
        return jsonify({"status": "error", "message": "Account temporarily locked. Try again later."}), 423

    stored_hash = user["password_hash"] or ""
    password_valid = False

    if stored_hash.startswith(("pbkdf2:", "scrypt:", "$2a$", "$2b$", "$argon2")):
        try:
            password_valid = check_password_hash(stored_hash, password)
        except Exception:
            password_valid = False
    elif ALLOW_PLAINTEXT_LOGIN and FLASK_ENV != "production":
        # Legacy plaintext path — strictly opt-in and never in prod.
        password_valid = (stored_hash == password)
        if password_valid:
            # Auto-upgrade to hash on first successful login.
            try:
                conn = _get_db_connection()
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE users SET password_hash=%s WHERE id=%s",
                            (generate_password_hash(password), user["id"]),
                        )
                conn.close()
            except Exception as exc:
                logger.warning("Plaintext-to-hash upgrade failed: %s", exc)
    else:
        password_valid = False  # plaintext stored but plaintext login disabled

    if not password_valid:
        _record_login_failure(username)
        _ensure_audit_schema()
        _record_audit(username, False, "invalid_credentials")
        log_audit(
            action="user.login_failed",
            actor=username or "unknown",
            actor_type="user",
            target_type="user",
            target_id=username,
            detail={"reason": "invalid_credentials"},
            severity="warning",
            source_ip=request.remote_addr,
        )
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    _record_login_success(user["id"])
    token = _generate_token(user)
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    _track_session(token, payload)
    _ensure_audit_schema()
    _record_audit(username, True, "login")
    log_audit(
        action="user.login",
        actor=username,
        actor_type="user",
        target_type="user",
        target_id=str(user.get("id")),
        detail={"role": user.get("role")},
        severity="info",
        source_ip=request.remote_addr,
    )

    logger.info("User '%s' authenticated successfully", username)
    return jsonify({
        "status": "success",
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
    })


@auth_bp.route("/verify", methods=["POST"])
def verify():
    body = request.get_json(silent=True)
    token = (body or {}).get("token", "")

    if not token:
        return jsonify({"status": "error", "message": "Token is required"}), 400

    payload = _decode_token(token)
    if payload is None:
        return jsonify({"status": "error", "valid": False, "message": "Invalid or expired token"}), 401

    return jsonify({"status": "success", "valid": True, "user": {
        "user_id": payload["user_id"],
        "username": payload["username"],
        "role": payload["role"],
    }})


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    user = request.current_user
    return jsonify({"status": "success", "user": {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }})


@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a new user account. Hashed password, default role 'user'."""
    if not ALLOW_PUBLIC_REGISTRATION:
        return jsonify({"status": "error", "message": "Public registration is disabled"}), 403

    _ensure_auth_schema()

    body = request.get_json(silent=True)
    if not body:
        return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not USERNAME_RE.match(username):
        return jsonify({"status": "error", "message": "Username must be 3-32 chars (letters, digits, _.-)"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"status": "error", "message": "Invalid email address"}), 400
    pw_err = _validate_password(password)
    if pw_err:
        return jsonify({"status": "error", "message": pw_err}), 400

    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM users WHERE username=%s OR email=%s", (username, email))
                if cur.fetchone():
                    return jsonify({"status": "error", "message": "Username or email already in use"}), 409
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role) "
                    "VALUES (%s, %s, %s, 'user') RETURNING id, username, role",
                    (username, email, generate_password_hash(password)),
                )
                row = cur.fetchone()
                user_row = {"id": row[0], "username": row[1], "role": row[2]}
    except psycopg2.Error as db_err:
        logger.error("Database error during registration: %s", db_err)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        if conn:
            conn.close()

    token = _generate_token(user_row)
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    _track_session(token, payload)
    _ensure_audit_schema()
    _record_audit(username, True, "register")
    logger.info("Registered new user '%s'", username)
    return jsonify({
        "status": "success",
        "success": True,
        "token": token,
        "user": user_row,
    }), 201


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    """Revoke the current bearer token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if token:
        with _blocklist_lock:
            _blocklist.add(token)
            # Cap blocklist size to avoid unbounded growth.
            if len(_blocklist) > 10000:
                _blocklist.clear()
        with _sessions_lock:
            _sessions.pop(token, None)
    return jsonify({"status": "success", "success": True})


@auth_bp.route("/change-password", methods=["POST"])
@token_required
def change_password():
    """Change current user's password. Requires current password."""
    body = request.get_json(silent=True) or {}
    current = body.get("current_password") or ""
    new_pw = body.get("new_password") or ""

    if not current or not new_pw:
        return jsonify({"status": "error", "message": "Current and new password required"}), 400

    pw_err = _validate_password(new_pw)
    if pw_err:
        return jsonify({"status": "error", "message": pw_err}), 400
    if current == new_pw:
        return jsonify({"status": "error", "message": "New password must differ from current"}), 400

    user_id = request.current_user.get("user_id")
    username = request.current_user.get("username", "")

    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
                row = cur.fetchone()
                if not row:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                if not check_password_hash(row["password_hash"] or "", current):
                    _ensure_audit_schema()
                    _record_audit(username, False, "change_password_invalid")
                    return jsonify({"status": "error", "message": "Current password incorrect"}), 401
                cur.execute(
                    "UPDATE users SET password_hash=%s WHERE id=%s",
                    (generate_password_hash(new_pw), user_id),
                )
    except psycopg2.Error as db_err:
        logger.error("Database error during change-password: %s", db_err)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        if conn:
            conn.close()

    _ensure_audit_schema()
    _record_audit(username, True, "change_password")
    logger.info("User '%s' changed password", username)
    return jsonify({"status": "success", "success": True})


@auth_bp.route("/audit/logins", methods=["GET"])
@token_required
def audit_logins():
    """Recent login audit rows for current user. Admins see all users."""
    _ensure_audit_schema()
    user = request.current_user
    is_admin = (user.get("role") == "admin")
    limit = max(1, min(int(request.args.get("limit", 50)), 200))

    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if is_admin:
                    cur.execute(
                        "SELECT id, username, success, reason, ip, user_agent, at "
                        "FROM login_audit ORDER BY at DESC LIMIT %s",
                        (limit,),
                    )
                else:
                    cur.execute(
                        "SELECT id, username, success, reason, ip, user_agent, at "
                        "FROM login_audit WHERE username = %s ORDER BY at DESC LIMIT %s",
                        (user.get("username"), limit),
                    )
                rows = cur.fetchall() or []
    except psycopg2.Error as db_err:
        logger.error("Database error during audit list: %s", db_err)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        if conn:
            conn.close()

    out = [
        {
            "id": r["id"],
            "username": r["username"],
            "success": bool(r["success"]),
            "reason": r["reason"],
            "ip": r["ip"],
            "user_agent": r["user_agent"],
            "at": r["at"].isoformat() if r["at"] else None,
        }
        for r in rows
    ]
    return jsonify({"status": "success", "data": out})


@auth_bp.route("/sessions", methods=["GET"])
@token_required
def list_sessions():
    """Active sessions for current user. Admins see all."""
    user = request.current_user
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    is_admin = (user.get("role") == "admin")
    out = []
    with _sessions_lock:
        for tok, info in _sessions.items():
            if not is_admin and info.get("user_id") != user.get("user_id"):
                continue
            out.append({
                "token_fp": tok[-12:],  # fingerprint, not the full token
                "username": info.get("username"),
                "role": info.get("role"),
                "issued_at": info.get("issued_at"),
                "ip": info.get("ip"),
                "user_agent": info.get("user_agent"),
                "current": tok == current_token,
            })
    return jsonify({"status": "success", "data": out})


@auth_bp.route("/sessions/<token_fp>", methods=["DELETE"])
@token_required
def revoke_session(token_fp):
    """Revoke a session by token fingerprint (last 12 chars)."""
    user = request.current_user
    is_admin = (user.get("role") == "admin")
    target = None
    with _sessions_lock:
        for tok, info in _sessions.items():
            if tok.endswith(token_fp):
                if not is_admin and info.get("user_id") != user.get("user_id"):
                    return jsonify({"status": "error", "message": "Forbidden"}), 403
                target = tok
                break
        if not target:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        _sessions.pop(target, None)
    with _blocklist_lock:
        _blocklist.add(target)
        if len(_blocklist) > 10000:
            _blocklist.clear()
    return jsonify({"status": "success", "success": True})


@auth_bp.route("/refresh", methods=["POST"])
@token_required
def refresh():
    """Issue a fresh token to a still-valid session. Old token is revoked."""
    user = request.current_user
    auth_header = request.headers.get("Authorization", "")
    old_token = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    user_row = {
        "id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }
    new_token = _generate_token(user_row)
    new_payload = jwt.decode(new_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    _track_session(new_token, new_payload)

    if old_token:
        with _blocklist_lock:
            _blocklist.add(old_token)
            if len(_blocklist) > 10000:
                _blocklist.clear()
        with _sessions_lock:
            _sessions.pop(old_token, None)

    return jsonify({
        "status": "success",
        "success": True,
        "token": new_token,
        "user": user_row,
    })


@auth_bp.route("/forgot", methods=["POST"])
def forgot():
    """Stub forgot-password. Always returns 200 to avoid user enumeration."""
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if email:
        logger.info("Password reset requested for %s (no-op stub)", email)
    return jsonify({
        "status": "success",
        "message": "If that email exists, a reset link has been sent.",
    })
