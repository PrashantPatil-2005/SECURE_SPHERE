"""
test_severity.py — Unit tests for the canonical severity resolver.

Covers all four buckets, the kill-chain floor, and the critical-technique
override. Pure function, no DB, runs in well under a second.
"""
from __future__ import annotations

import os
import sys
import pytest

# Make backend/engine importable from tests/.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend", "engine"))

from severity import (  # noqa: E402
    resolve_incident_severity,
    floor_severity,
    CRITICAL_TECHNIQUES,
    SEVERITY_ORDER,
)


# ── bucket coverage ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "score, expected",
    [
        (0,     "low"),
        (15,    "low"),
        (30,    "low"),       # boundary — still in Normal bucket
        (31,    "medium"),
        (50,    "medium"),
        (70,    "medium"),    # boundary — still in Suspicious bucket
        (71,    "high"),
        (120,   "high"),
        (150,   "high"),      # boundary — still in Threatening bucket
        (151,   "critical"),
        (500,   "critical"),
    ],
)
def test_score_only_buckets(score, expected):
    assert resolve_incident_severity(risk_score=score, step_count=0, technique_ids=[]) == expected


# ── kill-chain floor ────────────────────────────────────────────────────────

def test_kill_chain_floors_low_to_high():
    assert resolve_incident_severity(risk_score=0, step_count=2, technique_ids=[]) == "high"


def test_kill_chain_floors_medium_to_high():
    assert resolve_incident_severity(risk_score=50, step_count=3, technique_ids=[]) == "high"


def test_kill_chain_does_not_downgrade_critical_score():
    assert resolve_incident_severity(risk_score=200, step_count=5, technique_ids=[]) == "critical"


def test_single_step_does_not_floor():
    assert resolve_incident_severity(risk_score=10, step_count=1, technique_ids=[]) == "low"


# ── critical-technique override ─────────────────────────────────────────────

@pytest.mark.parametrize("tid", sorted(CRITICAL_TECHNIQUES))
def test_critical_technique_forces_critical(tid):
    assert resolve_incident_severity(risk_score=0, step_count=0, technique_ids=[tid]) == "critical"


def test_non_critical_technique_does_not_force():
    assert resolve_incident_severity(risk_score=10, step_count=0, technique_ids=["T1046"]) == "low"


# ── input hygiene ───────────────────────────────────────────────────────────

def test_handles_negative_score():
    assert resolve_incident_severity(risk_score=-50, step_count=0, technique_ids=[]) == "low"


def test_handles_none_inputs():
    assert resolve_incident_severity(risk_score=None, step_count=None, technique_ids=None) == "low"


# ── floor_severity helper ───────────────────────────────────────────────────

def test_floor_severity_keeps_higher_existing():
    assert floor_severity("critical", "high") == "critical"


def test_floor_severity_lifts_lower_existing():
    assert floor_severity("low", "high") == "high"


def test_floor_severity_handles_missing_current():
    assert floor_severity(None, "high") == "high"


def test_severity_ordering_consistent():
    assert SEVERITY_ORDER["low"] < SEVERITY_ORDER["medium"] < SEVERITY_ORDER["high"] < SEVERITY_ORDER["critical"]
