"""
SecuriSphere — Authentication Blueprint
========================================
POST /api/auth/login    → Credentials → access + refresh JWTs
POST /api/auth/refresh  → Rotate refresh token
POST /api/auth/logout   → Revoke tokens
GET  /api/auth/me       → Current user + permissions

Security:
  • bcrypt password hashing (Werkzeug legacy verified on login, auto-upgraded)
  • Short-lived access JWT + DB-backed refresh token rotation
  • RBAC roles: admin, analyst, viewer
"""

import hashlib
import os
import re
import secrets
import logging
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from threading import Lock

import jwt
import psycopg2
import psycopg2.extras
from flask import Blueprint, jsonify, request

from password_utils import hash_password, verify_password, needs_rehash, upgrade_hash
from rbac import normalize_role, permissions_for_role, permission_required, ROLES

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
if os.getenv("JWT_ACCESS_MINUTES"):
    JWT_ACCESS_MINUTES = int(os.getenv("JWT_ACCESS_MINUTES"))
elif os.getenv("JWT_EXPIRATION_HOURS"):
    JWT_ACCESS_MINUTES = int(float(os.getenv("JWT_EXPIRATION_HOURS", "1")) * 60)
else:
    JWT_ACCESS_MINUTES = 15
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))
FLASK_ENV = os.getenv("FLASK_ENV", "production").lower()
ALLOW_PLAINTEXT_LOGIN = os.getenv("ALLOW_PLAINTEXT_LOGIN", "0") == "1"
ALLOW_PUBLIC_REGISTRATION = os.getenv("ALLOW_PUBLIC_REGISTRATION", "0") == "1"

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
    """Create auth + RBAC tables for fresh deployments."""
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        email VARCHAR(100) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) DEFAULT 'viewer',
                        failed_attempts INTEGER NOT NULL DEFAULT 0,
                        locked_until TIMESTAMPTZ,
                        last_login_at TIMESTAMPTZ,
                        deleted_at TIMESTAMPTZ,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                for stmt in (
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_attempts INTEGER NOT NULL DEFAULT 0;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
                    """
                    CREATE TABLE IF NOT EXISTS roles (
                        id SERIAL PRIMARY KEY, name VARCHAR(32) NOT NULL UNIQUE,
                        description TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS refresh_tokens (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash VARCHAR(64) NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        revoked_at TIMESTAMPTZ,
                        replaced_by UUID,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        ip VARCHAR(45), user_agent VARCHAR(255)
                    );
                    """,
                    "UPDATE users SET role = 'viewer' WHERE role IN ('user','readonly','guest');",
                ):
                    cur.execute(stmt)

                for role_name, desc in (
                    ("admin", "Full platform control"),
                    ("analyst", "Investigate incidents and campaigns"),
                    ("viewer", "Read-only dashboards"),
                ):
                    cur.execute(
                        "INSERT INTO roles (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                        (role_name, desc),
                    )

                bootstrap_user = os.getenv("ADMIN_BOOTSTRAP_USER")
                bootstrap_pwd = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
                if bootstrap_user and bootstrap_pwd:
                    cur.execute(
                        "SELECT 1 FROM users WHERE username=%s AND deleted_at IS NULL",
                        (bootstrap_user,),
                    )
                    if not cur.fetchone():
                        cur.execute(
                            "INSERT INTO users (username,email,password_hash,role) "
                            "VALUES (%s,%s,%s,'admin')",
                            (
                                bootstrap_user,
                                os.getenv("ADMIN_BOOTSTRAP_EMAIL", f"{bootstrap_user}@local"),
                                hash_password(bootstrap_pwd),
                            ),
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
                "SELECT id, username, email, password_hash, role, failed_attempts, locked_until, is_active "
                "FROM users WHERE username = %s AND deleted_at IS NULL",
                (username,),
            )
            return cur.fetchone()
    finally:
        if conn:
            conn.close()


def _client_meta():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    if ip and "," in ip:
        ip = ip.split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")[:255]
    return ip[:45], ua


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _store_refresh_token(user_id: int, raw_token: str) -> str:
    token_id = str(uuid.uuid4())
    ip, ua = _client_meta()
    expires = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_DAYS)
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, ip, user_agent) "
                    "VALUES (%s::uuid, %s, %s, %s, %s, %s)",
                    (token_id, user_id, _hash_refresh(raw_token), expires, ip, ua),
                )
    finally:
        conn.close()
    return token_id


def _revoke_refresh_token(token_id: str, replaced_by: str | None = None):
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE refresh_tokens SET revoked_at = NOW(), replaced_by = %s::uuid "
                    "WHERE id = %s::uuid AND revoked_at IS NULL",
                    (replaced_by, token_id),
                )
    finally:
        conn.close()


def _lookup_refresh(raw_token: str):
    conn = _get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT rt.id, rt.user_id, rt.expires_at, u.username, u.role, u.is_active "
                "FROM refresh_tokens rt JOIN users u ON u.id = rt.user_id "
                "WHERE rt.token_hash = %s AND rt.revoked_at IS NULL AND u.deleted_at IS NULL",
                (_hash_refresh(raw_token),),
            )
            return cur.fetchone()
    finally:
        conn.close()


def _user_payload(user_row) -> dict:
    role = normalize_role(user_row.get("role"))
    return {
        "id": user_row["id"],
        "user_id": user_row["id"],
        "username": user_row["username"],
        "email": user_row.get("email"),
        "role": role,
        "permissions": permissions_for_role(role),
    }


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

