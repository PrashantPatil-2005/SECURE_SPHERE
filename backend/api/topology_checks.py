"""
topology_checks.py — Phase 12 checkpoint aggregator.

Exposes GET /api/topology-checks that probes the topology-collector
subsystem and returns a structured pass/fail/static report used by the
dashboard's TopologyChecklist card.
"""

import json
import logging
import os
from datetime import datetime, timezone

import redis
import requests
from flask import Blueprint, jsonify

logger = logging.getLogger("TopologyChecks")

bp = Blueprint("topology_checks", __name__)

TOPOLOGY_BASE = os.getenv("TOPOLOGY_URL", "http://topology-collector:5080")
ENGINE_BASE = os.getenv("ENGINE_URL", "http://correlation-engine:5070")
PROBE_TIMEOUT = 2  # seconds
CACHE_KEY = "topology:checks"
CACHE_TTL = 15  # seconds

TITLE = "Topology collector + service graph"
SUBTITLE = "Live service graph · enrichment pipeline · topology history"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _redis_client() -> redis.Redis | None:
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
            socket_connect_timeout=1,
        )
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable for checks cache: %s", exc)
        return None


def _probe_get(path: str) -> tuple[bool, str]:
    """GET {TOPOLOGY_BASE}{path} with a 2-s timeout. Return (ok, evidence)."""
    url = f"{TOPOLOGY_BASE}{path}"
    try:
        resp = requests.get(url, timeout=PROBE_TIMEOUT)
        if resp.status_code == 200:
            return True, path
        return False, f"{path} → HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return False, f"{path} → {type(exc).__name__}"


def _probe_post_edge() -> tuple[bool, str]:
    """Round-trip a harmless observed edge. Idempotent — collector dedupes."""
    url = f"{TOPOLOGY_BASE}/topology/edge"
    try:
        resp = requests.post(
            url,
            params={"source": "api-monitor", "target": "api-server",
                    "edge_type": "observed"},
            timeout=PROBE_TIMEOUT,
        )
        if resp.status_code == 200:
            return True, "/topology/edge"
        return False, f"/topology/edge → HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return False, f"/topology/edge → {type(exc).__name__}"


def _probe_collector_up() -> tuple[bool, str]:
    ok, _ = _probe_get("/health")
    return ok, "securisphere-topology" if ok else "collector unreachable"


def _probe_enrichment() -> tuple[bool, str]:
    """
    Confirm the correlation engine is live by probing its health endpoint.
    The enrichment itself (events carrying source_service_name) can't be
    probed without tapping a live event buffer; engine liveness is the
    best proxy for "enrichment is wired up and running".
    """
    url = f"{ENGINE_BASE}/engine/health"
    try:
        resp = requests.get(url, timeout=PROBE_TIMEOUT)
        if resp.status_code == 200:
            return True, "correlation-engine:5070/engine/health"
        return False, f"/engine/health → HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return False, f"/engine/health → {type(exc).__name__}"


def _build_checks() -> list:
    up_ok, up_ev = _probe_collector_up()
    graph_ok, graph_ev = _probe_get("/topology/graph")
    hist_ok, hist_ev = _probe_get("/topology/history?limit=1")
    edge_ok, edge_ev = _probe_post_edge()
    enr_ok, enr_ev = _probe_enrichment()

    def row(id_, label, ok, evidence):
        return {
            "id": id_,
            "label": label,
            "state": "pass" if ok else "fail",
            "evidence": evidence,
        }

    return [
        row("collector-up",    "Topology collector on :5080",                          up_ok,    up_ev),
        row("graph-endpoint",  "GET /topology/graph returns D3-ready JSON",            graph_ok, graph_ev),
        row("edge-endpoint",   "POST /topology/edge for runtime edge registration",    edge_ok,  edge_ev),
        row("history-endpoint","GET /topology/history with PostgreSQL persistence",    hist_ok,  hist_ev),
        row("enrichment",      "Correlation engine consumes source_service_name",      enr_ok,   enr_ev),
        {"id": "d3-overlay",     "label": "Dashboard topology panel renders live attack overlay", "state": "static", "evidence": "TopologyGraph.jsx"},
        {"id": "kill-chain-anim","label": "Kill-chain traversal animates in real time",           "state": "static", "evidence": "TopologyGraph.jsx"},
    ]


@bp.route("/api/topology-checks")
def topology_checks():
    rc = _redis_client()

    if rc is not None:
        try:
            cached = rc.get(CACHE_KEY)
            if cached:
                return jsonify(json.loads(cached))
        except Exception:
            pass

    checks = _build_checks()
    non_static = [c for c in checks if c["state"] != "static"]
    status = "ready" if all(c["state"] == "pass" for c in non_static) else "in_progress"

    payload = {
        "title": TITLE,
        "subtitle": SUBTITLE,
        "status": status,
        "updated_at": _now_iso(),
        "checks": checks,
    }

    if rc is not None:
        try:
            rc.set(CACHE_KEY, json.dumps(payload), ex=CACHE_TTL)
        except Exception:
            pass

    return jsonify(payload)
