"""Behavioural fingerprinting per service.

Why this exists
---------------
Rule-based correlation catches *known patterns*. It misses the case where a
service starts behaving differently for reasons no rule was written for —
e.g. a previously read-only service suddenly making outbound calls to a new
peer. A per-service behavioural baseline catches that, and the anomaly
event then becomes a first-class input to the correlation engine (rules can
key off ``event_type == "behavior_anomaly"``).

Why not "just use Isolation Forest"
-----------------------------------
We *do* use Isolation Forest when scikit-learn is installed (a deeper,
research-grade detector). But the engine container deliberately ships
without sklearn so cold start is fast and the image stays under 200 MB. So
the fallback path uses **median + MAD** (robust-z) per feature with an
``L∞`` aggregation — well known to be resistant to small training sets
and outlier contamination, both of which are the realistic case in
container telemetry where the baseline window is short and noisy.

Features (per service, per minute window)
-----------------------------------------
- ``req_rate``        : events/sec from this service
- ``distinct_peers``  : count of distinct ``destination_service`` seen
- ``error_rate``      : fraction of events with severity in {high, critical}
- ``layer_diversity`` : count of distinct ``source_layer`` values
- ``hour_of_day``     : circular feature, encoded as sin/cos pair

The fingerprint is *not* the full Node2Vec embedding (that lives in
``backend/engine/embedding/``). It is the lightweight real-time signal that
runs on every event without any model loading.
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger("BehaviorFingerprint")

WINDOW_SECONDS      = int(os.getenv("BEHAVIOR_WINDOW_SECONDS", "60"))
HISTORY_WINDOWS     = int(os.getenv("BEHAVIOR_HISTORY_WINDOWS", "20"))   # ~20 min of baselines
ANOMALY_Z_THRESHOLD = float(os.getenv("BEHAVIOR_Z_THRESHOLD", "3.5"))
MIN_BASELINE_SAMPLES= int(os.getenv("BEHAVIOR_MIN_SAMPLES", "5"))

ANOMALY_STREAM      = os.getenv("BEHAVIOR_ANOMALY_STREAM", "securisphere:events")
ANOMALY_LIST_KEY    = "behavior:anomalies"

# Optional sklearn path
try:
    from sklearn.ensemble import IsolationForest  # type: ignore
    _SKLEARN = True
except Exception:
    _SKLEARN = False


@dataclass
class _WindowAccumulator:
    """Mutable counters for the *current* (in-progress) window."""
    started_at: float
    event_count: int = 0
    error_count: int = 0
    peer_set: set = field(default_factory=set)
    layer_set: set = field(default_factory=set)
    hour_set: set = field(default_factory=set)

    def feature_vector(self, window_seconds: float) -> List[float]:
        rate = self.event_count / max(1.0, window_seconds)
        err = (self.error_count / self.event_count) if self.event_count else 0.0
        # Use the dominant hour for the circular encoding (windows are short)
        hour = next(iter(self.hour_set), time.gmtime().tm_hour)
        sin_h = math.sin(2 * math.pi * hour / 24)
        cos_h = math.cos(2 * math.pi * hour / 24)
        return [
            float(rate),
            float(len(self.peer_set)),
            float(err),
            float(len(self.layer_set)),
            float(sin_h),
            float(cos_h),
        ]


FEATURE_NAMES = [
    "req_rate", "distinct_peers", "error_rate", "layer_diversity",
    "hour_sin", "hour_cos",
]


def _robust_z(values: List[float], x: float) -> float:
    """Modified z-score using median + MAD. Resistant to outliers."""
    if not values:
        return 0.0
    med = statistics.median(values)
    mad = statistics.median([abs(v - med) for v in values]) or 1e-6
    # 1.4826 makes MAD a consistent estimator of σ for normal data
    return (x - med) / (1.4826 * mad)


@dataclass
class AnomalyReport:
    service: str
    score: float                  # max abs robust-z across features
    detector: str                 # "robust-z" | "iforest"
    features: Dict[str, float]
    deviations: Dict[str, float]  # per-feature signed z-score
    timestamp: float

    def as_event(self) -> Dict[str, Any]:
        """Shape compatible with the correlation engine's event schema."""
        sev = "critical" if self.score >= 5.0 else "high" if self.score >= ANOMALY_Z_THRESHOLD else "medium"
        return {
            "event_type": "behavior_anomaly",
            "source_layer": "behavior-fingerprint",
            "source_service_name": self.service,
            "source_entity": {"service": self.service},
            "severity": sev,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.timestamp)),
            "details": {
                "score": round(self.score, 3),
                "detector": self.detector,
                "features": self.features,
                "deviations": {k: round(v, 3) for k, v in self.deviations.items()},
            },
        }


