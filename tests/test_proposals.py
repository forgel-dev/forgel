from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.project_config import (
    BudgetConfig,
    JurisdictionConfig,
    ModelsConfig,
    ProjectConfig,
    QAConfig,
    ReleaseConfig,
)
from forgel.proposals import ProposalError, list_proposals, propose_project


def _config(
    auto_patch: bool = False, propose_minor: bool = False
) -> ProjectConfig:
    return ProjectConfig(
        name="demo",
        recipe="hello-web@0.1.0",
        qa=QAConfig(),
        jurisdiction=JurisdictionConfig(),
        models=ModelsConfig(),
        budget=BudgetConfig(),
        release=ReleaseConfig(
            auto_patch=auto_patch, propose_minor=propose_minor
        ),
    )


class ProposalTest(unittest.TestCase):
    def test_patch_is_proposed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            path = propose_project(
                workspace, _config(), "patch", "Fix double charge", "evidence"
            )
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("Class: `patch`", text)
            self.assertIn("Auto-apply: `false`", text)

    def test_minor_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ProposalError):
                propose_project(Path(tmp), _config(), "minor", "New feature")

    def test_minor_is_allowed_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = propose_project(
                Path(tmp), _config(propose_minor=True), "minor", "New feature"
            )
            self.assertTrue(path.exists())

    def test_auto_patch_flag_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = propose_project(
                Path(tmp), _config(auto_patch=True), "patch", "Fix"
            )
            self.assertIn("Auto-apply: `true`", path.read_text(encoding="utf-8"))

    def test_major_is_allowed_on_human_initiative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = propose_project(Path(tmp), _config(), "major", "Breaking change")
            self.assertTrue(path.exists())

    def test_list_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            propose_project(workspace, _config(), "patch", "One")
            propose_project(workspace, _config(), "patch", "Two")
            self.assertEqual(len(list_proposals(workspace)), 2)


if __name__ == "__main__":
    unittest.main()
