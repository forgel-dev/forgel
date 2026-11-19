from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.instructions import instruction_context
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class InstructionFilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        ledger = Ledger(settings.db_path)
        self.addCleanup(ledger.close)
        project_id = create_project(
            settings,
            ledger,
            "Instructions",
            "A demo project.",
            mode="brownfield",
        )
        project = ledger.get_project(project_id)
        assert project is not None
        self.layout = ProjectLayout.detect(project["workspace"])
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                },
                {
                    "id": "code",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": ["main"],
                },
            ],
        )
        for repo_id in ("main", "code"):
            self.layout.repo_path(repo_id).mkdir(
                parents=True, exist_ok=True
            )
        self.layout.control.mkdir(parents=True, exist_ok=True)
        (self.layout.control / "FORGEL.md").write_text(
            "PROJECT-MARKER\n", encoding="utf-8"
        )
        (self.layout.control / "AGENTS.md").write_text(
            "PROJECT-AGENTS-MARKER\n", encoding="utf-8"
        )
        (self.layout.repo_path("main") / "FORGEL.md").write_text(
            "MAIN-MARKER\n", encoding="utf-8"
        )
        (self.layout.repo_path("code") / "AGENTS.md").write_text(
            "CODE-MARKER\n", encoding="utf-8"
        )

    def test_both_layers_are_included_with_precedence(self) -> None:
        context = instruction_context(self.layout)
        self.assertIn("Project: FORGEL.md", context)
        self.assertIn("PROJECT-MARKER", context)
        self.assertIn("Project: AGENTS.md", context)
        self.assertIn("PROJECT-AGENTS-MARKER", context)
        self.assertIn("Repository main: FORGEL.md", context)
        self.assertIn("MAIN-MARKER", context)
        self.assertIn("Repository code: AGENTS.md", context)
        self.assertIn("CODE-MARKER", context)
        self.assertIn("take precedence", context)

    def test_a_single_repository_can_be_selected(self) -> None:
        context = instruction_context(self.layout, ["code"])
        self.assertIn("PROJECT-MARKER", context)
        self.assertIn("CODE-MARKER", context)
        self.assertNotIn("MAIN-MARKER", context)


if __name__ == "__main__":
    unittest.main()
