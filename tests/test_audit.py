"""
Audit log — unit + integration tests.

Unit tests cover the audit module in isolation by stubbing psycopg2.connect
so they run without a live database. The integration test hits the JWT-
protected `/api/v2/audit/logs` endpoint and skips when the stack is down.

Run with:
    pytest tests/test_audit.py -v
"""
from __future__ import annotations

import os
import sys
import importlib
from unittest.mock import MagicMock, patch

import pytest

# Make backend/api importable regardless of repo layout.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend", "api"))


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fresh_audit_module():
    """Return a freshly-imported audit module so per-process schema state resets."""
    if "audit" in sys.modules:
        del sys.modules["audit"]
    return importlib.import_module("audit")


def _mock_conn(rows=None, count=0):
    """Build a minimal psycopg2 connection mock that supports `with conn:` and cursors."""
    cur = MagicMock()
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchone.return_value = {"n": count}
    cur.fetchall.return_value = rows or []

    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value = cur
    return conn, cur


# ── Unit tests — log_audit ──────────────────────────────────────────────────

def test_log_audit_inserts_row_with_validated_fields():
    audit = _fresh_audit_module()
    conn, cur = _mock_conn()
    with patch.object(audit, "_get_conn", return_value=conn):
        audit.log_audit(
            action="kill_chain.created",
            actor="engine",
            actor_type="engine",
            target_type="kill_chain",
            target_id="abc-123",
            detail={"rule_name": "brute_force_attempt", "service_path": ["auth", "api"]},
            severity="critical",
            source_ip="10.0.0.1",
        )

    insert_calls = [c for c in cur.execute.call_args_list if "INSERT INTO audit_log" in str(c.args[0])]
    assert insert_calls, "Expected an INSERT INTO audit_log statement"
    args = insert_calls[-1].args[1]
    assert args[0] == "engine"               # actor
    assert args[1] == "engine"               # actor_type
    assert args[2] == "kill_chain.created"   # action
    assert args[3] == "kill_chain"           # target_type
    assert args[4] == "abc-123"              # target_id
    assert args[6] == "critical"             # severity
    assert args[7] == "10.0.0.1"             # source_ip


def test_log_audit_rejects_invalid_actor_type_and_severity():
    """Invalid enum values fall back to defaults instead of breaking the insert."""
    audit = _fresh_audit_module()
    conn, cur = _mock_conn()
    with patch.object(audit, "_get_conn", return_value=conn):
        audit.log_audit(action="user.login", actor="alice", actor_type="ghost", severity="apocalyptic")

    insert_call = [c for c in cur.execute.call_args_list if "INSERT INTO audit_log" in str(c.args[0])][-1]
    args = insert_call.args[1]
    assert args[1] == "system"   # actor_type fell back
    assert args[6] == "info"     # severity fell back


def test_log_audit_silent_fail_when_db_down():
    """Audit failures must not propagate — engine must keep running."""
    audit = _fresh_audit_module()
    with patch.object(audit, "_get_conn", side_effect=RuntimeError("db down")):
        # Must not raise.
        audit.log_audit(action="user.login", actor="bob", actor_type="user")


def test_log_audit_drops_empty_action():
    audit = _fresh_audit_module()
    with patch.object(audit, "_get_conn") as gc:
        audit.log_audit(action="")
        gc.assert_not_called()


# ── Unit tests — query_audit ────────────────────────────────────────────────

def test_query_audit_clamps_limit_and_returns_shape():
    audit = _fresh_audit_module()
    sample = [{
        "id": "00000000-0000-0000-0000-000000000001",
        "timestamp": None,
        "actor": "engine",
        "actor_type": "engine",
        "action": "kill_chain.created",
        "target_type": "kill_chain",
        "target_id": "abc",
        "detail": {"rule_name": "brute_force"},
        "severity": "critical",
        "source_ip": "10.0.0.1",
    }]
    conn, cur = _mock_conn(rows=sample, count=1)
    with patch.object(audit, "_get_conn", return_value=conn):
        result = audit.query_audit(severity="critical", action_prefix="kill_chain", limit=99999)

    assert result["total"] == 1
    assert len(result["logs"]) == 1
    assert result["logs"][0]["action"] == "kill_chain.created"

    # Limit clamped to 500 in the SELECT params.
    select_call = [c for c in cur.execute.call_args_list if "SELECT id" in str(c.args[0])][-1]
    params = select_call.args[1]
    assert params[-1] == 500


def test_query_audit_builds_where_clause_safely():
    audit = _fresh_audit_module()
    conn, cur = _mock_conn(rows=[], count=0)
    with patch.object(audit, "_get_conn", return_value=conn):
        audit.query_audit(actor="alice", action_prefix="user.", severity="warning",
                          start="2026-01-01T00:00:00Z", end="2026-12-31T23:59:59Z")

    count_sql = [c for c in cur.execute.call_args_list if "SELECT COUNT" in str(c.args[0])][-1].args[0]
    # All four filters present, parameterised with %s placeholders only.
    assert "actor = %s" in count_sql
    assert "action LIKE %s" in count_sql
    assert "severity = %s" in count_sql
    assert "timestamp >= %s" in count_sql
    assert "timestamp <= %s" in count_sql


# ── Integration test — JWT-protected REST endpoint ──────────────────────────

BACKEND_URL = os.getenv("SECURISPHERE_API_URL", "http://localhost:8000")


def _backend_up():
    try:
        import requests
        return requests.get(f"{BACKEND_URL}/api/metrics", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _backend_up(), reason="Backend not reachable — start the stack to run integration tests")
def test_audit_endpoint_requires_jwt():
    import requests
    resp = requests.get(f"{BACKEND_URL}/api/v2/audit/logs", timeout=5)
    assert resp.status_code == 401, f"Expected 401 without JWT, got {resp.status_code}"


@pytest.mark.skipif(not _backend_up(), reason="Backend not reachable — start the stack to run integration tests")
def test_audit_endpoint_returns_envelope_with_jwt():
    import requests
    user = os.getenv("AUDIT_TEST_USER")
    pw = os.getenv("AUDIT_TEST_PASSWORD")
    if not (user and pw):
        pytest.skip("Set AUDIT_TEST_USER / AUDIT_TEST_PASSWORD to run authenticated integration tests")

    login = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": user, "password": pw},
        timeout=5,
    )
    assert login.status_code == 200, login.text
    token = login.json().get("token")
    assert token

    resp = requests.get(
        f"{BACKEND_URL}/api/v2/audit/logs?limit=5",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = body.get("data") or body
    assert "total" in data
    assert "logs" in data
    assert isinstance(data["logs"], list)
