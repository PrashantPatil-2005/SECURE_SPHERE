"""
SecuriSphere — Authentication Blueprint
========================================
POST /api/auth/login   → Validate credentials, return JWT
POST /api/auth/verify  → Validate an existing JWT token
GET  /api/auth/me      → Return current user info from token

All database credentials are read from environment variables.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
import psycopg2
import psycopg2.extras
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

logger = logging.getLogger("SecuriSphereAuth")

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ── Configuration ───────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "securisphere-default-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 1))


# ── Database helper ─────────────────────────────────────────────────────────

def _get_db_connection():
    """Open a PostgreSQL connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )

def _ensure_auth_schema():
    """Create auth table and seed users for fresh cloud databases."""
    conn = None
    try:
        conn = _get_db_connection()
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) NOT NULL UNIQUE,
                        email VARCHAR(100) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) DEFAULT 'user',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """)
                cur.execute("""
                    INSERT INTO users (username, email, password_hash, role) VALUES
                    ('admin', 'admin@example.com', 'admin123', 'admin'),
                    ('user1', 'user1@example.com', 'password123', 'user'),
                    ('user2', 'user2@example.com', 'securepass', 'user')
                    ON CONFLICT (username) DO NOTHING;
                """)
    except psycopg2.Error as exc:
        logger.error("Could not ensure auth schema: %s", exc)
    finally:
        if conn:
            conn.close()


def _fetch_user_by_username(username):
    """Query the users table and return the row as a dict, or None."""
    conn = None
    try:
        conn = _get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()
    finally:
        if conn:
            conn.close()


# ── JWT helpers ─────────────────────────────────────────────────────────────

def _generate_token(user_row):
    """Create a signed JWT for the authenticated user."""
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
    """Decode and validate a JWT. Returns the payload dict or None."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def token_required(f):
    """Decorator that protects a route with JWT authentication."""
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


# ── Routes ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT."""
    _ensure_auth_schema()

    # 1. Parse request body
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required"}), 400

    # 2. Look up user
    try:
        user = _fetch_user_by_username(username)
    except psycopg2.Error as db_err:
        logger.error("Database error during login: %s", db_err)
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    if user is None:
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    # 3. Verify password
    #    Support both werkzeug-hashed passwords and legacy plaintext seeds
    stored_hash = user["password_hash"]
    password_valid = False

    if stored_hash.startswith(("pbkdf2:", "scrypt:")):
        # Werkzeug-hashed password
        password_valid = check_password_hash(stored_hash, password)
    else:
        # Legacy plaintext fallback (from init_db.sql seed data)
        password_valid = (stored_hash == password)

    if not password_valid:
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401

    # 4. Generate JWT
    token = _generate_token(user)

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
    """Verify that a JWT is still valid."""
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
    """Return the current user's profile from their JWT."""
    user = request.current_user
    return jsonify({"status": "success", "user": {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }})
