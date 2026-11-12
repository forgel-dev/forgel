from __future__ import annotations

import unittest

from forgel.state import STAGES, next_stage, stages_from, validate_stage


class StateTest(unittest.TestCase):
    def test_order_is_linear(self) -> None:
        self.assertEqual(next_stage("intake"), "jurisdiction")
        self.assertEqual(next_stage("jurisdiction"), "recipe")
        self.assertEqual(next_stage("audit"), "done")
        self.assertEqual(next_stage("done"), "done")

    def test_stages_from(self) -> None:
        stages = stages_from("spec")
        self.assertEqual(stages[0], "spec")
        self.assertEqual(stages[-1], "done")
        self.assertEqual(len(stages), len(STAGES) - STAGES.index("spec"))

    def test_invalid_stage(self) -> None:
        with self.assertRaises(ValueError):
            validate_stage("unknown")
        with self.assertRaises(ValueError):
            next_stage("unknown")


if __name__ == "__main__":
    unittest.main()
