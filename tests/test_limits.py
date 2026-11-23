from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel import limits
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.projects import create_project
from forgel.runtime_ops import run_operation

REPO_ROOT = Path(__file__).resolve().parents[1]


class LimitsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        project_id = create_project(
            self.settings, self.ledger, "limits", "A brief."
        )
        self.project = self.ledger.get_project(project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])

    def test_the_project_override_wins(self) -> None:
        self.assertEqual(
            limits.get(self.layout, "command_timeout"), 3600
        )
        limits.set_value(self.layout, "command_timeout", 7200)
        self.assertEqual(
            limits.get(self.layout, "command_timeout", 10), 7200
        )
        self.assertTrue(limits.path(self.layout).is_file())

    def test_an_unknown_limit_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            limits.set_value(self.layout, "unknown", 10)

    def test_the_audit_deadline_is_half_an_hour_and_configurable(
        self,
    ) -> None:
        self.assertEqual(
            limits.get(self.layout, "audit_timeout"), 1800
        )
        limits.set_value(self.layout, "audit_timeout", 900)
        self.assertEqual(
            limits.get(self.layout, "audit_timeout"), 900
        )

    def test_the_runtime_operation_raises_a_limit(self) -> None:
        text = run_operation(
            self.settings,
            self.ledger,
            self.project,
            "set_limit",
            {"name": "command_timeout", "seconds": 7200},
        )
        self.assertIn("7200", text)
        self.assertEqual(
            limits.get(self.layout, "command_timeout"), 7200
        )


if __name__ == "__main__":
    unittest.main()
