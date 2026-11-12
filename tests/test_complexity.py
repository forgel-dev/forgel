from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.complexity import PatchMetrics, evaluate, write_report
from forgel.project_config import SimplicityConfig


class ComplexityTest(unittest.TestCase):
    def test_under_budget(self) -> None:
        self.assertEqual(
            evaluate(PatchMetrics(added_lines=10), SimplicityConfig()), []
        )

    def test_added_lines_over_budget(self) -> None:
        violations = evaluate(
            PatchMetrics(added_lines=500), SimplicityConfig()
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("budget", violations[0])

    def test_config_keys_over_budget(self) -> None:
        violations = evaluate(
            PatchMetrics(new_config_keys=3), SimplicityConfig()
        )
        self.assertEqual(len(violations), 1)

    def test_compatibility_markers_over_budget(self) -> None:
        violations = evaluate(
            PatchMetrics(compat_markers=1), SimplicityConfig()
        )
        self.assertEqual(len(violations), 1)

    def test_disabled(self) -> None:
        self.assertEqual(
            evaluate(
                PatchMetrics(added_lines=9999),
                SimplicityConfig(enabled=False),
            ),
            [],
        )

    def test_write_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_report(Path(tmp), PatchMetrics(added_lines=1), [])
            self.assertTrue(path.exists())
            self.assertIn("PASS", path.read_text(encoding="utf-8"))
            self.assertTrue(
                (Path(tmp) / "docs/program/complexity/metrics.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
