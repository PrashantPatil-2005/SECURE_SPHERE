"""User management API — admin only."""

from __future__ import annotations

import logging
import re

import psycopg2
import psycopg2.extras
from flask import Blueprint, jsonify, request

from auth import _get_db_connection, _validate_password, token_required
from password_utils import hash_password
from rbac import ROLES, normalize_role, permission_required, permissions_for_role

try:
    from .audit import log_audit
except Exception:
    def log_audit(*_a, **_kw):
        return None

logger = logging.getLogger("SecuriSphereUsers")

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _user_row_to_dict(row) -> dict:
    role = normalize_role(row.get("role"))
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "role": role,
        "permissions": permissions_for_role(role),
        "is_active": bool(row.get("is_active", True)),
        "last_login_at": row["last_login_at"].isoformat() if row.get("last_login_at") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


@users_bp.route("", methods=["GET"])
@token_required
@permission_required("users.manage")
def list_users():
    include_deleted = request.args.get("include_deleted", "0") == "1"
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                q = (
                    "SELECT id, username, email, role, is_active, last_login_at, created_at, updated_at "
                    "FROM users "
                )
                if not include_deleted:
                    q += "WHERE deleted_at IS NULL "
                q += "ORDER BY username"
                cur.execute(q)
                rows = cur.fetchall() or []
        return jsonify({"status": "success", "users": [_user_row_to_dict(r) for r in rows]})
    finally:
        conn.close()


@users_bp.route("/<int:user_id>", methods=["GET"])
@token_required
@permission_required("users.manage")
def get_user(user_id: int):
    conn = _get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, email, role, is_active, last_login_at, created_at, updated_at "
                "FROM users WHERE id = %s AND deleted_at IS NULL",
                (user_id,),
            )
            row = cur.fetchone()
        if not row:
            return jsonify({"status": "error", "message": "User not found"}), 404
        return jsonify({"status": "success", "user": _user_row_to_dict(row)})
    finally:
        conn.close()


@users_bp.route("", methods=["POST"])
@token_required
@permission_required("users.manage")
def create_user():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    role = normalize_role(body.get("role") or "viewer")

    if not USERNAME_RE.match(username):
        return jsonify({"status": "error", "message": "Invalid username"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"status": "error", "message": "Invalid email"}), 400
    if role not in ROLES:
        return jsonify({"status": "error", "message": f"Role must be one of: {', '.join(ROLES)}"}), 400
    pw_err = _validate_password(password)
    if pw_err:
        return jsonify({"status": "error", "message": pw_err}), 400

    actor = request.current_user.get("username", "admin")
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT 1 FROM users WHERE (username = %s OR email = %s) AND deleted_at IS NULL",
                    (username, email),
                )
                if cur.fetchone():
                    return jsonify({"status": "error", "message": "Username or email already exists"}), 409
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role, is_active) "
                    "VALUES (%s, %s, %s, %s, TRUE) "
                    "RETURNING id, username, email, role, is_active, created_at, updated_at",
                    (username, email, hash_password(password), role),
                )
                row = cur.fetchone()
                cur.execute(
                    "INSERT INTO user_roles (user_id, role_id) "
                    "SELECT %s, id FROM roles WHERE name = %s ON CONFLICT DO NOTHING",
                    (row["id"], role),
                )
        log_audit(
            action="user.created",
            actor=actor,
            actor_type="user",
            target_type="user",
            target_id=str(row["id"]),
            detail={"username": username, "role": role},
            severity="info",
            source_ip=request.remote_addr,
        )
        return jsonify({"status": "success", "user": _user_row_to_dict(row)}), 201
    except psycopg2.Error as exc:
        logger.error("create_user db error: %s", exc)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        conn.close()


@users_bp.route("/<int:user_id>", methods=["PUT"])
@token_required
@permission_required("users.manage")
def update_user(user_id: int):
    body = request.get_json(silent=True) or {}
    actor = request.current_user.get("username", "admin")
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, email, role FROM users WHERE id = %s AND deleted_at IS NULL",
                    (user_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"status": "error", "message": "User not found"}), 404

                updates = []
                params = []
                if "email" in body:
                    email = (body.get("email") or "").strip().lower()
                    if not EMAIL_RE.match(email):
                        return jsonify({"status": "error", "message": "Invalid email"}), 400
                    updates.append("email = %s")
                    params.append(email)
                if "role" in body:
                    role = normalize_role(body.get("role"))
                    if role not in ROLES:
                        return jsonify({"status": "error", "message": "Invalid role"}), 400
                    updates.append("role = %s")
                    params.append(role)
                if "is_active" in body:
                    updates.append("is_active = %s")
                    params.append(bool(body.get("is_active")))
                if "password" in body and body.get("password"):
                    pw_err = _validate_password(body["password"])
                    if pw_err:
                        return jsonify({"status": "error", "message": pw_err}), 400
                    updates.append("password_hash = %s")
                    params.append(hash_password(body["password"]))

                if not updates:
                    return jsonify({"status": "error", "message": "No fields to update"}), 400

                updates.append("updated_at = NOW()")
                params.append(user_id)
                cur.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE id = %s "
                    "RETURNING id, username, email, role, is_active, last_login_at, created_at, updated_at",
                    params,
                )
                row = cur.fetchone()
                if "role" in body:
                    cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
                    cur.execute(
                        "INSERT INTO user_roles (user_id, role_id) "
                        "SELECT %s, id FROM roles WHERE name = %s",
                        (user_id, normalize_role(body.get("role"))),
                    )

        log_audit(
            action="user.updated",
            actor=actor,
            actor_type="user",
            target_type="user",
            target_id=str(user_id),
            detail={"fields": list(body.keys())},
            severity="info",
            source_ip=request.remote_addr,
        )
        return jsonify({"status": "success", "user": _user_row_to_dict(row)})
    except psycopg2.Error as exc:
        logger.error("update_user db error: %s", exc)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        conn.close()


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@token_required
@permission_required("users.manage")
def delete_user(user_id: int):
    if user_id == request.current_user.get("user_id"):
        return jsonify({"status": "error", "message": "Cannot delete your own account"}), 400

    actor = request.current_user.get("username", "admin")
    conn = _get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET deleted_at = NOW(), is_active = FALSE, updated_at = NOW() "
                    "WHERE id = %s AND deleted_at IS NULL RETURNING username",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
        log_audit(
            action="user.deleted",
            actor=actor,
            actor_type="user",
            target_type="user",
            target_id=str(user_id),
            detail={"username": row[0]},
            severity="warning",
            source_ip=request.remote_addr,
        )
        return jsonify({"status": "success", "success": True})
    except psycopg2.Error as exc:
        logger.error("delete_user db error: %s", exc)
        return jsonify({"status": "error", "message": "Internal server error"}), 500
    finally:
        conn.close()
