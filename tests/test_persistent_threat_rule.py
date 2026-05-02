"""Unit test for the relaxed persistent_threat (stealth) rule.

Asserts that ``rule_persistent_threat`` fires exactly once when 3 events
from the same source IP arrive with 30s gaps — the canonical "low and
slow" pattern that the previous threshold (10 events / 5min / 3 distinct
types) silently dropped.

Tested via a stub host class so we don't need Redis/Postgres/Docker.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
for sub in ("backend/engine/correlation", "backend/engine", "backend"):
    sys.path.insert(0, os.path.join(ROOT, sub))


def _make_event(ip: str, ts: datetime, event_type: str = "sql_injection"):
    return {
        "event_id": f"e-{ts.timestamp()}",
        "timestamp": ts.isoformat(),
        "event_type": event_type,
        "source_entity": {"ip": ip},
        "source_layer": "api",
        "severity": {"level": "low"},
    }


class _Host:
    """Minimal stand-in for CorrelationEngine that satisfies the rule's
    contract: cooldown helpers + a create_incident sink."""

    def __init__(self):
        self.incident_cooldowns: dict = {}
        self.cooldown_duration = timedelta(minutes=5)
        self.created: list = []

    def _check_cooldown(self, rule, key):
        ck = f"{rule}:{key}"
        if ck in self.incident_cooldowns:
            return datetime.now() < self.incident_cooldowns[ck] + self.cooldown_duration
        return False

    def _set_cooldown(self, rule, key):
        self.incident_cooldowns[f"{rule}:{key}"] = datetime.now()

    def create_incident(self, *args, **kwargs):
        inc = {"args": args, "kwargs": kwargs}
        self.created.append(inc)
        return inc


def _bound_rule():
    """Import the unbound method so the test isn't gated on full engine init."""
    # Import inside the function so sys.path tweaks above are in effect.
    from correlation_engine import CorrelationEngine
    return CorrelationEngine.rule_persistent_threat


def test_persistent_threat_fires_on_three_stealth_events_30s_apart():
    rule = _bound_rule()
    host = _Host()

    base = datetime(2026, 5, 2, 12, 0, 0)
    events = [_make_event("10.0.0.7", base + timedelta(seconds=30 * i)) for i in range(3)]

    fired = 0
    buffer = []
    for ev in events:
        buffer.append(ev)
        if rule(host, ev, buffer):
            fired += 1

    assert fired == 1, f"expected exactly 1 fire, got {fired}"
    assert host.created and host.created[0]["args"][0] == "persistent_threat"


def test_persistent_threat_does_not_fire_on_single_event():
    rule = _bound_rule()
    host = _Host()
    ev = _make_event("10.0.0.8", datetime(2026, 5, 2, 12, 0, 0))
    assert rule(host, ev, [ev]) is None
    assert host.created == []


def test_persistent_threat_respects_cooldown():
    rule = _bound_rule()
    host = _Host()
    base = datetime(2026, 5, 2, 12, 0, 0)
    evs = [_make_event("10.0.0.9", base + timedelta(seconds=30 * i)) for i in range(4)]
    fires = 0
    buf = []
    for e in evs:
        buf.append(e)
        if rule(host, e, buf):
            fires += 1
    assert fires == 1
