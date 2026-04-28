"""
topology_collector.py — SecuriSphere Phase 12

Live service-topology collector for the Docker Compose environment.
Queries the Docker daemon every 10 seconds via the Docker SDK, extracts
service-identity metadata (service name, container ID, image, network
aliases, ports), builds a ServiceGraph with dependency edges, and exposes
the graph through a FastAPI REST interface.  Updates are also published to
the Redis channel ``topology_updates`` so the correlation engine and
dashboard receive live topology diffs without polling.

Architecture role
-----------------
  Docker daemon  ──► topology_collector  ──► Redis (topology_updates)
                                          └──► REST GET /topology/...
  correlation_engine ──► GET /topology/service/{name}  (enrichment)
  frontend dashboard ──► GET /topology/graph           (D3 visualisation)
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import docker
import redis
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("TopologyCollector")

# ---------------------------------------------------------------------------
# Configuration (all overrideable via environment variables)
# ---------------------------------------------------------------------------

REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
REFRESH_INTERVAL: int = int(os.getenv("TOPOLOGY_REFRESH_INTERVAL", 10))  # seconds
COMPOSE_PROJECT: str = os.getenv("COMPOSE_PROJECT_NAME", "securisphere")

# Known static dependency edges extracted from the Compose file.
# These are augmented at runtime by traffic-observed edges.
STATIC_EDGES: List[Dict[str, str]] = [
    {"source": "api-server",   "target": "redis",      "type": "event_bus"},
    {"source": "auth-service", "target": "redis",      "type": "event_bus"},
    {"source": "api-server",   "target": "database",   "type": "database"},
    {"source": "api-monitor",  "target": "api-server", "type": "monitors"},
    {"source": "auth-monitor", "target": "auth-service","type": "monitors"},
    {"source": "network-monitor","target":"api-server", "type": "monitors"},
    {"source": "backend",      "target": "redis",      "type": "event_bus"},
    {"source": "correlation-engine","target":"redis",  "type": "event_bus"},
    {"source": "dashboard",    "target": "backend",    "type": "api"},
    {"source": "web-app",      "target": "api-server", "type": "proxy"},
    {"source": "web-app",      "target": "auth-service","type": "proxy"},
    {"source": "topology-collector","target":"redis",  "type": "event_bus"},
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ServiceNode(BaseModel):
    """Represents a single running container / Docker Compose service."""
    service_name: str          # com.docker.compose.service label
    container_id: str          # short container ID (12 chars)
    container_name: str        # full container name
    image: str                 # image name:tag
    status: str                # running | exited | …
    network_aliases: List[str]
    exposed_ports: List[str]   # ["5000/tcp", …]
    labels: Dict[str, str]
    ip_addresses: Dict[str, str]  # network_name → ip
    threat_level: str          # enriched from risk_scores_current
    last_seen: str             # ISO-8601 UTC


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str             # event_bus | database | proxy | monitors | api | observed
    observed: bool = False


class ServiceGraph(BaseModel):
    nodes: List[ServiceNode]
    edges: List[GraphEdge]
    last_updated: str
    total_services: int


# ---------------------------------------------------------------------------
# In-process state (updated by the background collector)
# ---------------------------------------------------------------------------

_service_map: Dict[str, ServiceNode] = {}          # service_name → node
_graph_edges: List[Dict[str, str]] = list(STATIC_EDGES)  # mutable edge list
_last_updated: str = ""

# ---------------------------------------------------------------------------
# Redis helper
# ---------------------------------------------------------------------------

def _build_redis() -> redis.Redis:
    """Return a connected Redis client, retrying indefinitely until success."""
    while True:
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis at %s:%s", REDIS_HOST, REDIS_PORT)
            return client
        except redis.ConnectionError:
            logger.warning("Redis not ready, retrying in 3 s…")
            time.sleep(3)


_redis: redis.Redis = _build_redis()

# ---------------------------------------------------------------------------
# Docker collector
# ---------------------------------------------------------------------------


def _safe_short_id(container_id: str) -> str:
    return container_id[:12] if container_id else ""


def _collect_topology() -> Dict[str, ServiceNode]:
    """Query Docker daemon and return a fresh service_name → ServiceNode map."""
    try:
        client = docker.from_env()
    except docker.errors.DockerException as exc:
        logger.error("Cannot reach Docker daemon: %s", exc)
        return {}

    nodes: Dict[str, ServiceNode] = {}

    try:
        containers = client.containers.list(all=False)  # running only
    except docker.errors.APIError as exc:
        logger.error("Docker API error listing containers: %s", exc)
        return {}

    # Fetch current risk scores from Redis so we can colour nodes
    try:
        raw_risks = _redis.hgetall("risk_scores_current")
        risk_map: Dict[str, str] = {}
        for ip, payload in raw_risks.items():
            try:
                data = json.loads(payload)
                risk_map[ip] = data.get("threat_level", "normal")
            except json.JSONDecodeError:
                pass
    except Exception:
        risk_map = {}

    for container in containers:
        labels = container.labels or {}

        # Extract Docker Compose service name (falls back to container name)
        service_name = (
            labels.get("com.docker.compose.service")
            or container.name.lstrip("/")
        )

        # Network aliases and IPs
        network_aliases: List[str] = []
        ip_addresses: Dict[str, str] = {}
        try:
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            for net_name, net_data in networks.items():
                aliases = net_data.get("Aliases") or []
                network_aliases.extend(aliases)
                ip = net_data.get("IPAddress", "")
                if ip:
                    ip_addresses[net_name] = ip
        except Exception:
            pass

        # Remove duplicate aliases
        network_aliases = list(set(network_aliases))

        # Exposed ports
        exposed_ports: List[str] = []
        try:
            ports_data = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            exposed_ports = list(ports_data.keys())
        except Exception:
            pass

        # Enrich threat level: scan all IPs associated with this container
        threat_level = "normal"
        for ip in ip_addresses.values():
            level = risk_map.get(ip, "normal")
            # Escalate to worst level
            priority = {"normal": 0, "suspicious": 1, "threatening": 2, "critical": 3}
            if priority.get(level, 0) > priority.get(threat_level, 0):
                threat_level = level

        nodes[service_name] = ServiceNode(
            service_name=service_name,
            container_id=_safe_short_id(container.id),
            container_name=container.name,
            image=container.image.tags[0] if container.image.tags else container.image.id[:12],
            status=container.status,
            network_aliases=network_aliases,
            exposed_ports=exposed_ports,
            labels={k: v for k, v in labels.items() if k.startswith("com.docker.compose")},
            ip_addresses=ip_addresses,
            threat_level=threat_level,
            last_seen=datetime.utcnow().isoformat() + "Z",
        )

    return nodes


def _publish_update(nodes: Dict[str, ServiceNode]) -> None:
    """Publish a topology snapshot to the ``topology_updates`` Redis channel."""
    payload = {
        "event": "topology_refresh",
        "services": {name: node.dict() for name, node in nodes.items()},
        "edges": _graph_edges,
        "total_services": len(nodes),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    try:
        _redis.publish("topology_updates", json.dumps(payload))
        # Also persist latest snapshot for the REST API (avoids re-querying Docker)
        _redis.set("topology:latest", json.dumps(payload), ex=60)
    except Exception as exc:
        logger.error("Failed to publish topology update: %s", exc)


def _pg_conn():
    """Open a psycopg2 connection to the SecuriSphere Postgres DB.

    Used by the collector loop to persist snapshots and by the history
    endpoint to read them back. Imported lazily so the service still
    starts if psycopg2 is unavailable (e.g. during local dev).
    """
    import psycopg2  # local import — keeps startup fast in minimal envs
    return psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def _persist_snapshot(nodes: Dict[str, "ServiceNode"]) -> None:
    """Persist the current topology to the ``topology_snapshots`` table.

    Best-effort: logs and swallows errors so a DB outage cannot crash the
    collector loop. The table is created by ``scripts/init_db.sql``.
    """
    try:
        snapshot = {
            "nodes": [n.model_dump() if hasattr(n, "model_dump") else dict(n)
                      for n in nodes.values()],
            "edges": [
                {"source": e["source"], "target": e["target"],
                 "type": e.get("type", "unknown"),
                 "observed": e.get("observed", False)}
                for e in _graph_edges
                if e["source"] in nodes and e["target"] in nodes
            ],
            "captured_at": datetime.utcnow().isoformat() + "Z",
        }
        conn = _pg_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO topology_snapshots (snapshot, service_count, captured_at) "
                    "VALUES (%s::jsonb, %s, NOW())",
                    (json.dumps(snapshot), len(nodes)),
                )
        conn.close()
    except Exception as exc:
        logger.warning("Topology persist skipped: %s", exc)


async def _collector_loop() -> None:
    """Async background task: refresh topology every REFRESH_INTERVAL seconds."""
    global _service_map, _last_updated

    while True:
        try:
            fresh = _collect_topology()
            if fresh:
                _service_map = fresh
                _last_updated = datetime.utcnow().isoformat() + "Z"
                _publish_update(fresh)
                _persist_snapshot(fresh)
                logger.info("Topology refreshed: %d services", len(fresh))
        except Exception as exc:
            logger.error("Collector loop error: %s", exc, exc_info=True)

        await asyncio.sleep(REFRESH_INTERVAL)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SecuriSphere Topology Collector",
    description="Live Docker service-topology graph for correlation & visualisation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Register the background collector when the server starts."""
    asyncio.create_task(_collector_loop())
    logger.info("Topology Collector started — refresh every %ds", REFRESH_INTERVAL)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Liveness probe used by Docker Compose healthcheck."""
    return {
        "status": "healthy",
        "service": "topology-collector",
        "redis_connected": True,
        "total_services": len(_service_map),
        "last_updated": _last_updated,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/topology/services", response_model=List[ServiceNode])
async def list_services() -> List[ServiceNode]:
    """Return all currently running services as a flat list."""
    return list(_service_map.values())


@app.get("/topology/graph", response_model=ServiceGraph)
async def get_graph() -> ServiceGraph:
    """
    Return the full service-dependency graph suitable for D3.js rendering.

    Nodes are coloured by ``threat_level``; edges carry a ``type`` label.
    """
    if not _service_map:
        raise HTTPException(status_code=503, detail="Topology not yet collected")

    # Only include edges whose endpoints actually exist in the running graph
    active_names = set(_service_map.keys())
    active_edges = [
        GraphEdge(
            source=e["source"],
            target=e["target"],
            edge_type=e.get("type", "unknown"),
            observed=e.get("observed", False),
        )
        for e in _graph_edges
        if e["source"] in active_names and e["target"] in active_names
    ]

    return ServiceGraph(
        nodes=list(_service_map.values()),
        edges=active_edges,
        last_updated=_last_updated or datetime.utcnow().isoformat() + "Z",
        total_services=len(_service_map),
    )


@app.get("/topology/service/{name}", response_model=Optional[ServiceNode])
async def get_service(name: str) -> ServiceNode:
    """
    Look up a specific service by name.

    Used by the correlation engine's enrichment pipeline to tag each event
    with ``source_service_name`` / ``destination_service_name``.
    """
    node = _service_map.get(name)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return node


@app.get("/topology/history")
async def topology_history(limit: int = 10) -> Dict[str, Any]:
    """
    Return the most recent topology snapshots from PostgreSQL.

    Query params:
        limit (int, default 10, max 100) — number of snapshots to return

    Each snapshot contains ``nodes``, ``edges``, and ``captured_at``.
    """
    limit = max(1, min(int(limit), 100))
    try:
        conn = _pg_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, snapshot, service_count, captured_at "
                "FROM topology_snapshots "
                "ORDER BY captured_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
        conn.close()

        history = []
        for row in rows:
            snapshot_id, snapshot, service_count, captured_at = row
            if isinstance(snapshot, str):
                try:
                    snapshot = json.loads(snapshot)
                except Exception:
                    pass
            history.append({
                "id": str(snapshot_id),
                "snapshot": snapshot,
                "service_count": service_count,
                "captured_at": captured_at.isoformat() if hasattr(captured_at, "isoformat") else captured_at,
            })

        return {"count": len(history), "history": history}
    except Exception as exc:
        logger.error("topology_history error: %s", exc)
        raise HTTPException(status_code=503, detail=f"history unavailable: {exc}")


@app.post("/topology/edge")
async def add_observed_edge(source: str, target: str, edge_type: str = "observed") -> Dict[str, str]:
    """
    Register a traffic-observed dependency edge at runtime.

    Called by the correlation engine when it detects cross-service event pairs
    (e.g. auth-service → api-server event correlation).
    """
    edge = {"source": source, "target": target, "type": edge_type, "observed": True}
    # Avoid exact duplicates
    if edge not in _graph_edges:
        _graph_edges.append(edge)
        logger.info("New observed edge: %s → %s (%s)", source, target, edge_type)
    return {"status": "ok", "source": source, "target": target}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "topology_collector:app",
        host="0.0.0.0",
        port=5080,
        log_level="info",
        reload=False,
    )
