"""End-to-end detection latency measurement for E3 throughput benchmark."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

def publish_event(redis_client, event: dict[str, Any]) -> str:
    """Publish event and return stream id if available, else empty string.

    Args:
        redis_client: Redis client.
        event: Event dict with optional client_publish_ts.

    Returns:
        Redis stream entry id or pub/sub ack placeholder.
    """
    event = dict(event)
    event.setdefault("client_publish_ts", time.time())
    payload = json.dumps(event)
    stream = os.getenv("SECURISPHERE_EVENT_STREAM", "securisphere:events")
    try:
        entry_id = redis_client.xadd(stream, {"payload": payload}, maxlen=100_000)
        return str(entry_id)
    except Exception:
        redis_client.publish("security_events", payload)
        return ""


def wait_for_incident(
    redis_client,
    *,
    since_ts: float,
    timeout_sec: float = 5.0,
    event_id: str | None = None,
) -> float | None:
    """Wait for incident/kill-chain signal after event publication.

    Detection latency = time from client_publish_ts to Postgres/Redis incident.

    Args:
        redis_client: Redis client.
        since_ts: Publication epoch (fallback if event_id lookup fails).
        timeout_sec: Max wait seconds.
        event_id: Optional event id to match in incident correlated events.

    Returns:
        Latency in milliseconds, or None on timeout.
    """
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        # Fast path: recent incidents list on Redis
        raw_list = redis_client.lrange("incidents", 0, 99) or []
        for raw in raw_list:
            try:
                inc = json.loads(raw)
            except json.JSONDecodeError:
                continue
            detected_at = inc.get("detected_at") or inc.get("timestamp")
            if not detected_at:
                continue
            try:
                dt = datetime.fromisoformat(str(detected_at).replace("Z", "+00:00"))
                detected_epoch = dt.timestamp()
            except ValueError:
                detected_epoch = since_ts
            if detected_epoch + 1 < since_ts:
                continue
            latency_ms = max((detected_epoch - since_ts) * 1000.0, 0.0)
            if event_id:
                events = inc.get("correlated_events") or []
                if not any(e.get("event_id") == event_id for e in events if isinstance(e, dict)):
                    continue
            return round(latency_ms, 3)
        time.sleep(0.05)
    return None