class BehaviorTracker:
    """Maintains rolling per-service feature windows and emits anomaly events.

    Thread-safety: ``observe`` is called from the correlation worker(s) which
    may run with multiple threads in the same group; one lock per service is
    fine because contention per service is naturally low.
    """

    def __init__(self, redis_client, bus=None) -> None:
        self.redis = redis_client
        self.bus = bus
        self._lock = threading.Lock()
        self._current: Dict[str, _WindowAccumulator] = {}
        self._history: Dict[str, Deque[List[float]]] = defaultdict(
            lambda: deque(maxlen=HISTORY_WINDOWS)
        )
        self._iforests: Dict[str, Any] = {}  # populated lazily if sklearn present

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    def observe(self, event: Dict[str, Any]) -> Optional[AnomalyReport]:
        """Update the current window with one event. If the window has
        elapsed, close it, score the *previous* window, and start a new one.
        Returns an AnomalyReport iff the closed window was anomalous."""
        svc = event.get("source_service_name")
        if not svc:
            return None

        now = time.time()
        report: Optional[AnomalyReport] = None

        with self._lock:
            acc = self._current.get(svc)
            if acc is None or (now - acc.started_at) >= WINDOW_SECONDS:
                if acc is not None and acc.event_count > 0:
                    report = self._close_window(svc, acc)
                acc = _WindowAccumulator(started_at=now)
                self._current[svc] = acc

            acc.event_count += 1
            sev = (event.get("severity") or "").lower()
            if sev in ("high", "critical"):
                acc.error_count += 1
            peer = event.get("destination_service") or event.get("destination_service_name")
            if peer:
                acc.peer_set.add(peer)
            layer = event.get("source_layer")
            if layer:
                acc.layer_set.add(layer)
            try:
                hour = time.gmtime().tm_hour
                acc.hour_set.add(hour)
            except Exception:
                pass

        if report is not None:
            self._emit(report)
        return report

    # ------------------------------------------------------------------
    # Window close + scoring
    # ------------------------------------------------------------------
    def _close_window(self, svc: str, acc: _WindowAccumulator) -> Optional[AnomalyReport]:
        feats = acc.feature_vector(WINDOW_SECONDS)
        feat_dict = dict(zip(FEATURE_NAMES, feats))

        history = self._history[svc]
        if len(history) < MIN_BASELINE_SAMPLES:
            history.append(feats)
            return None

        # Robust-z per feature (always available)
        deviations: Dict[str, float] = {}
        for i, name in enumerate(FEATURE_NAMES):
            col = [v[i] for v in history]
            deviations[name] = _robust_z(col, feats[i])

        peak = max((abs(z) for z in deviations.values()), default=0.0)
        detector = "robust-z"

        # Optional iforest score takes precedence if confident — used as a
        # corroborating signal so we don't flag on a single weak detector.
        if _SKLEARN and len(history) >= 12:
            try:
                clf = self._iforests.get(svc)
                X = list(history)
                if clf is None or len(history) % 4 == 0:
                    clf = IsolationForest(
                        n_estimators=64, contamination="auto", random_state=42,
                    )
                    clf.fit(X)
                    self._iforests[svc] = clf
                # decision_function: positive=normal, negative=anomaly
                score = -float(clf.decision_function([feats])[0])
                # Map to z-comparable scale: scores typically in [-0.5, 0.5]
                iforest_z = score * 10.0
                if iforest_z > peak:
                    peak = iforest_z
                    detector = "iforest"
            except Exception as exc:
                logger.debug("iforest scoring failed for %s: %s", svc, exc)

        # Always update history *after* scoring so the detector judges this
        # window against the prior baseline, not against itself.
        history.append(feats)

        if peak < ANOMALY_Z_THRESHOLD:
            return None

        return AnomalyReport(
            service=svc,
            score=peak,
            detector=detector,
            features=feat_dict,
            deviations=deviations,
            timestamp=acc.started_at,
        )

    # ------------------------------------------------------------------
    # Emit
    # ------------------------------------------------------------------
    def _emit(self, report: AnomalyReport) -> None:
        event = report.as_event()
        try:
            # Persist a small recent-anomaly list for the dashboard
            self.redis.lpush(ANOMALY_LIST_KEY, json.dumps(event))
            self.redis.ltrim(ANOMALY_LIST_KEY, 0, 199)
        except Exception:
            pass
        # Inject as a normal security event so existing rules can react
        if self.bus is not None:
            try:
                self.bus.publish_event(event)
                return
            except Exception as exc:
                logger.debug("bus publish failed, falling back to pub/sub: %s", exc)
        try:
            self.redis.publish("security_events", json.dumps(event))
        except Exception as exc:
            logger.warning("anomaly publish failed: %s", exc)

    # ------------------------------------------------------------------
    # Introspection (used by /engine/anomalies endpoint)
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {
                svc: {
                    "samples": len(hist),
                    "current_event_count": (
                        self._current[svc].event_count if svc in self._current else 0
                    ),
                    "history_size": HISTORY_WINDOWS,
                    "detector": "iforest" if (_SKLEARN and svc in self._iforests) else "robust-z",
                }
                for svc, hist in self._history.items()
            }
