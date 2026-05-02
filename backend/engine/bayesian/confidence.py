"""Bayesian confidence scoring for SecuriSphere incidents.

Why this exists
---------------
Rules fire on pattern matches but a pattern match alone does not say "this
is a real attack" with calibrated confidence. The dashboard analyst wants a
single number — "how sure are you?" — and downstream automation (auto-
suppression, paging escalation) needs that number to be principled rather
than a hand-waved hard-coded 0.92.

Approach
--------
A naive-Bayes-style log-odds combiner. We treat each evidence channel
(severity peak, corroborating-event count, distinct MITRE-technique count,
rule-specific prior) as a conditionally independent indicator of "this
incident is a true positive". For each indicator we map the observed value
to a likelihood-ratio (LR) and accumulate ``log(LR)``; the final posterior
is ``sigmoid(prior_logit + sum_log_lr)``.

This is intentionally not a trained model:
- We have no labelled "TP vs FP" corpus in this repo.
- The combiner stays interpretable — every contribution is logged on the
  incident as ``confidence_breakdown`` so an analyst can see *why* the
  score landed where it did.

Returned shape
--------------
``score_incident`` returns ``(posterior_float_in_0_1, breakdown_dict)``.
The engine writes both onto the incident under ``confidence`` and
``confidence_breakdown`` so the dashboard / explain layer can surface them.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("BayesianConfidence")


# Rule-type priors. Rules where false positives are common (rate-abuse,
# port-scan from a single IP) get a lower prior; rules whose patterns are
# almost always intentional (sql-injection payload, lateral-movement chain)
# get a higher one. These are deliberately conservative — the evidence
# multipliers below do most of the work.
DEFAULT_PRIOR = 0.55
RULE_PRIOR: Dict[str, float] = {
    "brute_force":            0.70,
    "credential_stuffing":    0.78,
    "sql_injection":          0.92,
    "path_traversal":         0.88,
    "privilege_escalation":   0.90,
    "lateral_movement":       0.85,
    "data_exfiltration":      0.80,
    "account_pivot":          0.82,
    "supply_chain_drift":     0.65,
    "rate_abuse":             0.45,
    "endpoint_enumeration":   0.50,
    "behavior_anomaly":       0.55,
    "port_scan":              0.40,
    "dns_tunneling":          0.78,
}

# Evidence-channel weights (in log-odds nats). Tuned so a "single
# medium-severity event with one MITRE tag" comes out near the rule prior,
# while "five high-severity events spanning three MITRE techniques" lands
# above 0.95.
SEVERITY_LR: Dict[str, float] = {
    "critical": 1.6,
    "high":     0.9,
    "medium":   0.0,
    "low":      -0.6,
    "info":     -0.9,
}


def _logit(p: float) -> float:
    p = max(min(p, 1 - 1e-9), 1e-9)
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _step_count_lr(n: int) -> float:
    """Smooth saturating bonus for corroborating events.

    1 step  → 0.0
    2 steps → +0.4
    3 steps → +0.7
    5 steps → +1.1
    8+      → +1.4
    """
    if n <= 1:
        return 0.0
    return 1.4 * (1 - math.exp(-(n - 1) / 2.5))


def _mitre_count_lr(n: int) -> float:
    """Bonus for spanning multiple MITRE techniques. Multi-technique chains
    are very rarely false positives because each technique is an
    independent matcher."""
    if n <= 1:
        return 0.0
    return 0.55 * math.log(1 + n)


def _peak_severity(steps: List[Dict[str, Any]], fallback: str) -> str:
    order = ["info", "low", "medium", "high", "critical"]
    seen = [s.get("severity") for s in steps if isinstance(s, dict)]
    seen = [s for s in seen if s in order]
    if not seen:
        return fallback if fallback in order else "medium"
    return max(seen, key=order.index)


class BayesianConfidence:
    """Stateless scorer. Held on the engine so callers can swap priors at
    runtime via ``self.engine.bayes.priors[rule] = ...`` for ablation tests."""

    def __init__(self) -> None:
        self.priors: Dict[str, float] = dict(RULE_PRIOR)
        self.default_prior: float = DEFAULT_PRIOR

    def score(self, incident: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        return score_incident(incident, priors=self.priors, default=self.default_prior)


def score_incident(
    incident: Dict[str, Any],
    *,
    priors: Dict[str, float] = None,
    default: float = DEFAULT_PRIOR,
) -> Tuple[float, Dict[str, Any]]:
    """Return ``(posterior, breakdown)`` for one incident.

    ``incident`` only needs ``incident_type``, ``severity``,
    ``kill_chain_steps``, and ``mitre_techniques`` — all of which the
    engine already populates before publish.
    """
    priors = priors or RULE_PRIOR

    rule = incident.get("incident_type") or "unknown"
    prior = float(priors.get(rule, default))

    steps = incident.get("kill_chain_steps") or []
    techniques = incident.get("mitre_techniques") or []
    sev = _peak_severity(steps, incident.get("severity", "medium"))

    log_lr_sev = SEVERITY_LR.get(sev, 0.0)
    log_lr_steps = _step_count_lr(len(steps))
    log_lr_mitre = _mitre_count_lr(len(techniques))

    logit = _logit(prior) + log_lr_sev + log_lr_steps + log_lr_mitre
    posterior = _sigmoid(logit)

    breakdown = {
        "rule":                rule,
        "prior":               round(prior, 3),
        "peak_severity":       sev,
        "log_lr_severity":     round(log_lr_sev, 3),
        "log_lr_step_count":   round(log_lr_steps, 3),
        "log_lr_mitre":        round(log_lr_mitre, 3),
        "step_count":          len(steps),
        "mitre_count":         len(techniques),
        "posterior_logit":     round(logit, 3),
        "posterior":           round(posterior, 4),
    }
    return posterior, breakdown
