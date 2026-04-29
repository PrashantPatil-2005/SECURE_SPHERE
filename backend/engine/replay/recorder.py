"""Record replay frames as a kill chain forms.

A *frame* is the minimum state needed to reconstruct one timestep of the
attack from a fresh dashboard load:
  - the event that fired,
  - the affected services + edges (graph delta from the previous frame),
  - the running risk score for the source service,
  - which rule (if any) was triggered at this step,
  - cumulative MITRE techniques observed up to and including this frame.

Frames are append-only. The replay player reconstructs intermediate state
by applying frames in order — there is no separate "snapshot" — so a frame
must always carry enough data to stand alone for that single timestep.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("ReplayRecorder")

REPLAY_PREFIX = os.getenv("SECURISPHERE_REPLAY_PREFIX", "securisphere:replay:")
REPLAY_INDEX_KEY = "securisphere:replay:index"   # sorted set: incident_id → first_event_ts
REPLAY_TTL_SECONDS = int(os.getenv("REPLAY_TTL_SECONDS", str(7 * 24 * 3600)))  # 1 week


class ReplayRecorder:
    def __init__(self, redis_client, bus=None) -> None:
        self.redis = redis_client
        self.bus = bus
        # Per-incident accumulator state — kept in memory only for the
        # lifetime of the engine process. The authoritative log lives in
        # Redis, so a restart loses the dedup-set but not the frames.
        self._seen_techniques: Dict[str, Set[str]] = {}
        self._seen_services: Dict[str, Set[str]] = {}

    # ------------------------------------------------------------------
    # Recording API — called from inside CorrelationEngine.publish_incident
    # ------------------------------------------------------------------
    def record_frame(
        self,
        incident_id: str,
        triggering_event: Dict[str, Any],
        rule_name: Optional[str],
        kill_chain_steps: List[Dict[str, Any]],
        mitre_techniques: List[str],
        risk_snapshot: Dict[str, Any],
    ) -> Optional[str]:
        if not incident_id:
            return None

        seen_t = self._seen_techniques.setdefault(incident_id, set())
        seen_s = self._seen_services.setdefault(incident_id, set())

        new_techs = [t for t in mitre_techniques if t and t not in seen_t]
        seen_t.update(new_techs)

        services_in_chain = [
            s.get("service") for s in kill_chain_steps if isinstance(s, dict) and s.get("service")
        ]
        new_services = [s for s in services_in_chain if s and s not in seen_s]
        seen_s.update(new_services)

        frame = {
            "incident_id": incident_id,
            "frame_index": len(seen_s),         # not strictly the index, but stable
            "ts": time.time(),
            "rule": rule_name,
            "event": {
                "event_type": triggering_event.get("event_type"),
                "source_layer": triggering_event.get("source_layer"),
                "source_service_name": triggering_event.get("source_service_name"),
                "source_ip": (triggering_event.get("source_entity") or {}).get("ip"),
                "destination_service": triggering_event.get("destination_service"),
                "severity": triggering_event.get("severity"),
                "timestamp": triggering_event.get("timestamp"),
            },
            "delta": {
                "new_services": new_services,
                "new_techniques": new_techs,
            },
            "cumulative": {
                "service_path": list(services_in_chain),
                "mitre_techniques": list(seen_t),
                "step_count": len(kill_chain_steps),
            },
            "risk": risk_snapshot,
        }

        stream_key = f"{REPLAY_PREFIX}{incident_id}"
        try:
            stream_id: Optional[str] = None
            if self.bus is not None:
                stream_id = self.bus.publish_replay_frame(incident_id, frame)
            else:
                stream_id = self.redis.xadd(
                    name=stream_key,
                    fields={"payload": json.dumps(frame)},
                    maxlen=10000,
                    approximate=True,
                )
            # Index for the "list all replays" view
            self.redis.zadd(REPLAY_INDEX_KEY, {incident_id: frame["ts"]})
            try:
                self.redis.expire(stream_key, REPLAY_TTL_SECONDS)
            except Exception:
                pass
            return stream_id
        except Exception as exc:
            logger.debug("replay frame write failed: %s", exc)
            return None

    def forget(self, incident_id: str) -> None:
        """Drop in-memory dedup state when an incident closes / cools down."""
        self._seen_techniques.pop(incident_id, None)
        self._seen_services.pop(incident_id, None)
