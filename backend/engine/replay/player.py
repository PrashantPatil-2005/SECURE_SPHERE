"""Read replay frames from Redis and serve them to the dashboard / CLI."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("ReplayPlayer")

REPLAY_PREFIX = os.getenv("SECURISPHERE_REPLAY_PREFIX", "securisphere:replay:")
REPLAY_INDEX_KEY = "securisphere:replay:index"


class ReplayPlayer:
    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    def list_replays(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most-recent ``limit`` incidents that have replay
        frames, newest first."""
        try:
            entries = self.redis.zrevrange(REPLAY_INDEX_KEY, 0, limit - 1, withscores=True)
        except Exception:
            return []
        out = []
        for incident_id, ts in entries:
            out.append({"incident_id": incident_id, "first_frame_ts": float(ts)})
        return out

    def frames(self, incident_id: str) -> List[Dict[str, Any]]:
        """All frames for an incident, in chronological order. Each entry
        contains the original ``stream_id`` so the dashboard can resume
        playback after a refresh."""
        stream_key = f"{REPLAY_PREFIX}{incident_id}"
        try:
            raw = self.redis.xrange(stream_key, min="-", max="+")
        except Exception as exc:
            logger.debug("xrange replay failed: %s", exc)
            return []
        out: List[Dict[str, Any]] = []
        for stream_id, fields in raw or []:
            payload = fields.get("payload") if isinstance(fields, dict) else None
            if not payload:
                continue
            try:
                frame = json.loads(payload)
            except Exception:
                continue
            frame["stream_id"] = stream_id
            out.append(frame)
        return out

    def reconstruct_at(self, incident_id: str, step: int) -> Optional[Dict[str, Any]]:
        """Return the cumulative state at frame index ``step``. Used by the
        scrub-bar so the user can jump to any moment without replaying from
        zero."""
        all_frames = self.frames(incident_id)
        if not all_frames:
            return None
        step = max(0, min(step, len(all_frames) - 1))
        frame = all_frames[step]
        return {
            "incident_id": incident_id,
            "step": step,
            "total_steps": len(all_frames),
            "at": frame.get("ts"),
            "cumulative": frame.get("cumulative", {}),
            "current_event": frame.get("event"),
            "rule": frame.get("rule"),
        }

    def stream_after(
        self, incident_id: str, after_stream_id: str = "0", count: int = 64
    ) -> List[Dict[str, Any]]:
        """Resume playback past ``after_stream_id`` — used by the SSE
        endpoint so the dashboard can attach mid-attack."""
        stream_key = f"{REPLAY_PREFIX}{incident_id}"
        try:
            entries = self.redis.xread({stream_key: after_stream_id}, count=count, block=0)
        except Exception:
            return []
        out: List[Dict[str, Any]] = []
        for _stream, msgs in entries or []:
            for stream_id, fields in msgs:
                raw = fields.get("payload") if isinstance(fields, dict) else None
                if not raw:
                    continue
                try:
                    frame = json.loads(raw)
                    frame["stream_id"] = stream_id
                    out.append(frame)
                except Exception:
                    continue
        return out
