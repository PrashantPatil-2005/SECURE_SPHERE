"""
Canonical event shape and service-centric correlation key resolution.

All monitors and the ingestion service should call ``normalize_event()`` before
publishing so ``correlation_key`` is stable across the pipeline.
"""

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
    """Stable correlation identity — service-first, IP last."""
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
    """Ensure service-identity fields and correlation_key are populated."""
    target = event.get("target_entity") or {}
    source = event.get("source_entity") or {}

    if not event.get("destination_service_name") and target.get("service"):
        event["destination_service_name"] = target["service"]

    if not event.get("workload_id") and source.get("container_id"):
        event["workload_id"] = source["container_id"]

    if not event.get("source_ip") and source.get("ip"):
        event["source_ip"] = source["ip"]

    # External attackers: attribute ingress when hitting a known destination
    if not event.get("source_service_name") and event.get("destination_service_name"):
        event.setdefault("ingress_attribution", "external")

    event["correlation_key"] = resolve_correlation_key(event)
    return event


def events_same_actor(
    a: Dict[str, Any],
    b: Dict[str, Any],
    *,
    mode: str = "service",
) -> bool:
    """Return True if two events belong to the same correlatable actor."""
    if mode == "legacy":
        return _get_ip(a) == _get_ip(b) and _get_ip(a) is not None

    ka = a.get("correlation_key") or resolve_correlation_key(a)
    kb = b.get("correlation_key") or resolve_correlation_key(b)
    if ka != "unknown" and ka == kb:
        return True

    if mode == "dual":
        ia, ib = _get_ip(a), _get_ip(b)
        return ia is not None and ia == ib

    return False


def filter_buffer_by_actor(
    buffer: list,
    event: Dict[str, Any],
    *,
    mode: str = "service",
) -> list:
    """Return buffer events matching the same actor as *event*."""
    key = event.get("correlation_key") or resolve_correlation_key(event)
    if mode == "legacy":
        ip = _get_ip(event)
        return [
            e for e in buffer
            if _get_ip(e) == ip and ip is not None
        ]

    matched = [
        e for e in buffer
        if (e.get("correlation_key") or resolve_correlation_key(e)) == key
        and key != "unknown"
    ]
    if matched or mode != "dual":
        return matched

    ip = _get_ip(event)
    return [e for e in buffer if _get_ip(e) == ip and ip is not None]
