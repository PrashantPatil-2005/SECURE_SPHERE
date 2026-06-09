"""Unit tests for service-centric correlation key resolution."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend", "engine"))

from shared.event_schema import (  # noqa: E402
    normalize_event,
    resolve_correlation_key,
    filter_buffer_by_actor,
    events_same_actor,
)


def test_correlation_key_service_pair():
    ev = {
        "source_service_name": "api-server",
        "destination_service_name": "auth-service",
        "trace_id": "abc",
    }
    key = resolve_correlation_key(ev)
    assert key == "svc:api-server→auth-service:abc"


def test_correlation_key_ip_destination_fallback():
    ev = {
        "source_entity": {"ip": "10.0.0.5"},
        "destination_service_name": "api-server",
    }
    key = resolve_correlation_key(normalize_event(ev))
    assert key == "ip:10.0.0.5→api-server"


def test_correlation_key_workload():
    ev = {"workload_id": "cid-123", "source_entity": {"ip": "10.0.0.1"}}
    key = resolve_correlation_key(ev)
    assert key == "wl:cid-123"


def test_churn_resilience_same_service_different_ip():
    ev1 = normalize_event({
        "source_service_name": "attacker-pod",
        "destination_service_name": "auth-service",
        "source_entity": {"ip": "10.0.0.99"},
        "timestamp": "2026-01-01T00:00:00Z",
    })
    ev2 = normalize_event({
        "source_service_name": "attacker-pod",
        "destination_service_name": "auth-service",
        "source_entity": {"ip": "10.0.0.55"},
        "timestamp": "2026-01-01T00:01:00Z",
    })
    assert events_same_actor(ev1, ev2, mode="service")
    assert not events_same_actor(ev1, ev2, mode="legacy")


def test_filter_buffer_by_actor():
    ev = normalize_event({
        "source_service_name": "attacker-pod",
        "destination_service_name": "api-server",
        "source_entity": {"ip": "10.0.0.99"},
    })
    other = normalize_event({
        "source_service_name": "other",
        "destination_service_name": "api-server",
        "source_entity": {"ip": "10.0.0.1"},
    })
    buf = [ev, other]
    matched = filter_buffer_by_actor(buf, ev, mode="service")
    assert len(matched) == 1
    assert matched[0]["source_service_name"] == "attacker-pod"


def test_campaign_actor_service_priority():
    sys.path.insert(0, os.path.join(ROOT, "backend", "engine", "correlation"))
    from campaign_aggregator import CampaignAggregator  # noqa: E402

    actor_id, actor_type = CampaignAggregator.resolve_actor({
        "source_service_name": "attacker-pod",
        "source_ip": "10.0.0.99",
    })
    assert actor_id == "service:attacker-pod"
    assert actor_type == "service"
