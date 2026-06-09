"""Unit tests for RBAC and password utilities."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "api"))
sys.path.insert(0, ROOT)

from rbac import (  # noqa: E402
    NAV_BY_ROLE,
    PERMISSIONS,
    normalize_role,
    permissions_for_role,
    role_has_permission,
)
from password_utils import hash_password, verify_password, needs_rehash  # noqa: E402


def test_normalize_role_legacy():
    assert normalize_role("user") == "viewer"
    assert normalize_role("ADMIN") == "admin"


def test_admin_has_user_management():
    assert role_has_permission("admin", "users.manage")
    assert not role_has_permission("analyst", "users.manage")
    assert not role_has_permission("viewer", "users.manage")


def test_viewer_read_only_permissions():
    perms = set(permissions_for_role("viewer"))
    assert "incidents.read" in perms
    assert "incidents.write" not in perms
    assert "users.manage" not in perms


def test_analyst_investigation_permissions():
    perms = set(permissions_for_role("analyst"))
    assert "campaigns.read" in perms
    assert "mitre.read" in perms
    assert "audit.read" not in perms


def test_nav_visibility_by_role():
    assert "users" in NAV_BY_ROLE["admin"]
    assert "users" not in NAV_BY_ROLE["analyst"]
    assert "topology" in NAV_BY_ROLE["viewer"]


def test_bcrypt_hash_and_verify():
    hashed = hash_password("TestPass123")
    assert hashed.startswith("$2b$")
    assert verify_password(hashed, "TestPass123")
    assert not verify_password(hashed, "wrong")
    assert not needs_rehash(hashed)


def test_all_permissions_have_roles():
    for perm, roles in PERMISSIONS.items():
        assert roles, f"{perm} has no roles"
        for r in roles:
            assert r in ("admin", "analyst", "viewer")
