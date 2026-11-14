from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel import tasks
from forgel.config import Settings
from forgel.daemon import project_state
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]


class TasksTest(unittest.TestCase):
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
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "demo",
            "A demo project.",
            mode="brownfield",
        )
        self.project = self.ledger.get_project(self.project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])

    def test_create_list_and_update(self) -> None:
        task = tasks.create_task(
            self.layout,
            "Build a blog",
            ["List posts", "Create posts"],
            ["POST /posts creates a post"],
            constraints=["stdlib only"],
            test_command=["python", "-m", "unittest"],
        )
        self.assertEqual(task["status"], "pending")
        self.assertEqual(len(tasks.list_tasks(self.layout)), 1)
        self.assertEqual(
            tasks.next_pending_task(self.layout)["id"], task["id"]
        )
        updated = tasks.update_task(
            self.layout, task["id"], status="done", result={"summary": "ok"}
        )
        self.assertEqual(updated["status"], "done")
        self.assertIsNone(tasks.next_pending_task(self.layout))
        self.assertEqual(tasks.latest_task(self.layout)["id"], task["id"])
        self.assertTrue(
            tasks.task_path(self.layout, task["id"]).exists()
        )

    def test_task_requires_requirements_and_acceptance(self) -> None:
        with self.assertRaises(ValueError):
            tasks.create_task(self.layout, "x", [], ["a"])
        with self.assertRaises(ValueError):
            tasks.create_task(self.layout, "x", ["a"], [])
        with self.assertRaises(ValueError):
            tasks.create_task(self.layout, "", ["a"], ["b"])

    def test_cancel_a_pending_task(self) -> None:
        task = tasks.create_task(
            self.layout, "Build", ["a"], ["b"]
        )
        cancelled = tasks.cancel_task(self.layout, task["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertIsNone(tasks.next_pending_task(self.layout))
        with self.assertRaises(ValueError):
            tasks.cancel_task(self.layout, task["id"])

    def test_project_state_tracks_tasks(self) -> None:
        self.assertEqual(
            project_state(self.ledger, self.project), "adopted"
        )
        task = tasks.create_task(
            self.layout, "Build", ["a"], ["b"]
        )
        self.assertEqual(
            project_state(self.ledger, self.project), "task pending"
        )
        tasks.update_task(self.layout, task["id"], status="running")
        self.assertEqual(
            project_state(self.ledger, self.project), "task running"
        )
        tasks.update_task(
            self.layout, task["id"], status="failed",
            result={"summary": "boom"},
        )
        self.assertEqual(
            project_state(self.ledger, self.project), "task failed"
        )
        tasks.update_task(self.layout, task["id"], status="done")
        self.assertEqual(
            project_state(self.ledger, self.project), "task done"
        )


if __name__ == "__main__":
    unittest.main()
