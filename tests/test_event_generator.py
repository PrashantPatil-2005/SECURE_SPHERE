"""Tests for synthetic event generator (E3)."""

from __future__ import annotations

import random
import unittest

from benchmarks.lib.event_generator import generate_event


class TestEventGenerator(unittest.TestCase):
    def test_reproducible_with_seed(self) -> None:
        a = generate_event(random.Random(42))
        b = generate_event(random.Random(42))
        self.assertEqual(a.event_type, b.event_type)
        self.assertEqual(a.source_service_name, b.source_service_name)

    def test_required_fields(self) -> None:
        ev = generate_event(random.Random(1))
        d = ev.to_dict()
        for key in (
            "event_id",
            "timestamp",
            "event_type",
            "source_layer",
            "source_service_name",
            "destination_service_name",
        ):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
