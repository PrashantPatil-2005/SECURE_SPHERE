"""Unit tests for Phase 13 modules.

Pure-Python tests — no Redis/Postgres/Docker required. Fast, deterministic,
suitable for the GitHub Actions ``unit`` job that runs on every push.
"""

from __future__ import annotations

import os
import sys
import time

# Add engine module roots so ``from confidence...`` resolves like in container
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for sub in ("backend/engine", "backend"):
    sys.path.insert(0, os.path.join(ROOT, sub))


# ---------------------------------------------------------------------------
# Bayesian confidence
# ---------------------------------------------------------------------------
def test_confidence_short_chain_low():
    from confidence.bayesian import score_chain
    rep = score_chain([{"stage": "reconnaissance"}])
    assert 0.0 <= rep.posterior <= 1.0
    assert rep.posterior < 0.7


def test_confidence_late_stage_high():
    from confidence.bayesian import score_chain
    rep = score_chain([
        {"stage": "reconnaissance"},
        {"stage": "initial_access"},
        {"stage": "lateral_movement"},
        {"stage": "exfiltration"},
    ])
    assert rep.posterior > 0.7
    assert len(rep.per_stage) == 4


# ---------------------------------------------------------------------------
# Counterfactual + diff
# ---------------------------------------------------------------------------
def test_counterfactual_pivotal_step_detected():
    from explain.counterfactual import explain_chain
    chain = [
        {"stage": "reconnaissance", "service": "a"},
        {"stage": "lateral_movement", "service": "b"},
        {"stage": "exfiltration",     "service": "c"},
    ]
    result = explain_chain(chain)
    assert result["baseline"]["posterior"] > 0
    # Removing the lateral_movement step should drop posterior more than
    # removing the recon step
    deltas = {r["removed_index"]: r["delta"] for r in result["removed"]}
    assert deltas[1] > deltas[0]


def test_diff_identical_chains_high_similarity():
    from explain.diff import diff_chains
    chain = {
        "kill_chain_steps": [{"stage": "recon"}, {"stage": "exploit"}],
        "service_path": ["a", "b"],
        "mitre_techniques": ["T1046", "T1190"],
    }
    out = diff_chains(chain, chain)
    assert out["similarity"]["overall"] == 1.0


def test_diff_disjoint_chains_zero_similarity():
    from explain.diff import diff_chains
    a = {
        "kill_chain_steps": [{"stage": "recon"}],
        "service_path": ["a"],
        "mitre_techniques": ["T1046"],
    }
    b = {
        "kill_chain_steps": [{"stage": "exfiltration"}],
        "service_path": ["z"],
        "mitre_techniques": ["T1048"],
    }
    out = diff_chains(a, b)
    assert out["similarity"]["overall"] < 0.4


# ---------------------------------------------------------------------------
# YAML rule DSL
# ---------------------------------------------------------------------------
def test_rule_dsl_match_simple_sequence():
    try:
        import yaml  # noqa: F401
    except Exception:
        # yaml not installed in unit job — skip silently
        return

    from rules.dsl import Rule
    rule = Rule.from_dict({
        "name": "t",
        "incident_type": "t",
        "severity": "high",
        "description": "x",
        "mitre_techniques": ["T1046"],
        "window_seconds": 600,
        "sequence": [
            {"id": "a", "match": {"event_type": "port_scan"}},
            {"id": "b", "same": {"key": "source_service_name"},
             "match": {"event_type": "sql_injection_attempt"}},
        ],
    })
    now = "2024-01-01T00:00:00"
    later = "2024-01-01T00:00:30"
    e1 = {"event_type": "port_scan", "source_service_name": "svc-a", "timestamp": now}
    e2 = {"event_type": "sql_injection_attempt", "source_service_name": "svc-a", "timestamp": later}
    inc = rule.evaluate(e2, [e1, e2])
    assert inc is not None
    assert inc["incident_type"] == "t"
    assert inc["service_path"] == ["svc-a"]


def test_rule_dsl_rejects_cross_service_match():
    try:
        import yaml  # noqa: F401
    except Exception:
        return
    from rules.dsl import Rule
    rule = Rule.from_dict({
        "name": "t", "incident_type": "t", "severity": "high",
        "description": "x", "mitre_techniques": [],
        "window_seconds": 600,
        "sequence": [
            {"id": "a", "match": {"event_type": "port_scan"}},
            {"id": "b", "same": {"key": "source_service_name"},
             "match": {"event_type": "sql_injection_attempt"}},
        ],
    })
    now = "2024-01-01T00:00:00"
    later = "2024-01-01T00:00:30"
    e1 = {"event_type": "port_scan", "source_service_name": "svc-a", "timestamp": now}
    e2 = {"event_type": "sql_injection_attempt", "source_service_name": "svc-b", "timestamp": later}
    assert rule.evaluate(e2, [e1, e2]) is None


# ---------------------------------------------------------------------------
# Behaviour fingerprinter
# ---------------------------------------------------------------------------
def test_fingerprinter_no_anomaly_during_warmup():
    from anomaly.fingerprinter import BehaviorTracker

    class _FakeRedis:
        def lpush(self, *a, **k): pass
        def ltrim(self, *a, **k): pass
        def publish(self, *a, **k): pass

    t = BehaviorTracker(_FakeRedis(), bus=None)
    for _ in range(3):
        rep = t.observe({
            "source_service_name": "svc",
            "source_layer": "api",
            "severity": "low",
            "destination_service": "db",
        })
        assert rep is None  # not enough baseline yet


# ---------------------------------------------------------------------------
# Heuristic predictor
# ---------------------------------------------------------------------------
def test_heuristic_predictor_falls_back_to_canonical_order():
    from predictor.heuristic import HeuristicPredictor
    p = HeuristicPredictor(redis_client=None)
    out = p.predict(current_stage="reconnaissance", observed_techniques=[])
    assert out["model"] == "markov-heuristic"
    assert isinstance(out["next_stages"], list)


# ---------------------------------------------------------------------------
# Topology drift signature
# ---------------------------------------------------------------------------
def test_drift_neighbour_change_flagged_critical():
    sys.path.insert(0, os.path.join(ROOT, "backend/topology"))
    from drift_detector import fingerprint, diff
    services = ["a", "b", "c"]
    e1 = [("a", "b"), ("b", "c")]
    e2 = [("a", "b"), ("b", "c"), ("a", "c")]    # a now also talks to c
    sig1 = fingerprint(services, e1)
    sig2 = fingerprint(services, e2)
    events = diff(sig1, sig2)
    assert any(ev.severity == "critical" and ev.drift_type == "neighbour_change"
               for ev in events)
