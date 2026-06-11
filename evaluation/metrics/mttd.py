"""MTTD helpers — Definition 12.10."""

from __future__ import annotations

from typing import Any


def mean_mttd_seconds(chains: list[dict[str, Any]]) -> float | None:
    """Mean engine-level MTTD across kill-chain rows.

    Args:
        chains: Rows from PostgreSQL with ``mttd_seconds`` field.

    Returns:
        Mean MTTD in seconds, or None if no valid values.
    """
    values = [
        float(c["mttd_seconds"])
        for c in chains
        if c.get("mttd_seconds") is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 4)