def _generate_access_token(user_row):
    now = datetime.now(timezone.utc)
    role = normalize_role(user_row.get("role"))
    payload = {
        "user_id": user_row["id"],
        "username": user_row["username"],
        "role": role,
        "permissions": permissions_for_role(role),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=JWT_ACCESS_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _generate_refresh_token_value():
    return secrets.token_urlsafe(48)


def _issue_token_pair(user_row):
    access = _generate_access_token(user_row)
    refresh_raw = _generate_refresh_token_value()
    refresh_id = _store_refresh_token(user_row["id"], refresh_raw)
    return access, refresh_raw, refresh_id


def _decode_token(token, expected_type: str | None = "access"):
    try:
        with _blocklist_lock:
            if token in _blocklist:
                return None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        tok_type = payload.get("type", "access")
        if expected_type and tok_type != expected_type:
            return None
        return payload
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
    allowed = {normalize_role(r) for r in allowed_roles}

    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user or normalize_role(user.get("role")) not in allowed:
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
        verify_password("$2b$12$000000000000000000000000000000000000000000000000000000000", password)
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    if not user.get("is_active", True):
        return jsonify({"status": "error", "message": "Account is disabled"}), 403

    locked_until = user.get("locked_until")
    if locked_until and locked_until > datetime.now(timezone.utc):
        return jsonify({"status": "error", "message": "Account temporarily locked. Try again later."}), 423

    stored_hash = user["password_hash"] or ""
    password_valid = verify_password(stored_hash, password)

    if not password_valid and ALLOW_PLAINTEXT_LOGIN and FLASK_ENV != "production":
        password_valid = stored_hash == password

    if password_valid and (needs_rehash(stored_hash) or (
        ALLOW_PLAINTEXT_LOGIN and stored_hash == password
    )):
        try:
            conn = _get_db_connection()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password_hash=%s WHERE id=%s",
                        (upgrade_hash(password), user["id"]),
                    )
            conn.close()
        except Exception as exc:
            logger.warning("Password hash upgrade failed: %s", exc)

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
    access_token, refresh_token, _refresh_id = _issue_token_pair(user)
    payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    _track_session(access_token, payload)
    _ensure_audit_schema()
    _record_audit(username, True, "login")
    log_audit(
        action="user.login",
        actor=username,
        actor_type="user",
        target_type="user",
        target_id=str(user.get("id")),
        detail={"role": normalize_role(user.get("role"))},
        severity="info",
        source_ip=request.remote_addr,
    )

    user_out = _user_payload(user)
    logger.info("User '%s' authenticated successfully", username)
    return jsonify({
        "status": "success",
        "success": True,
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": JWT_ACCESS_MINUTES * 60,
        "user": user_out,
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
    role = normalize_role(user.get("role"))
    return jsonify({
        "status": "success",
        "user": {
            "user_id": user["user_id"],
            "id": user["user_id"],
            "username": user["username"],
            "role": role,
            "permissions": user.get("permissions") or permissions_for_role(role),
        },
    })


@auth_bp.route("/permissions", methods=["GET"])
@token_required
def list_permissions():
    role = normalize_role(request.current_user.get("role"))
    return jsonify({
        "status": "success",
        "role": role,
        "permissions": permissions_for_role(role),
        "roles": list(ROLES),
    })


@auth_bp.route("/register", methods=["POST"])
def register():
    """Public self-registration disabled — admins create users via POST /api/users."""
    if ALLOW_PUBLIC_REGISTRATION:
        return jsonify({
            "status": "error",
            "message": "Public registration is deprecated. Contact an administrator.",
        }), 403
    return jsonify({
        "status": "error",
        "message": "Registration is disabled. Accounts are created by administrators.",
    }), 403


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
                if not verify_password(row["password_hash"] or "", current):
                    _ensure_audit_schema()
                    _record_audit(username, False, "change_password_invalid")
                    return jsonify({"status": "error", "message": "Current password incorrect"}), 401
                cur.execute(
                    "UPDATE users SET password_hash=%s, updated_at=NOW() WHERE id=%s",
                    (hash_password(new_pw), user_id),
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
def refresh():
    """Rotate refresh token → new access + refresh pair."""
    body = request.get_json(silent=True) or {}
    refresh_raw = (body.get("refresh_token") or "").strip()
    auth_header = request.headers.get("Authorization", "")
    if not refresh_raw and auth_header.startswith("Bearer "):
        refresh_raw = auth_header[7:].strip()

    if not refresh_raw:
        return jsonify({"status": "error", "message": "refresh_token required"}), 400

    row = _lookup_refresh(refresh_raw)
    if not row:
        return jsonify({"status": "error", "message": "Invalid refresh token"}), 401

    expires = row.get("expires_at")
    if expires and expires < datetime.now(timezone.utc):
        _revoke_refresh_token(str(row["id"]))
        return jsonify({"status": "error", "message": "Refresh token expired"}), 401

    if not row.get("is_active", True):
        return jsonify({"status": "error", "message": "Account disabled"}), 403

    user_row = {
        "id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
    }
    old_id = str(row["id"])
    access_token, new_refresh, new_id = _issue_token_pair(user_row)
    _revoke_refresh_token(old_id, replaced_by=new_id)

    payload = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    _track_session(access_token, payload)

    user_out = _user_payload(user_row)
    return jsonify({
        "status": "success",
        "success": True,
        "token": access_token,
        "access_token": access_token,
        "refresh_token": new_refresh,
        "expires_in": JWT_ACCESS_MINUTES * 60,
        "user": user_out,
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
