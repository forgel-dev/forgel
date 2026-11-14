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
            assumptions=["SQLite is the storage"],
        )
        self.assertEqual(task["assumptions"], ["SQLite is the storage"])
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

    def test_dependencies_gate_the_next_task(self) -> None:
        first = tasks.create_task(
            self.layout, "First", ["A"], ["B"], repo_id="main"
        )
        second = tasks.create_task(
            self.layout,
            "Second",
            ["A"],
            ["B"],
            repo_id="main",
            depends_on=[first["id"]],
        )
        self.assertEqual(
            tasks.next_pending_task(self.layout)["id"], first["id"]
        )
        tasks.update_task(self.layout, first["id"], status="done")
        self.assertEqual(
            tasks.next_pending_task(self.layout)["id"], second["id"]
        )
        tasks.update_task(self.layout, first["id"], status="failed")
        self.assertIsNone(tasks.next_pending_task(self.layout))
        blocked = tasks.blocked_pending(self.layout)
        self.assertEqual([item["id"] for item in blocked], [second["id"]])

    def test_a_failure_blocks_dependents_and_retry_releases_them(
        self,
    ) -> None:
        first = tasks.create_task(
            self.layout, "First", ["A"], ["B"], repo_id="main",
            plan_id="p1", order=1,
        )
        second = tasks.create_task(
            self.layout, "Second", ["A"], ["B"], repo_id="main",
            plan_id="p1", order=2, depends_on=[first["id"]],
        )
        third = tasks.create_task(
            self.layout, "Third", ["A"], ["B"], repo_id="main",
            plan_id="p1", order=3,
        )
        tasks.update_task(
            self.layout,
            first["id"],
            status="failed",
            result={"failure": {"kind": "qa", "message": "red"}},
        )
        blocked = tasks.block_dependents(self.layout, first["id"])
        self.assertEqual(
            [item["id"] for item in blocked], [second["id"]]
        )
        stored = tasks.get_task(self.layout, second["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["result"]["blocked_by"], first["id"])
        pending = tasks.get_task(self.layout, third["id"])
        assert pending is not None
        self.assertEqual(pending["status"], "pending")
        retried = tasks.retry_task(self.layout, first["id"])
        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["result"]["manual_retries"], 1)
        released = tasks.get_task(self.layout, second["id"])
        assert released is not None
        self.assertEqual(released["status"], "pending")

    def test_interrupted_tasks_are_requeued(self) -> None:
        task = tasks.create_task(
            self.layout,
            "Resume me",
            ["Do work"],
            ["Work is done"],
            repo_id="main",
        )
        tasks.update_task(self.layout, task["id"], status="running")
        recovered = tasks.recover_running(self.layout)
        self.assertEqual(len(recovered), 1)
        self.assertEqual(recovered[0]["status"], "pending")
        self.assertEqual(recovered[0]["result"]["resume_count"], 1)

        for _ in range(4):
            tasks.update_task(self.layout, task["id"], status="running")
            recovered = tasks.recover_running(self.layout)
        stored = tasks.get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertIn("interrupted", stored["result"]["summary"])

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
