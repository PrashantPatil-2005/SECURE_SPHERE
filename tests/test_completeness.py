"""Unit tests for kill chain completeness (Definition 12.7)."""

from __future__ import annotations

import unittest

from evaluation.metrics.completeness import (
    evaluate_completeness,
    events_equivalent,
    reconstruct_chain_log,
)


class TestCompleteness(unittest.TestCase):
    def test_full_match(self) -> None:
        expected = [
            {"event_type": "port_scan", "source_service_name": "a", "destination_service_name": "b"},
            {"event_type": "brute_force", "source_service_name": "a", "destination_service_name": "auth"},
        ]
        actual = [
            {"event_type": "port_scan", "service_name": "a", "destination_service_name": "b"},
            {"event_type": "brute_force", "service_name": "a", "destination_service_name": "auth"},
        ]
        self.assertEqual(evaluate_completeness(actual, expected), 1.0)

    def test_partial_match(self) -> None:
        expected = [
            {"event_type": "port_scan", "source_service_name": "a", "destination_service_name": "b"},
            {"event_type": "data_exfiltration", "source_service_name": "a", "destination_service_name": "ext"},
        ]
        actual = [
            {"event_type": "port_scan", "service_name": "a", "destination_service_name": "b"},
        ]
        self.assertEqual(evaluate_completeness(actual, expected), 0.5)

    def test_timestamp_tolerance(self) -> None:
        expected = [
            {
                "event_type": "brute_force",
                "source_service_name": "x",
                "timestamp": "2026-06-01T12:00:00",
            },
        ]
        actual = [
            {
                "event_type": "brute_force",
                "service_name": "x",
                "timestamp": "2026-06-01T12:00:25",
            },
        ]
        self.assertTrue(
            events_equivalent(actual[0], expected[0], timestamp_tolerance_sec=30.0)
        )
        self.assertFalse(
            events_equivalent(actual[0], expected[0], timestamp_tolerance_sec=10.0)
        )

    def test_reconstruct_chain_log(self) -> None:
        expected = [{"event_type": "a"}, {"event_type": "b"}]
        actual = [{"event_type": "a"}]
        log = reconstruct_chain_log(actual, expected)
        self.assertTrue(log[0]["matched"])
        self.assertFalse(log[1]["matched"])


if __name__ == "__main__":
    unittest.main()
