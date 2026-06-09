# Vendored copy of backend/engine/shared/event_schema.py for isolated monitor containers.
from __future__ import annotations

from typing import Any, Dict, Optional


def _get_ip(event: Dict[str, Any]) -> Optional[str]:
    ent = event.get("source_entity") or {}
    ip = ent.get("ip") or event.get("source_ip")
    if ip in (None, "", "?", "unknown", "0.0.0.0"):
        return None
    return str(ip)


def _get_dest_service(event: Dict[str, Any]) -> Optional[str]:
    dst = event.get("destination_service_name")
    if dst:
        return str(dst)
    target = event.get("target_entity") or {}
    svc = target.get("service")
    return str(svc) if svc else None


def _get_workload_id(event: Dict[str, Any]) -> Optional[str]:
    wl = event.get("workload_id")
    if wl:
        return str(wl)
    ent = event.get("source_entity") or {}
    cid = ent.get("container_id")
    return str(cid) if cid else None


def resolve_correlation_key(event: Dict[str, Any]) -> str:
    src_svc = event.get("source_service_name")
    dst_svc = _get_dest_service(event)
    workload = _get_workload_id(event)
    session = event.get("attack_session_id") or event.get("trace_id")
    ip = _get_ip(event)

    if src_svc and dst_svc:
        base = f"svc:{src_svc}→{dst_svc}"
        if session:
            return f"{base}:{session}"
        return base
    if src_svc:
        base = f"svc:{src_svc}"
        if session:
            return f"{base}:{session}"
        return base
    if workload:
        return f"wl:{workload}"
    if ip and dst_svc:
        return f"ip:{ip}→{dst_svc}"
    if ip:
        return f"ip:{ip}"
    if session:
        return f"trace:{session}"
    return "unknown"


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    target = event.get("target_entity") or {}
    source = event.get("source_entity") or {}
    if not event.get("destination_service_name") and target.get("service"):
        event["destination_service_name"] = target["service"]
    if not event.get("workload_id") and source.get("container_id"):
        event["workload_id"] = source["container_id"]
    if not event.get("source_ip") and source.get("ip"):
        event["source_ip"] = source["ip"]
    if not event.get("source_service_name") and event.get("destination_service_name"):
        event.setdefault("ingress_attribution", "external")
    event["correlation_key"] = resolve_correlation_key(event)
    return event
