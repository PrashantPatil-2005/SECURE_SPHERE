"""FastAPI ingestion service — validates events and XADD to Redis Streams."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Resolve shared event schema
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from shared.event_schema import normalize_event  # noqa: E402

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_EVENTS = os.getenv("EVENT_STREAM", "securisphere:events")

app = FastAPI(title="SecuriSphere Ingestion", version="1.0.0")
_redis: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    return _redis


class EventBatch(BaseModel):
    events: List[Dict[str, Any]]


@app.get("/health")
def health():
    try:
        get_redis().ping()
        return {"status": "ok", "service": "ingestion"}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


def _xadd_event(event: Dict[str, Any]) -> str:
    event = normalize_event(event)
    if not event.get("timestamp"):
        event["timestamp"] = datetime.utcnow().isoformat() + "Z"
    r = get_redis()
    return r.xadd(STREAM_EVENTS, {"payload": json.dumps(event)})


@app.post("/ingest/events")
def ingest_events(batch: EventBatch):
    ids = []
    for ev in batch.events:
        ids.append(_xadd_event(ev))
    return {"accepted": len(ids), "ids": ids}


@app.post("/ingest/syslog")
def ingest_syslog(body: Dict[str, Any]):
    line = body.get("line") or body.get("message", "")
    event = {
        "event_id": body.get("event_id"),
        "timestamp": body.get("timestamp") or datetime.utcnow().isoformat() + "Z",
        "source_layer": "syslog",
        "source_monitor": "ingestion",
        "event_category": "log",
        "event_type": "syslog",
        "severity": {"level": "info", "score": 10},
        "source_entity": {"ip": body.get("host")},
        "detection_details": {"description": line[:500], "confidence": 0.5},
    }
    eid = _xadd_event(event)
    return {"id": eid}


@app.post("/ingest/docker-events")
def ingest_docker_events(body: Dict[str, Any]):
    action = body.get("Action") or body.get("action", "unknown")
    actor = body.get("Actor", {}) or {}
    attrs = actor.get("Attributes", {}) or {}
    svc = attrs.get("com.docker.compose.service")
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source_layer": "docker",
        "source_monitor": "ingestion",
        "event_category": "lifecycle",
        "event_type": f"docker_{action}",
        "severity": {"level": "medium", "score": 40},
        "source_service_name": svc,
        "workload_id": actor.get("ID"),
        "detection_details": {"description": f"Docker {action} on {svc}", "confidence": 0.9},
        "mitre_technique": "T1525" if action in ("die", "destroy", "remove") else None,
    }
    eid = _xadd_event(event)
    return {"id": eid}
