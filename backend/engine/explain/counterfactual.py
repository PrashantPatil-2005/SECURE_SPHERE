"""Counterfactual explainer: "if event X were missing, would chain still fire?"

The point isn't to convince a model — it's to surface for an analyst the
*pivotal* events in a chain: the ones that, if removed, drop the
posterior confidence below the alert threshold. Those are the events
worth investigating first; everything else is corroborating evidence.

This is intentionally analytical, not ML — we re-score the chain with
each step removed and report the deltas. Fast, reproducible, no training
required.
"""

from __future__ import annotations

from typing import Any, Dict, List

from confidence.bayesian import score_chain  # type: ignore


ALERT_THRESHOLD = 0.65


def explain_chain(kill_chain_steps: List[Dict[str, Any]], base_rate: float = 0.05) -> Dict[str, Any]:
    if not kill_chain_steps:
        return {"baseline": None, "removed": [], "pivotal_steps": []}

    baseline = score_chain(kill_chain_steps, base_rate=base_rate)

    removed_reports: List[Dict[str, Any]] = []
    pivotal: List[int] = []
    for i in range(len(kill_chain_steps)):
        without = kill_chain_steps[:i] + kill_chain_steps[i + 1:]
        if not without:
            continue
        report = score_chain(without, base_rate=base_rate)
        delta = baseline.posterior - report.posterior
        crossed_threshold = (
            baseline.posterior >= ALERT_THRESHOLD and report.posterior < ALERT_THRESHOLD
        )
        if crossed_threshold:
            pivotal.append(i)
        removed_reports.append({
            "removed_index":     i,
            "removed_stage":     kill_chain_steps[i].get("stage") if isinstance(kill_chain_steps[i], dict) else None,
            "removed_service":   kill_chain_steps[i].get("service") if isinstance(kill_chain_steps[i], dict) else None,
            "posterior_without": round(report.posterior, 4),
            "delta":             round(delta, 4),
            "crossed_threshold": crossed_threshold,
        })

    return {
        "baseline":       baseline.to_dict(),
        "removed":        removed_reports,
        "pivotal_steps":  pivotal,
        "alert_threshold": ALERT_THRESHOLD,
        "interpretation": (
            "Pivotal steps are the indices whose removal drops the chain "
            "below the alert threshold — investigate them first."
        ),
    }
