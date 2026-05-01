"""
test_account_pivot.py — Unit tests for username extraction + account-pivot rule.

Covers:
  * `_extract_username` priority order across event types
  * `rule_account_pivot` trigger conditions (positive + negative paths)

Engine instantiation is bypassed via `object.__new__` so tests stay
DB/Redis-free. `create_incident` is monkey-patched per test to capture the
incident dict the rule would have built.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

# Make backend/engine importable.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend", "engine"))
sys.path.insert(0, os.path.join(ROOT, "backend", "engine", "correlation"))

from correlation.correlation_engine import CorrelationEngine  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────────

def _engine():
    """Build an engine without running __init__ (no Redis / no DB)."""
    eng = object.__new__(CorrelationEngine)
    eng.incident_cooldowns = {}
    eng.cooldown_duration = timedelta(minutes=5)
    eng.create_incident = MagicMock(return_value={"_called": True})
    return eng


def _login_event(ip="10.0.0.1", username="alice", offset_seconds=0):
    ts = (datetime.now() - timedelta(seconds=offset_seconds)).isoformat()
    return {
        "event_id": f"login-{offset_seconds}",
        "event_type": "login_success",
        "source_layer": "auth",
        "source_entity": {"ip": ip},
        "target_entity": {"username": username},
        "timestamp": ts,
    }


def _api_event(ip="10.0.0.1", etype="sql_injection", offset_seconds=0):
    ts = (datetime.now() - timedelta(seconds=offset_seconds)).isoformat()
    return {
        "event_id": f"api-{etype}-{offset_seconds}",
        "event_type": etype,
        "source_layer": "api",
        "source_entity": {"ip": ip},
        "target_entity": {},
        "timestamp": ts,
    }


# ── _extract_username ───────────────────────────────────────────────────────

class TestExtractUsername:

    def test_returns_none_for_empty(self):
        assert CorrelationEngine._extract_username([]) is None
        assert CorrelationEngine._extract_username(None) is None

    def test_picks_suspicious_login_over_others(self):
        events = [
            {"event_type": "login_failure", "target_entity": {"username": "bob"}},
            {"event_type": "login_success", "target_entity": {"username": "carol"}},
            {"event_type": "suspicious_login", "target_entity": {"username": "alice"}},
        ]
        assert CorrelationEngine._extract_username(events) == "alice"

    def test_login_success_beats_credential_stuffing(self):
        events = [
            {"event_type": "credential_stuffing", "target_entity": {"username": "bob"}},
            {"event_type": "login_success", "target_entity": {"username": "carol"}},
        ]
        assert CorrelationEngine._extract_username(events) == "carol"

    def test_credential_stuffing_beats_login_failure(self):
        events = [
            {"event_type": "login_failure", "target_entity": {"username": "bob"}},
            {"event_type": "credential_stuffing", "target_entity": {"username": "dan"}},
        ]
        assert CorrelationEngine._extract_username(events) == "dan"

    def test_login_failure_used_when_only_signal(self):
        events = [
            {"event_type": "sql_injection", "target_entity": {"username": "ignored"}},
            {"event_type": "login_failure", "target_entity": {"username": "eve"}},
        ]
        assert CorrelationEngine._extract_username(events) == "eve"

    def test_falls_back_to_any_username(self):
        events = [
            {"event_type": "sql_injection", "target_entity": {"username": "frank"}},
        ]
        assert CorrelationEngine._extract_username(events) == "frank"

    def test_skips_non_dict_entries(self):
        events = [None, "garbage", 42,
                  {"event_type": "login_success", "target_entity": {"username": "gina"}}]
        assert CorrelationEngine._extract_username(events) == "gina"

    def test_returns_none_when_no_username_anywhere(self):
        events = [
            {"event_type": "login_success", "target_entity": {}},
            {"event_type": "sql_injection"},
        ]
        assert CorrelationEngine._extract_username(events) is None


# ── rule_account_pivot ──────────────────────────────────────────────────────

class TestAccountPivot:

    def test_triggers_on_login_then_anomalous_api(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=30)
        api = _api_event(ip="10.0.0.5", etype="sql_injection", offset_seconds=0)

        result = eng.rule_account_pivot(api, [login])

        assert result == {"_called": True}
        eng.create_incident.assert_called_once()
        args, _ = eng.create_incident.call_args
        # Positional: type, title, description, severity, confidence, source_ip, ...
        assert args[0] == "account_pivot"
        assert "alice" in args[1]
        assert args[3] == "critical"
        assert args[5] == "10.0.0.5"
        # MITRE list at index 8
        assert "T1078" in args[8] and "T1021" in args[8]
        # Extra dict (last positional) carries explicit username.
        assert args[-1] == {"target_username": "alice"}

    def test_ignored_when_api_event_type_not_anomalous(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=10)
        api = _api_event(ip="10.0.0.5", etype="normal_request", offset_seconds=0)

        assert eng.rule_account_pivot(api, [login]) is None
        eng.create_incident.assert_not_called()

    def test_ignored_when_layer_not_api(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=10)
        not_api = dict(_api_event(ip="10.0.0.5"))
        not_api["source_layer"] = "auth"

        assert eng.rule_account_pivot(not_api, [login]) is None
        eng.create_incident.assert_not_called()

    def test_ignored_when_no_recent_login(self):
        eng = _engine()
        api = _api_event(ip="10.0.0.5", etype="data_export", offset_seconds=0)
        assert eng.rule_account_pivot(api, []) is None
        eng.create_incident.assert_not_called()

    def test_ignored_when_login_outside_5min_window(self):
        eng = _engine()
        # Login 6 minutes earlier — outside the window.
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=360)
        api = _api_event(ip="10.0.0.5", etype="path_traversal", offset_seconds=0)

        assert eng.rule_account_pivot(api, [login]) is None
        eng.create_incident.assert_not_called()

    def test_ignored_when_login_from_different_ip(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.7", username="alice", offset_seconds=10)
        api = _api_event(ip="10.0.0.5", etype="sql_injection", offset_seconds=0)

        assert eng.rule_account_pivot(api, [login]) is None
        eng.create_incident.assert_not_called()

    def test_ignored_when_source_ip_missing(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=10)
        api = _api_event(ip="10.0.0.5", etype="sql_injection")
        api["source_entity"] = {}

        assert eng.rule_account_pivot(api, [login]) is None
        eng.create_incident.assert_not_called()

    def test_cooldown_suppresses_second_trigger(self):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=10)
        api1 = _api_event(ip="10.0.0.5", etype="sql_injection", offset_seconds=1)
        api2 = _api_event(ip="10.0.0.5", etype="rate_abuse", offset_seconds=0)

        first = eng.rule_account_pivot(api1, [login])
        second = eng.rule_account_pivot(api2, [login])

        assert first == {"_called": True}
        assert second is None
        assert eng.create_incident.call_count == 1

    @pytest.mark.parametrize("etype", ["sql_injection", "path_traversal",
                                       "rate_abuse", "data_export"])
    def test_each_anomalous_api_type_triggers(self, etype):
        eng = _engine()
        login = _login_event(ip="10.0.0.5", username="alice", offset_seconds=5)
        api = _api_event(ip="10.0.0.5", etype=etype, offset_seconds=0)

        result = eng.rule_account_pivot(api, [login])
        assert result == {"_called": True}
