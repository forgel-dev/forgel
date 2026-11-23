from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel import contract
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.projects import create_project
from forgel.tasks import create_task

REPO_ROOT = Path(__file__).resolve().parents[1]


class ContractTest(unittest.TestCase):
    def test_the_contract_is_shared_and_names_the_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                home=Path(tmp),
                registry_path=REPO_ROOT / "registry" / "recipes.json",
                templates_path=REPO_ROOT / "src" / "forgel" / "templates",
                jurisdiction_path=REPO_ROOT / "jurisdiction",
                qa_runtime="local",
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project = create_project(
                settings, ledger, "contract", "A brief."
            )
            layout = ProjectLayout.detect(
                ledger.get_project(project)["workspace"]
            )
            spec = "docs/program/specs/contract.md"
            write_text(
                layout.artifact(spec),
                "# Spec\n\n## Non-Goals\n\n- Do not refactor the harness\n\n"
                "## Affected Files\n\n- install.sh\n- tests/test_install.py\n",
            )
            task = create_task(
                layout,
                "Fix the installer",
                ["Fix it"],
                ["It works"],
                repo_id="main",
                spec=spec,
            )
            digest = contract.digest(layout, task)
            self.assertIn("Do not refactor the harness", digest)
            self.assertIn("Include every file the task needs", digest)
            self.assertIn("against a file list", digest)
            # An old file list is context only, never a contract.
            self.assertNotIn("install.sh", digest)
            stripped = contract.without_affected_files(
                layout.artifact(spec).read_text(encoding="utf-8")
            )
            self.assertNotIn("## Affected Files", stripped)
            self.assertIn("Do not refactor the harness", stripped)


if __name__ == "__main__":
    unittest.main()
