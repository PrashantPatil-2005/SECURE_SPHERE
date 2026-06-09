"""Agent manager — registers docker agents and forwards events to ingestion."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
from fastapi import FastAPI
from pydantic import BaseModel

INGESTION_URL = os.getenv("INGESTION_URL", "http://ingestion:5010")
app = FastAPI(title="SecuriSphere Agent Manager", version="1.0.0")
_agents: Dict[str, Dict[str, Any]] = {}


class AgentRegister(BaseModel):
    agent_id: str
    hostname: str = "unknown"
    capabilities: List[str] = []


class EventBatch(BaseModel):
    events: List[Dict[str, Any]]


@app.get("/health")
def health():
    return {"status": "ok", "agents": len(_agents)}


@app.post("/agents/register")
def register(agent: AgentRegister):
    _agents[agent.agent_id] = agent.model_dump()
    return {"registered": True}


@app.get("/agents")
def list_agents():
    return {"agents": list(_agents.values())}


@app.post("/agents/{agent_id}/events")
def forward_events(agent_id: str, batch: EventBatch):
    if agent_id not in _agents:
        _agents[agent_id] = {"agent_id": agent_id}
    try:
        resp = requests.post(
            f"{INGESTION_URL}/ingest/events",
            json={"events": batch.events},
            timeout=10,
        )
        return resp.json()
    except Exception as exc:
        return {"error": str(exc), "accepted": 0}
