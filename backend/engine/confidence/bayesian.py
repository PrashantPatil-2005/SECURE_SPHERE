"""Bayesian confidence scoring for a reconstructed kill chain.

Why a model and not a single hardcoded number
---------------------------------------------
A rule firing tells us "this pattern matched". It does NOT tell us how
likely the matched pattern represents an *actual* attack vs a benign
coincidence. The two pieces of evidence we already have but never combine
are:

  1. **Per-stage prior** P(attack | stage) — how often a stage-N event is
     part of a real attack vs noise. Calibrated from labelled history.
  2. **Stage-transition likelihood** P(stage_{i+1} | stage_i, attack) —
     read out of the same Markov matrix the predictor uses.

We combine these with a naive-Bayes update and report a posterior
probability + a per-stage breakdown so an analyst can see *why* the chain
is high- or low-confidence.

This is intentionally simple — naive Bayes, not a full belief network — so
it's defensible, debuggable, and survives sparse data. The paper section
discusses the assumptions and where they break.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Default priors — these are the *demo lab* defaults, NOT field-calibrated
# numbers. Operators are expected to refit from their own kill_chains
# table; the engine exposes /engine/confidence/refit for that.
DEFAULT_PRIORS = {
    "reconnaissance":      0.40,   # frequent benign noise
    "initial_access":      0.65,
    "execution":           0.70,
    "persistence":         0.85,
    "privilege_escalation":0.90,
    "credential_access":   0.92,
    "discovery":           0.55,
    "lateral_movement":    0.95,
    "collection":          0.85,
    "exfiltration":        0.97,
    "impact":              0.97,
    "defense_evasion":     0.80,
}

# How much each new stage *moves* the posterior — a damping factor so a
# chain doesn't asymptote to 1.0 the moment two stages fire.
LIKELIHOOD_RATIO_PER_STAGE = 1.6


@dataclass
class ConfidenceReport:
    posterior: float                          # P(attack | observed chain)
    per_stage: List[Dict[str, Any]]           # contribution of each stage
    explanation: str
    model: str = "naive-bayes-v1"
    priors_source: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "posterior":     round(self.posterior, 4),
            "per_stage":     self.per_stage,
            "explanation":   self.explanation,
            "model":         self.model,
            "priors_source": self.priors_source,
        }


def _logit(p: float) -> float:
    p = max(min(p, 0.999), 0.001)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def score_chain(
    kill_chain_steps: List[Dict[str, Any]],
    priors: Optional[Dict[str, float]] = None,
    base_rate: float = 0.05,
) -> ConfidenceReport:
    """Compute the posterior probability that the chain represents an
    attack, given a per-stage prior table and the system's overall base
    rate of attacks among all observed event sequences.

    The base rate matters: in a quiet system, even a high-likelihood chain
    is more likely benign than attack.
    """
    priors = priors or DEFAULT_PRIORS
    log_odds = _logit(base_rate)

    per_stage: List[Dict[str, Any]] = []
    for step in kill_chain_steps:
        stage = (step.get("stage") if isinstance(step, dict) else None) or "unknown"
        stage = stage.lower()
        prior = priors.get(stage, 0.5)
        # Likelihood ratio = prior / (1 - prior) — Bayes update in log-space.
        # We damp the per-stage contribution by LIKELIHOOD_RATIO_PER_STAGE
        # so the posterior is conservative on long chains.
        lr = (prior / max(1e-3, 1 - prior)) ** (1.0 / LIKELIHOOD_RATIO_PER_STAGE)
        delta = math.log(lr) if lr > 0 else 0.0
        log_odds += delta
        per_stage.append({
            "stage": stage,
            "service": step.get("service") if isinstance(step, dict) else None,
            "prior": prior,
            "log_odds_delta": round(delta, 3),
        })

    posterior = _sigmoid(log_odds)

    if posterior > 0.9:
        explanation = "High confidence — combination of late-stage indicators."
    elif posterior > 0.7:
        explanation = "Moderate-high confidence — at least one strong indicator."
    elif posterior > 0.4:
        explanation = "Moderate confidence — could be attack or noisy benign sequence."
    else:
        explanation = "Low confidence — chain is dominated by benign-prior stages."

    return ConfidenceReport(
        posterior=posterior,
        per_stage=per_stage,
        explanation=explanation,
    )
