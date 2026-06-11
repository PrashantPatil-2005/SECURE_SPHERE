"""Unit tests for Brier score (Definition 12.9)."""

from __future__ import annotations

import unittest

from evaluation.metrics.brier import brier_score, reliability_diagram


class TestBrier(unittest.TestCase):
    def test_perfect_calibration(self) -> None:
        preds = [1.0, 0.0, 1.0, 0.0]
        labels = [1, 0, 1, 0]
        self.assertEqual(brier_score(preds, labels), 0.0)

    def test_worst_case(self) -> None:
        preds = [0.0, 1.0]
        labels = [1, 0]
        self.assertEqual(brier_score(preds, labels), 1.0)

    def test_reliability_buckets(self) -> None:
        preds = [0.1, 0.2, 0.9, 0.95]
        labels = [0, 0, 1, 1]
        buckets = reliability_diagram(preds, labels, n_buckets=10)
        self.assertEqual(len(buckets), 10)
        self.assertGreater(buckets[9]["count"], 0)


if __name__ == "__main__":
    unittest.main()
