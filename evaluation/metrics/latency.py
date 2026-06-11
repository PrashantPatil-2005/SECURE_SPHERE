"""Latency percentile helpers for throughput benchmarks."""

from __future__ import annotations


def percentile_ms(samples: list[float], p: float) -> float:
    """Compute percentile of latency samples in milliseconds.

    Args:
        samples: Latency values in milliseconds.
        p: Percentile in (0, 100] (e.g. 50, 95, 99).

    Returns:
        Percentile value, or 0.0 if *samples* is empty.
    """
    if not samples:
        return 0.0
    ordered = sorted(samples)
    if p <= 0:
        return round(ordered[0], 3)
    if p >= 100:
        return round(ordered[-1], 3)
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return round(ordered[f], 3)
    return round(ordered[f] + (k - f) * (ordered[c] - ordered[f]), 3)
