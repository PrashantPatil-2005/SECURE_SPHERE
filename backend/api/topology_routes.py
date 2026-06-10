"""
SecuriSphere — Topology routes
==============================
Proxies the live service-dependency graph from the topology-collector, with a
static fallback when the collector is unreachable. Token-protected.
"""

from datetime import datetime

import requests
from flask import Blueprint, jsonify

from auth import token_required

bp = Blueprint("topology_routes", __name__)


@bp.route('/api/topology')
@token_required
def get_topology():
    """
    Proxy the live service-dependency graph from the topology-collector.
    Falls back to a static description if the collector is not reachable.
    """
    try:
        resp = requests.get('http://topology-collector:5080/topology/graph', timeout=3)
        if resp.status_code == 200:
            return jsonify({"status": "success", "data": resp.json()})
    except Exception:
        pass  # fall through to static fallback

    # Static fallback: return known services without live enrichment
    static_nodes = [
        {"service_name": svc, "status": "unknown", "threat_level": "normal",
         "container_id": "", "container_name": svc, "image": "",
         "network_aliases": [], "exposed_ports": [], "labels": {}, "ip_addresses": {},
         "last_seen": datetime.utcnow().isoformat() + "Z"}
        for svc in [
            "redis", "database", "api-server", "auth-service",
            "network-monitor", "api-monitor", "auth-monitor",
            "backend", "dashboard", "correlation-engine", "web-app",
            "topology-collector",
        ]
    ]
    static_edges = [
        {"source": "api-server",    "target": "redis",       "edge_type": "event_bus"},
        {"source": "auth-service",  "target": "redis",       "edge_type": "event_bus"},
        {"source": "api-monitor",   "target": "api-server",  "edge_type": "monitors"},
        {"source": "auth-monitor",  "target": "auth-service","edge_type": "monitors"},
        {"source": "backend",       "target": "redis",       "edge_type": "event_bus"},
        {"source": "dashboard",     "target": "backend",     "edge_type": "api"},
        {"source": "web-app",       "target": "api-server",  "edge_type": "proxy"},
        {"source": "web-app",       "target": "auth-service","edge_type": "proxy"},
        {"source": "correlation-engine","target":"redis",    "edge_type": "event_bus"},
    ]
    return jsonify({
        "status": "success",
        "data": {
            "nodes": static_nodes,
            "edges": static_edges,
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_services": len(static_nodes),
            "note": "topology-collector unavailable; static fallback returned",
        }
    })


@bp.route('/api/topology/service/<service_name>')
@token_required
def get_topology_service(service_name):
    """Proxy a single service lookup from the topology-collector."""
    try:
        resp = requests.get(
            f'http://topology-collector:5080/topology/service/{service_name}', timeout=3
        )
        if resp.status_code == 200:
            return jsonify({"status": "success", "data": resp.json()})
        return jsonify({"status": "error", "message": "Service not found"}), 404
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 503
