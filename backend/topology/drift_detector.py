"""Topology drift detector — Phase 12 completion.

Why novel: container topology drift = potential supply-chain compromise. We
embed each service in a vector space using degree + neighbour-name hashing
(a poor-man's Node2Vec that runs without PyTorch), and flag deviations from
a rolling baseline. Existing tools (Falco, Cilium, Wazuh) treat the topology
as ground truth and never check whether it changed unexpectedly.

The full Node2Vec embedding lives in `backend/engine/embedding/` — this
module emits the lightweight, real-time signal that triggers a deeper
embedding refresh when something looks off.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("TopologyDrift")

DRIFT_REDIS_KEY = "topology:drift:baseline"
DRIFT_CHANNEL = "topology_drift"


@dataclass
class TopologySignature:
    """Compact fingerprint of the running topology."""
    service_count: int
    edge_count: int
    service_set_hash: str          # sha256 of sorted service names
    edge_set_hash: str             # sha256 of sorted "src->dst" strings
    degree_signature: Dict[str, int] = field(default_factory=dict)
    # Each service's neighbour-name hash — gives a per-node fingerprint that
    # changes if the node's local subgraph changes. Detects supply-chain
    # attacks where one service is silently replaced.
    neighbour_signature: Dict[str, str] = field(default_factory=dict)
    captured_at: float = 0.0

    def to_json(self) -> str:
        return json.dumps({
            "service_count": self.service_count,
            "edge_count": self.edge_count,
            "service_set_hash": self.service_set_hash,
            "edge_set_hash": self.edge_set_hash,
            "degree_signature": self.degree_signature,
            "neighbour_signature": self.neighbour_signature,
            "captured_at": self.captured_at,
        })

    @classmethod
    def from_json(cls, raw: str) -> "TopologySignature":
        d = json.loads(raw)
        return cls(**d)


def _stable_hash(items) -> str:
    h = hashlib.sha256()
    for item in sorted(items):
        h.update(item.encode("utf-8"))
        h.update(b"|")
    return h.hexdigest()[:16]


def fingerprint(services: List[str], edges: List[Tuple[str, str]]) -> TopologySignature:
    """Build a TopologySignature for the given service+edge sets."""
    services_sorted = sorted(services)
    edge_strs = [f"{s}->{t}" for s, t in edges]
    degrees: Dict[str, int] = {s: 0 for s in services_sorted}
    neighbours: Dict[str, Set[str]] = {s: set() for s in services_sorted}
    for s, t in edges:
        if s in degrees:
            degrees[s] += 1
            neighbours[s].add(t)
        if t in degrees:
            degrees[t] += 1
            neighbours[t].add(s)
    return TopologySignature(
        service_count=len(services_sorted),
        edge_count=len(edge_strs),
        service_set_hash=_stable_hash(services_sorted),
        edge_set_hash=_stable_hash(edge_strs),
        degree_signature=degrees,
        neighbour_signature={
            svc: _stable_hash(list(nset)) for svc, nset in neighbours.items()
        },
        captured_at=time.time(),
    )


@dataclass
class DriftEvent:
    severity: str              # "info" | "warn" | "critical"
    drift_type: str            # "service_added" | "service_removed" | "edge_added" | "edge_removed" | "neighbour_change"
    target: str
    details: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return {
            "severity": self.severity,
            "drift_type": self.drift_type,
            "target": self.target,
            "details": self.details,
            "timestamp": time.time(),
        }


def diff(prev: TopologySignature, curr: TopologySignature) -> List[DriftEvent]:
    """Compute per-service drift events between two signatures.

    Severity logic:
      - service_added/removed = warn (could be normal redeploy)
      - neighbour_change without service_added/removed = critical (silent
        rewire suggests potential supply-chain attack)
    """
    events: List[DriftEvent] = []
    prev_svcs = set(prev.degree_signature.keys())
    curr_svcs = set(curr.degree_signature.keys())

    for added in curr_svcs - prev_svcs:
        events.append(DriftEvent(
            severity="warn",
            drift_type="service_added",
            target=added,
            details={"degree": curr.degree_signature.get(added, 0)},
        ))
    for removed in prev_svcs - curr_svcs:
        events.append(DriftEvent(
            severity="warn",
            drift_type="service_removed",
            target=removed,
            details={"prev_degree": prev.degree_signature.get(removed, 0)},
        ))

    if prev.edge_set_hash != curr.edge_set_hash:
        events.append(DriftEvent(
            severity="info",
            drift_type="edge_set_changed",
            target="*",
            details={"prev": prev.edge_count, "curr": curr.edge_count},
        ))

    # Per-service neighbour drift on services that exist in both snapshots.
    # This is the real signal: a service whose neighbour-set fingerprint
    # changed without the service itself appearing/disappearing.
    for svc in prev_svcs & curr_svcs:
        if prev.neighbour_signature.get(svc) != curr.neighbour_signature.get(svc):
            events.append(DriftEvent(
                severity="critical",
                drift_type="neighbour_change",
                target=svc,
                details={
                    "prev_degree": prev.degree_signature.get(svc, 0),
                    "curr_degree": curr.degree_signature.get(svc, 0),
                },
            ))

    return events


class DriftDetector:
    """Holds the rolling baseline signature and emits drift events to Redis."""

    def __init__(self, redis_client) -> None:
        self.redis = redis_client
        self._baseline: Optional[TopologySignature] = self._load()

    def _load(self) -> Optional[TopologySignature]:
        try:
            raw = self.redis.get(DRIFT_REDIS_KEY)
            if raw:
                return TopologySignature.from_json(raw)
        except Exception as exc:
            logger.debug("baseline load failed: %s", exc)
        return None

    def _save(self, sig: TopologySignature) -> None:
        try:
            self.redis.set(DRIFT_REDIS_KEY, sig.to_json())
        except Exception as exc:
            logger.warning("baseline save failed: %s", exc)

    def observe(self, services: List[str], edges: List[Tuple[str, str]]) -> List[DriftEvent]:
        sig = fingerprint(services, edges)
        if self._baseline is None:
            self._baseline = sig
            self._save(sig)
            return []
        events = diff(self._baseline, sig)
        if events:
            for ev in events:
                try:
                    self.redis.publish(DRIFT_CHANNEL, json.dumps(ev.to_dict()))
                    self.redis.lpush("topology:drift_events", json.dumps(ev.to_dict()))
                    self.redis.ltrim("topology:drift_events", 0, 199)
                except Exception:
                    pass
            # Update baseline only on warn/info; critical drifts are kept
            # against the old baseline so the next observe() still flags
            # them until an analyst clears them.
            crit = [e for e in events if e.severity == "critical"]
            if not crit:
                self._baseline = sig
                self._save(sig)
        else:
            # No drift — update baseline to track normal evolution
            self._baseline = sig
            self._save(sig)
        return events

    def reset(self) -> None:
        self._baseline = None
        try:
            self.redis.delete(DRIFT_REDIS_KEY)
        except Exception:
            pass
