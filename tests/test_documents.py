from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from forgel.agent import build_context
from forgel.config import Settings
from forgel.documents import (
    created_after,
    document_created_at,
    initialized_at,
    is_current,
    parse_time,
)
from forgel.instructions import instruction_context
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]
OLD = "2020-01-01T00:00:00+00:00"


def _commit(root: Path, files: list[str], date: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", *files], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "document",
        ],
        cwd=root,
        env=dict(
            os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date
        ),
        check=True,
    )


class DocumentTimeTest(unittest.TestCase):
    def test_parse_time_accepts_iso_and_rejects_garbage(self) -> None:
        self.assertEqual(
            parse_time("2026-11-14T23:33:25+00:00"),
            datetime(2026, 11, 14, 23, 33, 25, tzinfo=timezone.utc),
        )
        self.assertEqual(
            parse_time("2026-11-14T23:33:25Z"),
            datetime(2026, 11, 14, 23, 33, 25, tzinfo=timezone.utc),
        )
        self.assertIsNone(parse_time(""))
        self.assertIsNone(parse_time(None))
        self.assertIsNone(parse_time("not a time"))

    def test_the_first_commit_is_the_creation_time(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "README.md"
            path.write_text("first\n", encoding="utf-8")
            _commit(root, ["README.md"], OLD)
            path.write_text("changed\n", encoding="utf-8")

            created = document_created_at(path)

            assert created is not None
            self.assertEqual(created.year, 2020)
            self.assertFalse(
                is_current(path, datetime(2026, 1, 1, tzinfo=timezone.utc))
            )
            self.assertTrue(
                is_current(path, datetime(2019, 1, 1, tzinfo=timezone.utc))
            )

    def test_a_missing_time_is_not_filtered(self) -> None:
        self.assertTrue(created_after(None, datetime.now(timezone.utc)))
        self.assertTrue(created_after("", datetime.now(timezone.utc)))


class ContextTimeFilterTest(unittest.TestCase):
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
            self.settings,
            self.ledger,
            "Documents",
            "A brief.",
            mode="brownfield",
        )
        self.project = self.ledger.get_project(project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                }
            ],
        )

    def test_initialized_at_reads_project_metadata(self) -> None:
        initialized = initialized_at(self.layout, self.project)
        assert initialized is not None
        self.assertEqual(
            initialized, parse_time(self.project["created_at"])
        )

    def test_pre_initialization_instructions_are_not_used(self) -> None:
        control = self.layout.control
        control.mkdir(parents=True, exist_ok=True)
        (control / "FORGEL.md").write_text(
            "OLD-PROJECT-MARKER\n", encoding="utf-8"
        )
        _commit(control, ["FORGEL.md"], OLD)

        repo = self.layout.repo_path("main")
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "AGENTS.md").write_text(
            "CURRENT-REPO-MARKER\n", encoding="utf-8"
        )

        context = instruction_context(self.layout)

        self.assertIn("CURRENT-REPO-MARKER", context)
        self.assertNotIn("OLD-PROJECT-MARKER", context)

    def test_pre_initialization_project_documents_are_not_context(
        self,
    ) -> None:
        repo = self.layout.repo_path("main")
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "OLD-README-MARKER\n", encoding="utf-8"
        )
        _commit(repo, ["README.md"], OLD)
        (repo / "docs").mkdir(parents=True, exist_ok=True)
        (repo / "docs" / "GUIDE.md").write_text(
            "CURRENT-GUIDE-MARKER\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", "docs/GUIDE.md"], cwd=repo, check=True
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "guide",
            ],
            cwd=repo,
            check=True,
        )

        context = build_context(self.layout, self.project, self.ledger)

        self.assertIn("CURRENT-GUIDE-MARKER", context)
        self.assertNotIn("OLD-README-MARKER", context)


if __name__ == "__main__":
    unittest.main()
