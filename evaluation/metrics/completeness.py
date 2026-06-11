"""Kill chain completeness — Definition 12.7 (SECURISPHERE_RESEARCH_CONTEXT.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_ts(ts: str | None) -> datetime | None:
    """Parse ISO timestamp to naive datetime for comparison."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)
    except ValueError:
        return None


def _service_path(step: dict[str, Any]) -> tuple[str | None, str | None]:
    """Extract (source, destination) service names from a step dict."""
    src = (
        step.get("source_service_name")
        or step.get("service_name")
        or step.get("source")
    )
    dst = step.get("destination_service_name") or step.get("destination")
    return src, dst


def _paths_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """True when service attribution matches (Definition 12.7 equivalence)."""
    es, ed = _service_path(expected)
    as_, ad = _service_path(actual)
    if es and as_ and es != as_:
        return False
    if ed and ad and ed != ad:
        return False
    if expected.get("service_name") and actual.get("service_name"):
        if expected["service_name"] != actual["service_name"]:
            # Allow destination in expected to match service_name in actual
            if expected.get("destination_service_name") != actual.get("service_name"):
                return False
    return True


def _stage_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Match attack stage type when ground truth specifies it."""
    exp_stage = expected.get("attack_stage") or expected.get("stage")
    act_stage = actual.get("attack_stage") or actual.get("stage")
    if exp_stage and act_stage:
        return str(exp_stage).lower() == str(act_stage).lower()
    return True


def _type_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Match event_type when present in ground truth."""
    exp_type = expected.get("event_type")
    act_type = actual.get("event_type")
    if exp_type and act_type:
        return str(exp_type).lower() == str(act_type).lower()
    return True


def events_equivalent(
    actual: dict[str, Any],
    expected: dict[str, Any],
    *,
    timestamp_tolerance_sec: float = 30.0,
) -> bool:
    """Test event attribution equivalence (Definition 12.7).

    Args:
        actual: Reconstructed kill-chain step from PostgreSQL.
        expected: Ground-truth step from scenario YAML.
        timestamp_tolerance_sec: Max |Δt| for timestamp match.

    Returns:
        True if steps are equivalent under the formal definition.
    """
    if not _type_match(expected, actual):
        return False
    if not _paths_match(expected, actual):
        return False
    if not _stage_match(expected, actual):
        return False

    exp_ts = _parse_ts(expected.get("timestamp"))
    act_ts = _parse_ts(actual.get("timestamp"))
    if exp_ts and act_ts:
        delta = abs((act_ts - exp_ts).total_seconds())
        if delta > timestamp_tolerance_sec:
            return False
    return True


def _find_match(
    expected: dict[str, Any],
    actual_steps: list[dict[str, Any]],
    used: set[int],
    *,
    timestamp_tolerance_sec: float,
) -> int | None:
    """Return index of first unused actual step matching *expected*."""
    for idx, actual in enumerate(actual_steps):
        if idx in used:
            continue
        if events_equivalent(
            actual,
            expected,
            timestamp_tolerance_sec=timestamp_tolerance_sec,
        ):
            return idx
        # Relaxed match: event_type + service path without timestamp
        if _type_match(expected, actual) and _paths_match(expected, actual):
            if _stage_match(expected, actual):
                return idx
    return None


def evaluate_completeness(
    actual_steps: list[dict[str, Any]],
    expected_steps: list[dict[str, Any]],
    *,
    timestamp_tolerance_sec: float = 30.0,
) -> float:
    """Fraction of ground-truth steps present in the reconstructed chain.

    Args:
        actual_steps: Steps from ``kill_chains.steps`` (possibly merged).
        expected_steps: ``expected_kill_chain_steps`` from scenario YAML.
        timestamp_tolerance_sec: Timestamp equivalence window.

    Returns:
        Completeness score in [0.0, 1.0].
    """
    if not expected_steps:
        return 1.0 if not actual_steps else 0.0
    used: set[int] = set()
    hits = 0
    for expected in expected_steps:
        idx = _find_match(
            expected,
            actual_steps,
            used,
            timestamp_tolerance_sec=timestamp_tolerance_sec,
        )
        if idx is not None:
            used.add(idx)
            hits += 1
    return round(hits / len(expected_steps), 4)


def reconstruct_chain_log(
    actual_steps: list[dict[str, Any]],
    expected_steps: list[dict[str, Any]],
    *,
    timestamp_tolerance_sec: float = 30.0,
) -> list[dict[str, Any]]:
    """Build a per-step audit log for paper Table 5 / debugging.

    Args:
        actual_steps: Reconstructed steps.
        expected_steps: Ground-truth steps.
        timestamp_tolerance_sec: Timestamp tolerance.

    Returns:
        List of dicts with expected, matched (bool), matched_actual index.
    """
    used: set[int] = set()
    log: list[dict[str, Any]] = []
    for i, expected in enumerate(expected_steps):
        idx = _find_match(
            expected,
            actual_steps,
            used,
            timestamp_tolerance_sec=timestamp_tolerance_sec,
        )
        entry: dict[str, Any] = {
            "step_index": i,
            "expected": expected,
            "matched": idx is not None,
        }
        if idx is not None:
            used.add(idx)
            entry["matched_actual"] = actual_steps[idx]
        log.append(entry)
    return log
