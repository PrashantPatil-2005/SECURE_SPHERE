"""
RBAC — roles, permissions, decorators for Flask routes.
"""

from __future__ import annotations

from functools import wraps
from typing import Dict, Iterable, List, Set, Tuple

ROLES: Tuple[str, ...] = ("admin", "analyst", "viewer")

# permission → roles allowed
PERMISSIONS: Dict[str, Tuple[str, ...]] = {
    "users.manage": ("admin",),
    "incidents.read": ("admin", "analyst", "viewer"),
    "incidents.write": ("admin", "analyst"),
    "campaigns.read": ("admin", "analyst"),
    "dashboard.read": ("admin", "analyst", "viewer"),
    "topology.read": ("admin", "analyst", "viewer"),
    "mitre.read": ("admin", "analyst"),
    "reports.generate": ("admin", "analyst"),
    "audit.read": ("admin",),
    "system.manage": ("admin",),
    "alerts.manage": ("admin",),
    "evaluation.read": ("admin", "analyst"),
    "replay.read": ("admin", "analyst"),
}

# Nav / route visibility hints for frontend
NAV_BY_ROLE: Dict[str, Tuple[str, ...]] = {
    "admin": (
        "dashboard", "events", "incidents", "campaigns", "evaluation",
        "topology", "risk", "mitre", "replay", "audit", "system", "users",
    ),
    "analyst": (
        "dashboard", "events", "incidents", "campaigns", "evaluation",
        "topology", "risk", "mitre", "replay",
    ),
    "viewer": ("dashboard", "events", "incidents", "topology", "risk"),
}


def normalize_role(role: str | None) -> str:
    if not role:
        return "viewer"
    r = role.lower().strip()
    if r in ("user", "readonly", "guest"):
        return "viewer"
    return r if r in ROLES else "viewer"


def permissions_for_role(role: str | None) -> List[str]:
    r = normalize_role(role)
    return sorted(p for p, roles in PERMISSIONS.items() if r in roles)


def role_has_permission(role: str | None, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission, ())
    return normalize_role(role) in allowed


def roles_for_permission(permission: str) -> Tuple[str, ...]:
    return PERMISSIONS.get(permission, ())


def permission_required(*required: str):
    """Gate a route by permission(s). User needs ANY listed permission."""

    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import jsonify, request

            user = getattr(request, "current_user", None)
            if not user:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            role = normalize_role(user.get("role"))
            perms: Set[str] = set(user.get("permissions") or permissions_for_role(role))
            if not any(p in perms for p in required):
                return jsonify({"status": "error", "message": "Forbidden"}), 403
            return f(*args, **kwargs)

        return decorated

    return wrapper


def any_role(*allowed: Iterable[str]):
    """Decorator factory — allowed role names."""

    allowed_set = {normalize_role(r) for r in allowed}

    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from flask import jsonify, request

            user = getattr(request, "current_user", None)
            if not user:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            if normalize_role(user.get("role")) not in allowed_set:
                return jsonify({"status": "error", "message": "Forbidden"}), 403
            return f(*args, **kwargs)

        return decorated

    return wrapper
