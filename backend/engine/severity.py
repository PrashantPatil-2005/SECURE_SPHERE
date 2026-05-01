"""
severity.py — Canonical severity resolver shared by the correlation engine
and the API layer.

Thresholds align with the README risk-score buckets:
    Normal      0  – 30   → "low"
    Suspicious  31 – 70   → "medium"
    Threatening 71 – 150  → "high"
    Critical    > 150     → "critical"

Two additional rules apply on top of the score thresholds:
  • Confirmed kill chains (step_count >= 2) are floored at "high" — a
    multi-stage correlation is never "low" or "medium" by definition.
  • A handful of high-impact MITRE techniques force "critical" regardless
    of risk score (privilege escalation, valid accounts, exfiltration,
    credential dumping, container escape).

Keep the resolver pure (no DB, no logging) so it stays trivially testable
and importable from any layer.
"""
from __future__ import annotations

from typing import Iterable, Optional

# Severity ordering for "max(input, computed)" merging.
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
VALID_SEVERITIES = ("low", "medium", "high", "critical")

# MITRE techniques whose mere presence in a kill chain warrants "critical".
CRITICAL_TECHNIQUES = frozenset({
    "T1068",   # Exploitation for Privilege Escalation
    "T1078",   # Valid Accounts
    "T1041",   # Exfiltration Over C2 Channel
    "T1003",   # OS Credential Dumping
    "T1611",   # Escape to Host (container escape)
})


def resolve_incident_severity(
    risk_score: float,
    step_count: int,
    technique_ids: Optional[Iterable[str]] = None,
) -> str:
    """Return one of 'low', 'medium', 'high', 'critical'.

    Args:
        risk_score:  Current risk score for the source entity at the time
                     the incident was created. Negative values clamp to 0.
        step_count:  Number of kill-chain steps reconstructed for this
                     incident. ``>= 2`` floors severity at 'high'.
        technique_ids: Iterable of MITRE technique IDs associated with the
                     incident. Presence of any technique in
                     ``CRITICAL_TECHNIQUES`` forces 'critical'.
    """
    score = max(0.0, float(risk_score or 0))
    steps = int(step_count or 0)
    techs = set(technique_ids or [])

    if techs & CRITICAL_TECHNIQUES:
        return "critical"
    if score > 150:
        return "critical"
    if score > 70 or steps >= 2:
        return "high"
    if score > 30:
        return "medium"
    return "low"


def floor_severity(current: Optional[str], minimum: str) -> str:
    """Return whichever of ``current`` and ``minimum`` is more severe."""
    cur = SEVERITY_ORDER.get((current or "").lower(), -1)
    minv = SEVERITY_ORDER.get((minimum or "low").lower(), 0)
    if cur >= minv:
        return current  # type: ignore[return-value]
    return minimum
