"""
Tests for CampaignAggregator core contract:
  - 3 incidents from same source_ip → 1 campaign (the bug we're fixing)
  - distinct attackers → distinct campaigns
  - duplicate ingest → idempotent
  - severity is monotonic (max)
  - new kill-chain stage → "escalated" change_kind
  - idle timeout closes the campaign

Heavy DB / Redis dependencies are stubbed with FakeRedis + an in-memory
psycopg2 monkeypatch so the contract can be verified without spinning up
a stack.

Run:  pytest backend/engine/correlation/tests/test_campaign_aggregator.py
"""

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from correlation.campaign_aggregator import (  # noqa: E402
    CampaignAggregator,
    CAMPAIGN_REDIS_PREFIX,
    CAMPAIGN_INDEX_KEY,
    _utcnow,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeRedis:
    def __init__(self):
        self.store: Dict[str, Any] = {}
        self.sets: Dict[str, set] = {}

    def get(self, k):
        v = self.store.get(k)
        if isinstance(v, dict) and v.get("__expires") and _utcnow() > v["__expires"]:
            del self.store[k]
            return None
        return v["v"] if isinstance(v, dict) and "v" in v else v

    def setex(self, k, ttl, v):
        self.store[k] = {"v": v, "__expires": _utcnow() + timedelta(seconds=ttl)}

    def delete(self, k):
        self.store.pop(k, None)

    def sadd(self, k, m):
        self.sets.setdefault(k, set()).add(m)

    def srem(self, k, m):
        self.sets.get(k, set()).discard(m)

    def smembers(self, k):
        return self.sets.get(k, set())


class FakePGCursor:
    def __init__(self, store, cursor_factory=None):
        self.store = store
        self.cursor_factory = cursor_factory
        self._result: List[Any] = []

    def __enter__(self): return self
    def __exit__(self, *a): pass

    def execute(self, sql, params=()):
        sql_l = " ".join(sql.lower().split())

        # Schema DDL — accept silently
        if any(sql_l.startswith(p) for p in (
            "create table", "create unique index", "create index",
            "alter table",
        )):
            self._result = []
            return

        # INSERT INTO campaigns
        if sql_l.startswith("insert into campaigns"):
            row = {
                "campaign_id": params[0],   "actor_id": params[1],
                "source_ip":   params[2],   "target_usernames": list(params[3] or []),
                "incident_ids": list(params[4] or []), "incident_count": params[5],
                "service_path": list(params[6] or []),
                "kill_chain_steps": json.loads(params[7]) if isinstance(params[7], str) else params[7],
                "mitre_techniques": list(params[8] or []),
                "layers_involved":  list(params[9] or []),
                "stages_seen":      list(params[10] or []),
                "severity":         params[11], "max_confidence": params[12],
                "first_event_at":   params[13], "last_event_at":  params[14],
                "status":           params[15],
                "discord_message_id": params[16], "discord_channel_id": params[17],
                "created_at":       params[18], "updated_at":     params[19],
                "closed_reason": None, "closed_at": None,
            }
            for ex in self.store["campaigns"]:
                if ex["actor_id"] == row["actor_id"] and ex["status"] == "active":
                    import psycopg2.errors
                    raise psycopg2.errors.UniqueViolation("duplicate active campaign")
            self.store["campaigns"].append(row)
            self._result = []
            return

        # UPDATE campaigns SET ... WHERE campaign_id = %s
        if sql_l.startswith("update campaigns set"):
            cid = params[-1]
            if "status = 'closed'" in sql_l:
                # close path: params=(reason, campaign_id)
                reason = params[0]
                for r in self.store["campaigns"]:
                    if r["campaign_id"] == cid:
                        r["status"] = "closed"
                        r["closed_reason"] = reason
                        r["closed_at"] = _utcnow()
                self._result = []
                return
            if "discord_message_id" in sql_l and "set discord_message_id" in sql_l:
                msg_id, chan_id, cid2 = params
                for r in self.store["campaigns"]:
                    if r["campaign_id"] == cid2:
                        r["discord_message_id"] = msg_id
                        r["discord_channel_id"] = chan_id
                self._result = []
                return
            # generic incremental update
            (incident_ids, incident_count, service_path, kc_steps,
             mitre, layers, stages, severity, conf, last_evt,
             usernames, updated_at, _cid) = params
            for r in self.store["campaigns"]:
                if r["campaign_id"] == _cid:
                    r["incident_ids"]     = list(incident_ids)
                    r["incident_count"]   = incident_count
                    r["service_path"]     = list(service_path)
                    r["kill_chain_steps"] = json.loads(kc_steps) if isinstance(kc_steps, str) else kc_steps
                    r["mitre_techniques"] = list(mitre)
                    r["layers_involved"]  = list(layers)
                    r["stages_seen"]      = list(stages)
                    r["severity"]         = severity
                    r["max_confidence"]   = conf
                    r["last_event_at"]    = last_evt
                    r["target_usernames"] = list(usernames)
                    r["updated_at"]       = updated_at
            self._result = []
            return

        # SELECT ... FROM campaigns WHERE actor_id = %s AND status='active'
        if "from campaigns" in sql_l and "where actor_id" in sql_l:
            actor = params[0]
            self._result = [
                r for r in self.store["campaigns"]
                if r["actor_id"] == actor and r["status"] == "active"
            ]
            return

        if "select actor_id from campaigns" in sql_l:
            cid = params[0]
            self._result = [
                (r["actor_id"],) for r in self.store["campaigns"]
                if r["campaign_id"] == cid
            ]
            return

        if "select actor_id from campaigns" in sql_l and "last_event_at <" in sql_l:
            self._result = []
            return

        # Backlink updates — stubbed (no incident table in fake)
        if sql_l.startswith("update correlated_incidents") or \
           sql_l.startswith("update kill_chains"):
            self._result = []
            return

        self._result = []

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return list(self._result)


class FakePGConn:
    def __init__(self, store):
        self.store = store

    def cursor(self, cursor_factory=None):
        return FakePGCursor(self.store, cursor_factory)

    def __enter__(self): return self
    def __exit__(self, *a): pass

    def close(self): pass


@pytest.fixture
def store():
    return {"campaigns": []}


@pytest.fixture
def aggregator(store):
    fake_redis = FakeRedis()
    with patch("correlation.campaign_aggregator.psycopg2.connect",
               side_effect=lambda **_: FakePGConn(store)):
        agg = CampaignAggregator(fake_redis, {})
        yield agg


def mk_incident(*, ip="10.0.0.5", svc="auth-service", severity="high",
                tactic="Reconnaissance", techniques=None,
                username=None, ts=None):
    techniques = techniques or ["T1595"]
    ts = ts or _utcnow().isoformat()
    return {
        "incident_id":      str(uuid.uuid4()),
        "incident_type":    "test_rule",
        "source_ip":        ip,
        "target_username":  username,
        "severity":         severity,
        "confidence":       0.8,
        "tactic":           tactic,
        "service_path":     [svc],
        "mitre_techniques": techniques,
        "layers_involved":  ["api"],
        "kill_chain_steps": [{
            "service_name": svc,
            "event_id":     str(uuid.uuid4()),
            "timestamp":    ts,
            "tactic":       tactic,
        }],
        "first_event_at":   ts,
        "timestamp":        ts,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_three_incidents_one_campaign(aggregator):
    """The headline bug: 3 sequential incidents from same IP → 1 campaign."""
    inc1 = mk_incident(svc="auth-service", tactic="Reconnaissance",
                       techniques=["T1595"])
    inc2 = mk_incident(svc="api-gateway",  tactic="Initial Access",
                       techniques=["T1190"])
    inc3 = mk_incident(svc="database",     tactic="Exfiltration",
                       techniques=["T1530"])

    c1, k1 = aggregator.ingest(inc1)
    c2, k2 = aggregator.ingest(inc2)
    c3, k3 = aggregator.ingest(inc3)

    assert k1 == "created"
    assert k2 == "escalated"   # new kill-chain stage entered
    assert k3 == "escalated"
    assert c1["campaign_id"] == c2["campaign_id"] == c3["campaign_id"]
    assert c3["incident_count"] == 3
    assert c3["service_path"] == ["auth-service", "api-gateway", "database"]
    assert set(c3["mitre_techniques"]) == {"T1595", "T1190", "T1530"}
    assert "reconnaissance" in c3["stages_seen"]
    assert "actions_on_objectives" in c3["stages_seen"]


def test_different_attackers_different_campaigns(aggregator):
    a, _ = aggregator.ingest(mk_incident(ip="10.0.0.5"))
    b, _ = aggregator.ingest(mk_incident(ip="10.0.0.6"))
    assert a["campaign_id"] != b["campaign_id"]
    assert a["actor_id"] == "ip:10.0.0.5"
    assert b["actor_id"] == "ip:10.0.0.6"


def test_duplicate_incident_ignored(aggregator):
    inc = mk_incident()
    aggregator.ingest(inc)
    c, k = aggregator.ingest(inc)
    assert k == "duplicate"
    assert c["incident_count"] == 1


def test_severity_is_monotonic(aggregator):
    aggregator.ingest(mk_incident(severity="high"))
    c, k = aggregator.ingest(mk_incident(severity="medium"))
    assert c["severity"] == "high"
    assert k == "extended"   # no escalation, just appended


def test_severity_escalation(aggregator):
    aggregator.ingest(mk_incident(severity="medium",
                                  tactic="Reconnaissance"))
    c, k = aggregator.ingest(mk_incident(severity="critical",
                                         tactic="Reconnaissance"))
    assert c["severity"] == "critical"
    assert k == "escalated"


def test_idle_timeout_splits_campaign(aggregator):
    a, _ = aggregator.ingest(mk_incident())
    # Force idle by rewinding the campaign's last_event_at
    a["last_event_at"] = _utcnow() - timedelta(hours=2)
    aggregator._cache(a)
    aggregator._persist_update(a)

    b, k = aggregator.ingest(mk_incident())
    assert k == "created"
    assert a["campaign_id"] != b["campaign_id"]


def test_user_fallback_when_no_ip(aggregator):
    inc = mk_incident(ip="0.0.0.0", username="admin")
    c, k = aggregator.ingest(inc)
    assert k == "created"
    assert c["actor_id"] == "user:admin"


def test_attacker_with_no_identity_skipped(aggregator):
    inc = mk_incident(ip="0.0.0.0")
    inc["target_username"] = None
    c, k = aggregator.ingest(inc)
    assert k == "duplicate"
    assert c == {}


def test_service_path_dedupes_consecutive(aggregator):
    a, _ = aggregator.ingest(mk_incident(svc="auth"))
    b, _ = aggregator.ingest(mk_incident(svc="auth"))     # same → no append
    c, _ = aggregator.ingest(mk_incident(svc="api"))
    assert c["service_path"] == ["auth", "api"]
