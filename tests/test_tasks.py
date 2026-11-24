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

    def test_attempt_number_reads_the_rework_count(self) -> None:
        self.assertEqual(tasks.attempt_number({}), 0)
        self.assertEqual(
            tasks.attempt_number({"result": {"rework_count": 2}}), 2
        )
        self.assertEqual(
            tasks.attempt_number({"result": {"rework_count": "bad"}}), 0
        )

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

    def test_tasks_run_in_creation_order(self) -> None:
        first = tasks.create_task(
            self.layout, "First", ["A"], ["B"], repo_id="main"
        )
        second = tasks.create_task(
            self.layout, "Second", ["A"], ["B"], repo_id="main"
        )
        self.assertEqual(
            tasks.next_pending_task(self.layout)["id"], first["id"]
        )
        tasks.update_task(self.layout, first["id"], status="done")
        self.assertEqual(
            tasks.next_pending_task(self.layout)["id"], second["id"]
        )
        self.assertNotIn("depends_on", first)
        self.assertNotIn("depends_on", second)

    def test_stopping_a_plan_blocks_it_and_retry_releases_it(
        self,
    ) -> None:
        first = tasks.create_task(
            self.layout, "First", ["A"], ["B"], repo_id="main",
            plan_id="p1", order=1,
        )
        second = tasks.create_task(
            self.layout, "Second", ["A"], ["B"], repo_id="main",
            plan_id="p1", order=2,
        )
        other = tasks.create_task(
            self.layout, "Other", ["A"], ["B"], repo_id="main",
            plan_id="p2", order=1,
        )
        tasks.update_task(
            self.layout,
            first["id"],
            status="failed",
            result={"failure": {"kind": "qa", "message": "red"}},
        )
        blocked = tasks.stop_plan(self.layout, first["id"])
        self.assertEqual(
            [item["id"] for item in blocked], [second["id"]]
        )
        stored = tasks.get_task(self.layout, second["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(stored["result"]["blocked_by"], first["id"])
        untouched = tasks.get_task(self.layout, other["id"])
        assert untouched is not None
        self.assertEqual(untouched["status"], "pending")
        retried = tasks.retry_task(self.layout, first["id"])
        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["result"]["manual_retries"], 1)
        released = tasks.get_task(self.layout, second["id"])
        assert released is not None
        self.assertEqual(released["status"], "pending")

    def test_a_delayed_retry_is_not_picked_until_its_time(self) -> None:
        from datetime import datetime, timezone

        task = tasks.create_task(
            self.layout, "Retry later", ["A"], ["B"], repo_id="main"
        )
        now = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)
        data = dict(task.get("result") or {})
        data["retry_after"] = "2026-11-16T10:05:00+00:00"
        tasks.update_task(self.layout, task["id"], result=data)
        self.assertIsNone(tasks.next_pending_task(self.layout, now))
        self.assertEqual(len(tasks.waiting_pending(self.layout, now)), 1)
        later = datetime(2026, 11, 16, 10, 5, 1, tzinfo=timezone.utc)
        self.assertEqual(
            tasks.next_pending_task(self.layout, later)["id"],
            task["id"],
        )
        self.assertEqual(tasks.waiting_pending(self.layout, later), [])

    def test_manual_retry_clears_the_backoff(self) -> None:
        task = tasks.create_task(
            self.layout, "Retry me", ["A"], ["B"], repo_id="main"
        )
        data = {
            "attempts": 2,
            "retry_after": "2026-11-16T10:05:00+00:00",
            "failure": {"kind": "infrastructure", "message": "x"},
        }
        tasks.update_task(
            self.layout, task["id"], status="failed", result=data
        )
        retried = tasks.retry_task(self.layout, task["id"])
        self.assertEqual(retried["status"], "pending")
        self.assertNotIn("retry_after", retried["result"])
        self.assertEqual(retried["result"]["attempts"], 0)

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
        self.assertEqual(tasks.listed_tasks(self.layout), [])
        again = tasks.cancel_task(self.layout, task["id"])
        self.assertEqual(again["status"], "cancelled")

    def test_a_running_task_can_be_cancelled_and_keeps_its_result(
        self,
    ) -> None:
        task = tasks.create_task(
            self.layout, "Build", ["a"], ["b"]
        )
        tasks.update_task(
            self.layout,
            task["id"],
            status="running",
            result={"git": {"head": "a" * 40}},
        )

        cancelled = tasks.cancel_task(
            self.layout, task["id"], notes="not needed"
        )

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(
            cancelled["result"]["git"]["head"], "a" * 40
        )
        self.assertIn("not needed", cancelled["result"]["summary"])
        with self.assertRaises(ValueError):
            tasks.retry_task(self.layout, task["id"])
        with self.assertRaises(ValueError):
            tasks.restart_task(self.layout, task["id"])

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

    def test_current_task_prefers_the_running_task(self) -> None:
        running = tasks.create_task(
            self.layout,
            "Running work",
            ["A"],
            ["B"],
            repo_id="main",
            task_id="20260101000000_running",
        )
        tasks.update_task(
            self.layout, running["id"], status="running"
        )
        newer = tasks.create_task(
            self.layout,
            "Newer work",
            ["A"],
            ["B"],
            repo_id="main",
            task_id="20260101000001_newer",
        )
        tasks.update_task(self.layout, newer["id"], status="review")

        current = tasks.current_task(self.layout)

        assert current is not None
        self.assertEqual(current["id"], running["id"])

    def test_current_task_uses_the_last_launch_not_the_file_name(self) -> None:
        earlier = tasks.create_task(
            self.layout,
            "Earlier file name",
            ["A"],
            ["B"],
            task_id="20260101000000_alpha",
        )
        later = tasks.create_task(
            self.layout,
            "Later file name",
            ["A"],
            ["B"],
            task_id="20260101000001_zulu",
        )
        tasks.update_task(
            self.layout,
            earlier["id"],
            started_at="2026-01-01T10:00:00+00:00",
        )
        tasks.update_task(
            self.layout,
            later["id"],
            started_at="2026-01-01T09:00:00+00:00",
        )

        current = tasks.current_task(self.layout)
        latest = tasks.latest_task(self.layout)

        assert current is not None
        assert latest is not None
        self.assertEqual(current["id"], earlier["id"])
        self.assertEqual(latest["id"], earlier["id"])

    def test_current_task_prefers_a_recently_restarted_task(self) -> None:
        restarted = tasks.create_task(
            self.layout,
            "Restarted work",
            ["A"],
            ["B"],
            task_id="20260101000000_alpha",
        )
        other = tasks.create_task(
            self.layout,
            "Other work",
            ["A"],
            ["B"],
            task_id="20260101000001_zulu",
        )
        tasks.update_task(
            self.layout,
            other["id"],
            started_at="2026-01-01T09:00:00+00:00",
        )
        tasks.restart_task(self.layout, restarted["id"])

        current = tasks.current_task(self.layout)

        assert current is not None
        self.assertEqual(current["id"], restarted["id"])

    def test_resolve_task_by_id_title_and_description(self) -> None:
        by_id = tasks.create_task(
            self.layout,
            "Alpha",
            ["A"],
            ["B"],
            task_id="20260101000000_alpha",
        )
        by_title = tasks.create_task(
            self.layout,
            "Build the client",
            ["A"],
            ["B"],
            task_id="20260101000001_client",
        )
        by_description = tasks.create_task(
            self.layout,
            "Unrelated title",
            ["A"],
            ["B"],
            task_id="20260101000002_installer",
            summary="A combined installer for the engine and the client.",
        )

        resolved_id = tasks.resolve_task(
            self.layout, "20260101000000_alpha"
        )
        resolved_title = tasks.resolve_task(
            self.layout, "Build the client"
        )
        resolved_description = tasks.resolve_task(
            self.layout, "combined installer"
        )

        assert resolved_id is not None
        assert resolved_title is not None
        assert resolved_description is not None
        self.assertEqual(resolved_id["id"], by_id["id"])
        self.assertEqual(resolved_title["id"], by_title["id"])
        self.assertEqual(
            resolved_description["id"], by_description["id"]
        )

    def test_resolve_task_rejects_an_ambiguous_reference(self) -> None:
        tasks.create_task(
            self.layout,
            "Build the client",
            ["A"],
            ["B"],
            task_id="20260101000000_client",
        )
        tasks.create_task(
            self.layout,
            "Build the engine",
            ["A"],
            ["B"],
            task_id="20260101000001_engine",
        )
        with self.assertRaises(ValueError):
            tasks.resolve_task(self.layout, "build")

    def test_resolve_task_empty_uses_the_current_task(self) -> None:
        tasks.create_task(
            self.layout,
            "Earlier work",
            ["A"],
            ["B"],
            task_id="20260101000000_alpha",
        )
        later = tasks.create_task(
            self.layout,
            "Later work",
            ["A"],
            ["B"],
            task_id="20260101000001_zulu",
        )
        tasks.update_task(
            self.layout,
            later["id"],
            started_at="2026-01-01T10:00:00+00:00",
        )

        resolved = tasks.resolve_task(self.layout, "")

        assert resolved is not None
        self.assertEqual(resolved["id"], later["id"])

    def test_restart_task_records_the_restart_time(self) -> None:
        task = tasks.create_task(
            self.layout, "Restart", ["A"], ["B"]
        )
        tasks.restart_task(self.layout, task["id"])
        stored = tasks.get_task(self.layout, task["id"])
        assert stored is not None
        self.assertIn("restarted_at", stored["result"])
        self.assertEqual(stored["result"]["manual_restarts"], 1)


if __name__ == "__main__":
    unittest.main()
