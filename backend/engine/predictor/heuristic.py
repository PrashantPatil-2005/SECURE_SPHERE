"""Markov-baseline next-step predictor.

Reads historical kill chains from the ``kill_chains`` PG table (written by
``engine.kill_chain.reconstructor``), builds a stage-transition matrix, and
predicts the next likely stage + technique given the chain so far.

This is the *honest baseline* against which the TGNN must beat in the paper
— without it the TGNN's reported uplift is meaningless.
"""

from __future__ import annotations

import json
import logging
import math
import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("HeuristicPredictor")

# Rough MITRE-stage ordering used as a fallback when no historical data.
# Source: ATT&CK for Containers tactic ordering, simplified.
DEFAULT_STAGE_ORDER = [
    "reconnaissance", "initial_access", "execution", "persistence",
    "privilege_escalation", "defense_evasion", "credential_access",
    "discovery", "lateral_movement", "collection", "exfiltration", "impact",
]


class HeuristicPredictor:
    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client
        self._matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._technique_co: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._loaded = False

    # ------------------------------------------------------------------
    # Training (offline — runs at engine boot or via /engine/predictor/refit)
    # ------------------------------------------------------------------
    def fit_from_postgres(self) -> int:
        """Build transition counts from ``kill_chains`` table. Returns the
        number of chains it ingested."""
        try:
            from common.db import conn_ctx  # type: ignore
        except Exception:
            try:
                from engine.common.db import conn_ctx  # type: ignore
            except Exception:
                logger.debug("PG context unavailable; skipping fit")
                return 0

        n = 0
        try:
            with conn_ctx() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT kill_chain_steps, mitre_techniques FROM kill_chains "
                    "ORDER BY detected_at DESC LIMIT 5000"
                )
                rows = cur.fetchall()
                for steps_raw, techniques_raw in rows:
                    steps = self._coerce_list(steps_raw)
                    techs = self._coerce_list(techniques_raw)
                    self._ingest_chain(steps, techs)
                    n += 1
                cur.close()
        except Exception as exc:
            logger.debug("HeuristicPredictor.fit_from_postgres failed: %s", exc)
            return 0
        self._loaded = True
        return n

    @staticmethod
    def _coerce_list(value) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except Exception:
                return []
        return []

    def _ingest_chain(self, steps: List[Any], techniques: List[Any]) -> None:
        stages = [self._stage_of(s) for s in steps if s]
        stages = [s for s in stages if s]
        for prev, nxt in zip(stages, stages[1:]):
            self._matrix[prev][nxt] += 1
        # Technique co-occurrence within the same chain
        for i, ti in enumerate(techniques):
            for tj in techniques[i + 1:]:
                if ti and tj and ti != tj:
                    self._technique_co[ti][tj] += 1
                    self._technique_co[tj][ti] += 1

    @staticmethod
    def _stage_of(step: Any) -> Optional[str]:
        if isinstance(step, dict):
            return (step.get("stage") or step.get("tactic") or "").lower() or None
        if isinstance(step, str):
            return step.lower()
        return None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def predict_next_stage(self, current_stage: str, top_k: int = 3) -> List[Tuple[str, float]]:
        current_stage = (current_stage or "").lower()
        row = self._matrix.get(current_stage)
        if row:
            total = float(sum(row.values()))
            ranked = sorted(
                ((s, c / total) for s, c in row.items()), key=lambda x: -x[1]
            )
            return ranked[:top_k]

        # Fallback: take the next stage in the canonical order.
        try:
            i = DEFAULT_STAGE_ORDER.index(current_stage)
            tail = DEFAULT_STAGE_ORDER[i + 1:i + 1 + top_k]
            return [(s, 1.0 / max(1, len(tail))) for s in tail]
        except ValueError:
            return []

    def predict_next_techniques(
        self, observed_techniques: List[str], top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Score MITRE techniques by their co-occurrence with the observed
        ones. Effectively a neighbour-vote in the technique graph."""
        if not observed_techniques:
            return []
        scores: Dict[str, float] = defaultdict(float)
        seen = set(observed_techniques)
        for t in observed_techniques:
            row = self._technique_co.get(t, {})
            row_total = float(sum(row.values())) or 1.0
            for other, c in row.items():
                if other in seen:
                    continue
                scores[other] += c / row_total
        # Length-normalise so chains of different lengths are comparable.
        norm = max(1, len(observed_techniques))
        ranked = sorted(
            ((tech, s / norm) for tech, s in scores.items()), key=lambda x: -x[1]
        )
        return ranked[:top_k]

    def predict(
        self, current_stage: str, observed_techniques: List[str]
    ) -> Dict[str, Any]:
        """Single-call API used by the engine's /engine/predict-next route."""
        return {
            "current_stage": current_stage,
            "next_stages": [
                {"stage": s, "probability": round(p, 4)}
                for s, p in self.predict_next_stage(current_stage)
            ],
            "next_techniques": [
                {"technique": t, "score": round(p, 4)}
                for t, p in self.predict_next_techniques(observed_techniques)
            ],
            "model": "markov-heuristic",
            "trained_on": sum(sum(row.values()) for row in self._matrix.values()),
        }
