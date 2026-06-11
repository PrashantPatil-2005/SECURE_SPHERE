"""Synthetic NormalizedEvent factory for throughput benchmarks (E3)."""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


EVENT_PROFILES: list[dict[str, str]] = [
    {
        "event_type": "auth_failure",
        "source_layer": "auth",
        "source_service_name": "auth-service",
        "destination_service_name": "auth-service",
        "severity": "medium",
    },
    {
        "event_type": "http_4xx",
        "source_layer": "api",
        "source_service_name": "api-server",
        "destination_service_name": "api-server",
        "severity": "low",
    },
    {
        "event_type": "lateral_movement",
        "source_layer": "network",
        "source_service_name": "api-server",
        "destination_service_name": "database",
        "severity": "high",
    },
    {
        "event_type": "port_scan",
        "source_layer": "network",
        "source_service_name": "attacker-pod",
        "destination_service_name": "api-server",
        "severity": "low",
    },
    {
        "event_type": "suspicious_login",
        "source_layer": "auth",
        "source_service_name": "attacker-pod",
        "destination_service_name": "auth-service",
        "severity": "high",
    },
]


@dataclass
class NormalizedEvent:
    """Schema-aligned synthetic security event."""

    event_id: str
    timestamp: str
    event_type: str
    source_layer: str
    source_service_name: str
    destination_service_name: str
    severity: str
    source_entity: dict[str, Any] = field(default_factory=dict)
    client_publish_ts: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize for Redis publication."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source_layer": self.source_layer,
            "source_service_name": self.source_service_name,
            "destination_service_name": self.destination_service_name,
            "severity": self.severity,
            "source_entity": self.source_entity,
            "client_publish_ts": self.client_publish_ts,
        }


def generate_event(rng: random.Random, *, profile: str = "mixed") -> NormalizedEvent:
    """Generate one realistic synthetic event.

    Args:
        rng: Seeded random generator.
        profile: ``mixed`` selects from auth/http/lateral templates.

    Returns:
        NormalizedEvent ready for publication.
    """
    if profile != "mixed":
        template = EVENT_PROFILES[0]
    else:
        template = rng.choice(EVENT_PROFILES)
    octet = rng.randint(1, 254)
    return NormalizedEvent(
        event_id=str(uuid.uuid4()),
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        event_type=template["event_type"],
        source_layer=template["source_layer"],
        source_service_name=template["source_service_name"],
        destination_service_name=template["destination_service_name"],
        severity=template["severity"],
        source_entity={"ip": f"10.0.{rng.randint(0, 5)}.{octet}"},
        client_publish_ts=time.time(),
    )


def event_to_dict(ev: NormalizedEvent) -> dict[str, Any]:
    """Convert NormalizedEvent to a plain dict."""
    return ev.to_dict()
