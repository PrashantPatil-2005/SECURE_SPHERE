"""
test_scenarios.py — Regression tests for the attacker/ scenario package.

Runs offline: every outbound HTTP call is monkey-patched. The tests verify
stage ordering, structural correctness, expected incident types per scenario,
traffic-generator plumbing, and Makefile target presence.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

# Ensure repo root is on sys.path when pytest runs from subfolders
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from attacker import common, scenario_a, scenario_b, scenario_c, traffic_generator  # noqa: E402


# ── Fake HTTP layer ─────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code: int = 200, json_body: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text or json.dumps(self._json)

    def json(self) -> dict:
        return self._json


def _incidents_payload(types: list[str]) -> dict:
    return {
        "data": {
            "incidents": [
                {
                    "incident_id":        f"inc-{i}",
                    "incident_type":      t,
                    "severity":           "high",
                    "title":              f"Test {t}",
                    "mitre_techniques":   [],
                }
                for i, t in enumerate(types)
            ]
        }
    }


@pytest.fixture
def captured_requests():
    """Record every requests.request call and return a list of (method, url)."""
    captured: list[tuple[str, str]] = []

    def _fake_request(method, url, *args, **kwargs):
        captured.append((method.upper(), url))
        if "/auth/login" in url:
            # Only 'john:password123' succeeds; everything else fails
            body = kwargs.get("json") or {}
            ok = body.get("username") == "john" and body.get("password") == "password123"
            return _FakeResponse(
                status_code=200 if ok else 401,
                json_body={"status": "success" if ok else "fail"},
                text="success" if ok else "locked" if "admin" in (body.get("username", "")) else "fail",
            )
        if "/api/incidents" in url:
            # Will be overridden per-test via the monkeypatch on requests.get
            return _FakeResponse(200, _incidents_payload([]))
        return _FakeResponse(200, {"ok": True}, "ok")

    def _fake_get(url, *args, **kwargs):
        captured.append(("GET", url))
        return _FakeResponse(200, {"ok": True}, "ok")

    def _fake_post(url, *args, **kwargs):
        captured.append(("POST", url))
        return _FakeResponse(200, {"ok": True}, "ok")

    with mock.patch("attacker.common.requests.request", side_effect=_fake_request), \
         mock.patch("attacker.common.requests.get",     side_effect=_fake_get),     \
         mock.patch("attacker.common.requests.post",    side_effect=_fake_post),    \
         mock.patch("attacker.traffic_generator.req",   side_effect=lambda *a, **kw: _FakeResponse()), \
         mock.patch("socket.gethostbyname", return_value="127.0.0.1"), \
         mock.patch("socket.socket") as fake_sock:
        fake_sock.return_value.connect_ex.return_value = 1  # every port closed
        yield captured


def _patch_verification(incident_types: list[str]):
    """Replace /api/incidents fetch inside verify_detections with a fixed payload."""
    return mock.patch(
        "attacker.common.requests.get",
        return_value=_FakeResponse(200, _incidents_payload(incident_types)),
    )


# ── Scenario structural tests ───────────────────────────────────────────────

class TestScenarioA:
    EXPECTED = scenario_a.EXPECTED_INCIDENTS

    def test_expected_incidents(self):
        assert "brute_force_attempt" in self.EXPECTED
        assert "credential_compromise" in self.EXPECTED
        assert "data_exfiltration_risk" in self.EXPECTED

    def test_runs_four_stages(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            summary = scenario_a.run(speed="fast", noise=False)
        stage_names = [s["name"] for s in summary["stages"]]
        assert stage_names == [
            "auth_recon",
            "brute_force",
            "credential_stuffing",
            "data_exfiltration",
        ]

    def test_all_expected_incidents_matched(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            summary = scenario_a.run(speed="fast", noise=False)
        assert set(summary["matched"]) == set(self.EXPECTED)
        assert summary["match_ratio"] == 1.0

    def test_exfil_stage_hits_sensitive_endpoints(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            scenario_a.run(speed="fast", noise=False)
        urls = " ".join(u for _, u in captured_requests)
        assert "/api/admin/config" in urls
        assert "/api/admin/users/export" in urls


class TestScenarioB:
    EXPECTED = scenario_b.EXPECTED_INCIDENTS

    def test_expected_incidents(self):
        assert "recon_to_exploitation" in self.EXPECTED
        assert "critical_exploit_attempt" in self.EXPECTED

    def test_runs_three_stages(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            summary = scenario_b.run(speed="fast", noise=False)
        stage_names = [s["name"] for s in summary["stages"]]
        assert stage_names == [
            "reconnaissance",
            "exploitation",
            "privilege_escalation",
        ]

    def test_sqli_and_traversal_payloads_sent(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            scenario_b.run(speed="fast", noise=False)
        urls = " ".join(u for _, u in captured_requests)
        assert "/api/products/search" in urls
        assert "/api/files" in urls


class TestScenarioC:
    EXPECTED = scenario_c.EXPECTED_INCIDENTS

    def test_expected_incidents(self):
        assert "full_kill_chain" in self.EXPECTED
        assert "distributed_credential_attack" in self.EXPECTED

    def test_runs_four_hops(self, captured_requests, monkeypatch):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
        with _patch_verification(self.EXPECTED):
            summary = scenario_c.run(speed="fast", noise=False)
        stage_names = [s["name"] for s in summary["stages"]]
        services   = [s["service"] for s in summary["stages"]]
        assert stage_names == [
            "web_app_foothold",
            "api_credential_harvest",
            "auth_credential_stuffing",
            "data_exfiltration",
        ]
        assert set(services) == {"web-app", "api-server", "auth-service", "data-store"}
        assert len(services) == 4

    def test_spoofed_ips_used(self):
        assert len(scenario_c.SPOOFED_IPS) >= 3


# ── Traffic generator tests ─────────────────────────────────────────────────

class TestTrafficGenerator:
    def test_one_cycle_issues_request(self, captured_requests):
        with mock.patch("attacker.traffic_generator.req") as m:
            m.return_value = _FakeResponse()
            traffic_generator._one_cycle()
            assert m.called

    def test_run_respects_duration(self, monkeypatch):
        # Speed up by patching sleep + req
        monkeypatch.setattr("attacker.traffic_generator.time.sleep", lambda *_: None)
        with mock.patch("attacker.traffic_generator.req", return_value=_FakeResponse()):
            count = traffic_generator.run(duration=0.01, rate=100, verbose=False)
        assert count > 0

    def test_background_context_manager_stops(self, monkeypatch):
        monkeypatch.setattr("attacker.traffic_generator.time.sleep", lambda *_: None)
        with mock.patch("attacker.traffic_generator.req", return_value=_FakeResponse()):
            before = threading.active_count()
            with traffic_generator.background(rate=50, verbose=False):
                mid = threading.active_count()
                assert mid >= before + 1
            time.sleep(0.05)
        # Thread should have exited
        assert threading.active_count() <= mid


# ── Makefile integration ────────────────────────────────────────────────────

class TestMakefileTargets:
    @pytest.fixture(scope="class")
    def makefile_text(self) -> str:
        return (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

    @pytest.mark.parametrize("target", [
        "attack-a:", "attack-b:", "attack-c:",
        "attacker-a:", "attacker-b:", "attacker-c:",
        "attacker-noise:", "test-scenarios:",
    ])
    def test_target_defined(self, makefile_text, target):
        assert target in makefile_text, f"Makefile missing target {target}"

    def test_attacker_targets_invoke_package(self, makefile_text):
        assert "python -m attacker.scenario_a" in makefile_text
        assert "python -m attacker.scenario_b" in makefile_text
        assert "python -m attacker.scenario_c" in makefile_text


# ── Common helpers ──────────────────────────────────────────────────────────

class TestCommon:
    def test_detection_result_match_ratio(self):
        r = common.DetectionResult(scenario="X", start_time="t")
        r.expected = ["a", "b", "c"]
        r.detections = [{"type": "a"}, {"type": "c"}]
        summary = r.summary()
        assert set(summary["matched"]) == {"a", "c"}
        assert summary["match_ratio"] == pytest.approx(2 / 3)

    def test_speed_map_contains_all_modes(self):
        assert set(common.SPEED_MAP.keys()) == {"fast", "normal", "demo", "slow"}
