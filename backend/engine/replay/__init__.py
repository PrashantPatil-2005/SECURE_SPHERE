"""Attack Replay Engine — turn a kill chain into a scrubbable timeline.

Frames are written to the per-incident Redis Stream
``securisphere:replay:{incident_id}`` by the correlation engine as the
incident takes shape, then read back by the dashboard "Threat Cinema" view
or the CLI's ``securisphere replay <id>`` command.

The replay is *deterministic* — the same incident produces the same frame
sequence — so it's safe to use as a regression fixture for rule changes:
diffing today's frames against yesterday's catches rule drift.
"""
from .recorder import ReplayRecorder
from .player import ReplayPlayer

__all__ = ["ReplayRecorder", "ReplayPlayer"]
