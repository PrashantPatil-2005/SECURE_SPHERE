"""Engine proxy blueprint — forwards /api/engine/* to the correlation engine.

The Flask backend (port 8000) is the single ingress the frontend talks to;
the correlation engine (port 5070) is on an internal docker network and not
directly exposed. Every Phase 13+ dashboard feature (Replay, MITRE
heatmap, Anomalies, Predict-next, YAML rules, Threat-intel, Explain) hits
the engine via these proxy routes so:

  * auth + CORS stay handled in one place,
  * the engine port doesn't have to be on the host network,
  * we can normalise error shapes (engine down → graceful 503 envelope
    instead of raw connection traceback).

All routes are protected by ``@token_required``. Each forwards the
``Authorization`` header so the engine can in future add its own RBAC.
On any upstream connection failure the route returns
``{"status": "error", "data": [], "error": "engine unavailable: <reason>"}``
with HTTP 503 — the frontend's ``api.js`` unwraps ``j.data ?? j`` so it
will see an empty list rather than crash.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests
from flask import Blueprint, Response, jsonify, request

from auth import token_required

logger = logging.getLogger("SecuriSphere.EngineProxy")

# Allow either ENGINE_URL (preferred) or the legacy SECURISPHERE_ENGINE_URL
# so deployments mid-rename keep working.
ENGINE_URL = (
    os.getenv("ENGINE_URL")
    or os.getenv("SECURISPHERE_ENGINE_URL")
    or "http://correlation-engine:5070"
).rstrip("/")

_TIMEOUT = float(os.getenv("ENGINE_PROXY_TIMEOUT", "4"))

engine_proxy_bp = Blueprint("engine_proxy", __name__, url_prefix="/api/engine")


def _forward_headers() -> dict:
    """Forward Authorization so the engine can in future enforce its own
    RBAC. Strip hop-by-hop headers."""
    h = {}
    auth = request.headers.get("Authorization")
    if auth:
        h["Authorization"] = auth
    return h


def _proxy(method: str, path: str, *, params=None, json_body=None) -> Response:
    """Forward to engine and return the upstream response verbatim. On
    connection failure return a graceful 503 envelope so the frontend's
    ``j.data ?? j`` unwrap yields an empty list/dict instead of crashing."""
    upstream = f"{ENGINE_URL}{path}"
    try:
        if method == "POST":
            r = requests.post(
                upstream,
                params=params,
                json=json_body,
                headers=_forward_headers(),
                timeout=_TIMEOUT,
            )
        else:
            r = requests.get(
                upstream,
                params=params,
                headers=_forward_headers(),
                timeout=_TIMEOUT,
            )
        return Response(
            r.content,
            status=r.status_code,
            content_type=r.headers.get("content-type", "application/json"),
        )
    except requests.RequestException as exc:
        logger.warning("engine proxy %s %s failed: %s", method, path, exc)
        return jsonify({
            "status": "error",
            "data": [],
            "error": f"engine unavailable: {exc.__class__.__name__}",
        }), 503


# ─────────────────────────────────────────────────────────────────────────
# Replay
# ─────────────────────────────────────────────────────────────────────────

@engine_proxy_bp.route("/replays", methods=["GET"])
@token_required
def replays_index():
    return _proxy("GET", "/engine/replays", params=request.args)


@engine_proxy_bp.route("/replay/<incident_id>", methods=["GET"])
@token_required
def replay_frames(incident_id: str):
    return _proxy("GET", f"/engine/replay/{incident_id}", params=request.args)


@engine_proxy_bp.route("/replay/<incident_id>/at/<int:step>", methods=["GET"])
@token_required
def replay_at(incident_id: str, step: int):
    return _proxy("GET", f"/engine/replay/{incident_id}/at/{step}")


# ─────────────────────────────────────────────────────────────────────────
# MITRE
# ─────────────────────────────────────────────────────────────────────────

@engine_proxy_bp.route("/mitre-heatmap", methods=["GET"])
@token_required
def mitre_heatmap():
    return _proxy("GET", "/engine/mitre-heatmap", params=request.args)


@engine_proxy_bp.route("/mitre-mapping", methods=["GET"])
@token_required
def mitre_mapping():
    return _proxy("GET", "/engine/mitre-mapping", params=request.args)


# ─────────────────────────────────────────────────────────────────────────
# Anomalies / Predict / YAML rules / Threat-intel / Explain
# ─────────────────────────────────────────────────────────────────────────

@engine_proxy_bp.route("/anomalies", methods=["GET"])
@token_required
def anomalies():
    return _proxy("GET", "/engine/anomalies", params=request.args)


@engine_proxy_bp.route("/predict-next", methods=["GET"])
@token_required
def predict_next():
    return _proxy("GET", "/engine/predict-next", params=request.args)


@engine_proxy_bp.route("/predictor/refit", methods=["POST"])
@token_required
def predictor_refit():
    return _proxy("POST", "/engine/predictor/refit",
                  json_body=request.get_json(silent=True))


@engine_proxy_bp.route("/yaml-rules", methods=["GET"])
@token_required
def yaml_rules():
    return _proxy("GET", "/engine/yaml-rules", params=request.args)


@engine_proxy_bp.route("/threat-intel", methods=["GET"])
@token_required
def threat_intel():
    return _proxy("GET", "/engine/threat-intel", params=request.args)


@engine_proxy_bp.route("/threat-intel/refresh", methods=["POST"])
@token_required
def threat_intel_refresh():
    return _proxy("POST", "/engine/threat-intel/refresh",
                  json_body=request.get_json(silent=True))


@engine_proxy_bp.route("/incident/<incident_id>/explain", methods=["GET"])
@token_required
def incident_explain(incident_id: str):
    return _proxy("GET", f"/engine/incident/{incident_id}/explain")


@engine_proxy_bp.route("/incident/<incident_id>/diff/<other_id>", methods=["GET"])
@token_required
def incident_diff(incident_id: str, other_id: str):
    return _proxy("GET", f"/engine/incident/{incident_id}/diff/{other_id}")


# ─────────────────────────────────────────────────────────────────────────
# Engine health / stats / risk / mttd-report — useful for dashboards
# ─────────────────────────────────────────────────────────────────────────

@engine_proxy_bp.route("/health", methods=["GET"])
@token_required
def engine_health():
    return _proxy("GET", "/engine/health")


@engine_proxy_bp.route("/stats", methods=["GET"])
@token_required
def engine_stats():
    return _proxy("GET", "/engine/stats")


@engine_proxy_bp.route("/risk-scores", methods=["GET"])
@token_required
def risk_scores():
    return _proxy("GET", "/engine/risk-scores")


@engine_proxy_bp.route("/mttd-report", methods=["GET"])
@token_required
def mttd_report():
    return _proxy("GET", "/engine/mttd-report")


@engine_proxy_bp.route("/clear-buffer", methods=["POST"])
@token_required
def clear_buffer():
    """Used by the evaluation harness between scenarios to flush the
    correlation engine's in-memory event buffer + incident cooldowns."""
    return _proxy("POST", "/engine/clear-buffer")


# ─────────────────────────────────────────────────────────────────────────
# Catch-all for any future engine route — keeps backwards-compat with the
# pre-blueprint catch-all proxy. Still token-protected.
# ─────────────────────────────────────────────────────────────────────────

@engine_proxy_bp.route("/<path:subpath>", methods=["GET", "POST"])
@token_required
def engine_catchall(subpath: str):
    method = request.method
    json_body = request.get_json(silent=True) if method == "POST" else None
    return _proxy(
        method,
        f"/engine/{subpath}",
        params=request.args,
        json_body=json_body,
    )
