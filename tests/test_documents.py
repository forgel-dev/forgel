from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from forgel.agent import build_context
from forgel.artifacts import read_json, write_json
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
from forgel.tasks import create_task

REPO_ROOT = Path(__file__).resolve().parents[1]
OLD = "2020-01-01T00:00:00+00:00"


def _git(root: Path, *args: str, date: str | None = None) -> None:
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            *args,
        ],
        cwd=root,
        env=env,
        check=True,
    )


def _commit(root: Path, files: list[str], date: str) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    _git(root, "add", *files)
    _git(root, "commit", "-q", "-m", "document", date=date)


def _commit_more(root: Path, files: list[str]) -> None:
    _git(root, "add", *files)
    _git(root, "commit", "-q", "-m", "document")


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

    def test_repository_documents_are_read_regardless_of_age(self) -> None:
        control = self.layout.control
        control.mkdir(parents=True, exist_ok=True)
        (control / "FORGEL.md").write_text(
            "OLD-PROJECT-MARKER\n", encoding="utf-8"
        )
        (control / "AGENTS.md").write_text(
            "OLD-AGENTS-MARKER\n", encoding="utf-8"
        )
        _commit(control, ["FORGEL.md", "AGENTS.md"], OLD)

        repo = self.layout.repo_path("main")
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "OLD-README-MARKER\n", encoding="utf-8"
        )
        (repo / "PLAN.md").write_text(
            "OLD-PLAN-MARKER\n", encoding="utf-8"
        )
        _commit(repo, ["README.md", "PLAN.md"], OLD)

        instructions = instruction_context(self.layout)
        context = build_context(self.layout, self.project, self.ledger)

        self.assertIn("OLD-PROJECT-MARKER", instructions)
        self.assertIn("OLD-AGENTS-MARKER", instructions)
        self.assertIn("OLD-README-MARKER", context)
        self.assertNotIn("OLD-PLAN-MARKER", context)

    def test_process_documents_from_before_initialization_are_ignored(
        self,
    ) -> None:
        control = self.layout.control
        plans = control / "docs" / "program" / "plans"
        plans.mkdir(parents=True, exist_ok=True)
        (plans / "20200101000000_old.md").write_text(
            "# Plan: OLD-PLAN-MARKER\n", encoding="utf-8"
        )
        decisions = control / "docs" / "program" / "decisions.md"
        decisions.write_text("OLD-DECISION-MARKER\n", encoding="utf-8")
        _commit(
            control,
            ["docs/program/plans/20200101000000_old.md",
             "docs/program/decisions.md"],
            OLD,
        )

        (plans / "20260101000000_new.md").write_text(
            "# Plan: CURRENT-PLAN-MARKER\n", encoding="utf-8"
        )
        _commit_more(control, ["docs/program/plans/20260101000000_new.md"])

        task = create_task(
            self.layout, "OLD-TASK-MARKER", ["Do it"], ["Done"]
        )
        path = self.layout.artifact(
            f"docs/program/tasks/{task['id']}.json"
        )
        data = read_json(path)
        data["created_at"] = OLD
        write_json(path, data)

        context = build_context(self.layout, self.project, self.ledger)

        self.assertNotIn("OLD-PLAN-MARKER", context)
        self.assertNotIn("OLD-DECISION-MARKER", context)
        self.assertNotIn("OLD-TASK-MARKER", context)
        self.assertIn("CURRENT-PLAN-MARKER", context)


if __name__ == "__main__":
    unittest.main()
