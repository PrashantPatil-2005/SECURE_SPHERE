"""Brier score and reliability diagram — Definitions 12.8–12.9."""

from __future__ import annotations

from typing import Any


def brier_score(predictions: list[float], labels: list[int]) -> float:
    """Compute Brier score BS = (1/N) Σ (p̂_i − y_i)².

    Args:
        predictions: Predicted probabilities in [0, 1].
        labels: Ground-truth binary labels (0 = benign, 1 = attack).

    Returns:
        Brier score; lower is better.

    Raises:
        ValueError: If lengths differ or N == 0.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    if not predictions:
        raise ValueError("empty trial set")
    total = sum((float(p) - int(y)) ** 2 for p, y in zip(predictions, labels))
    return round(total / len(predictions), 6)


def reliability_diagram(
    predictions: list[float],
    labels: list[int],
    *,
    n_buckets: int = 10,
) -> list[dict[str, Any]]:
    """Bin predictions into confidence buckets for calibration plots.

    Args:
        predictions: Predicted probabilities.
        labels: Binary ground truth.
        n_buckets: Number of equal-width buckets on [0, 1].

    Returns:
        List of bucket dicts with bucket_lo, bucket_hi, mean_conf,
        frac_positive, count.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must have the same length")
    buckets: list[dict[str, Any]] = []
    width = 1.0 / n_buckets
    for b in range(n_buckets):
        lo = round(b * width, 4)
        hi = round((b + 1) * width, 4)
        in_bucket = [
            (p, y)
            for p, y in zip(predictions, labels)
            if (lo <= p < hi) or (b == n_buckets - 1 and p == 1.0)
        ]
        if not in_bucket:
            buckets.append({
                "bucket_lo": lo,
                "bucket_hi": hi,
                "mean_conf": None,
                "frac_positive": None,
                "count": 0,
            })
            continue
        ps = [p for p, _ in in_bucket]
        ys = [y for _, y in in_bucket]
        buckets.append({
            "bucket_lo": lo,
            "bucket_hi": hi,
            "mean_conf": round(sum(ps) / len(ps), 4),
            "frac_positive": round(sum(ys) / len(ys), 4),
            "count": len(in_bucket),
        })
    return buckets
