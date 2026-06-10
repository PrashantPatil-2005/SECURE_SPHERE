"""Proxy selected read APIs to the FastAPI BFF."""

from __future__ import annotations

import logging
import os

import requests
from flask import Blueprint, Response, request

from auth import token_required

logger = logging.getLogger("SecuriSphere.BFFProxy")

BFF_URL = os.getenv("BFF_URL", "http://bff:8001")

bp = Blueprint("bff_proxy", __name__)


def _proxy(path: str) -> Response:
    url = f"{BFF_URL}{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    try:
        upstream = requests.request(
            method=request.method,
            url=url,
            headers={"Authorization": request.headers.get("Authorization", "")},
            timeout=15,
        )
        return Response(upstream.content, status=upstream.status_code, mimetype="application/json")
    except requests.RequestException as exc:
        logger.warning("BFF proxy failed: %s", exc)
        return Response(
            '{"error":"bff unavailable"}',
            status=503,
            mimetype="application/json",
        )


@bp.route("/api/search/events", methods=["GET"])
@bp.route("/api/evaluation/results", methods=["GET"])
@token_required
def bff_routes():
    return _proxy(request.path)
