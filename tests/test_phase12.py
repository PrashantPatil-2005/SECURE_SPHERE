"""Phase 12 — topology checkpoint integration test.

Requires the full stack to be running (same assumption as tests/test_smoke.py).
"""
import os
import requests

BASE = os.getenv("SECURISPHERE_API_URL", "http://localhost:8000")

EXPECTED_IDS = {
    "collector-up",
    "graph-endpoint",
    "edge-endpoint",
    "history-endpoint",
    "enrichment",
    "d3-overlay",
    "kill-chain-anim",
}


def test_topology_checks_endpoint():
    resp = requests.get(f"{BASE}/api/topology-checks", timeout=10)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    for field in ("title", "subtitle", "status", "updated_at", "checks"):
        assert field in data, f"missing field: {field}"

    assert data["status"] in ("ready", "in_progress")

    ids = {c["id"] for c in data["checks"]}
    assert ids == EXPECTED_IDS, f"unexpected ids: {ids ^ EXPECTED_IDS}"

    for c in data["checks"]:
        assert c["state"] in ("pass", "fail", "static"), c
        assert c["label"], c
        assert c["evidence"], c
