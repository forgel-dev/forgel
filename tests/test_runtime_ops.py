from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from forgel import specs
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.projects import create_project
from forgel.release_train import load_release, save_release
from forgel.runtime_ops import OPERATIONS, run_operation
from forgel.tasks import create_task, get_task, listed_tasks, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]


RESTART_SPEC = {
    "problem": "The work is missing.",
    "outcome": "The work is done.",
    "scope": ["the work"],
    "non_goals": [],
    "requirements": ["The work is done."],
    "acceptance": ["The work works."],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The work exists."],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "related_documents": [],
    "revision_history": [],
    "checks": [
        {
            "criterion": "The work is correct",
            "verification": "review",
            "command": [],
        }
    ],
    "test_command": [],
    "external_dependencies": [],
}


class RuntimeOpsTest(unittest.TestCase):
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
            self.settings, self.ledger, "runtime-ops", "A brief."
        )
        self.project = self.ledger.get_project(project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])

    def _task(self, status: str = "running") -> dict:
        task = create_task(
            self.layout, "Do work", ["A"], ["B"], repo_id="main"
        )
        update_task(self.layout, task["id"], status=status)
        return task

    def _release(self, status: str = "running") -> str:
        release_id = "20260101000000_release"
        save_release(
            self.layout,
            {
                "id": release_id,
                "title": "A release",
                "status": status,
                "repos": {},
                "tasks": [],
            },
        )
        return release_id

    def test_an_unknown_operation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_operation(
                self.settings, self.ledger, self.project, "secret"
            )

    def test_the_template_pipeline_is_not_a_chat_operation(self) -> None:
        self.assertNotIn("orchestrate", OPERATIONS)
        with self.assertRaises(ValueError):
            run_operation(
                self.settings, self.ledger, self.project, "orchestrate"
            )

    def test_drive_advances_the_runtime(self) -> None:
        with patch(
            "forgel.runtime_ops.run_once", return_value=["p1"]
        ) as run_once:
            text = run_operation(
                self.settings, self.ledger, self.project, "drive"
            )
        run_once.assert_called_once()
        self.assertIn("p1", text)

    def test_task_process_runs_the_post_agent_pipeline(self) -> None:
        task = self._task()
        with patch(
            "forgel.runtime_ops.process_task_result"
        ) as process:
            text = run_operation(
                self.settings,
                self.ledger,
                self.project,
                "task_process",
                {"task_id": task["id"]},
            )
        process.assert_called_once()
        self.assertIn(task["id"], text)

    def test_task_qa_reports_the_verdict(self) -> None:
        task = self._task()
        with patch(
            "forgel.runtime_ops.run_task_qa",
            return_value=SimpleNamespace(status="pass"),
        ):
            text = run_operation(
                self.settings,
                self.ledger,
                self.project,
                "task_qa",
                {"task_id": task["id"]},
            )
        self.assertIn("QA pass", text)

    def test_release_audit_reports_the_verdict(self) -> None:
        release_id = self._release()
        with patch(
            "forgel.runtime_ops.audit_release", return_value=True
        ):
            text = run_operation(
                self.settings,
                self.ledger,
                self.project,
                "release_audit",
                {"release_id": release_id},
                client=object(),
            )
        self.assertIn("audit passed", text)

    def test_release_finalize_publishes(self) -> None:
        release_id = self._release("ready")
        with patch(
            "forgel.runtime_ops.finalize_release",
            return_value={"id": release_id, "status": "released"},
        ):
            text = run_operation(
                self.settings,
                self.ledger,
                self.project,
                "release_finalize",
                {"release_id": release_id},
            )
        self.assertIn("released", text)


    def test_task_retry_accepts_any_status(self) -> None:
        task = self._task(status="running")
        text = run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_retry",
            {"task_id": task["id"]},
        )
        self.assertIn("queued", text)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "pending")

    def test_task_restart_rewrites_the_spec_and_starts_over(self) -> None:
        task = self._task(status="done")
        client = ScriptedModelClient([json.dumps(RESTART_SPEC)])
        with patch("forgel.runtime_ops._run_task") as run_task:
            text = run_operation(
                self.settings,
                self.ledger,
                self.project,
                "task_restart",
                {"task_id": task["id"]},
                client=client,
            )
        self.assertIn("restarted", text)
        run_task.assert_called_once()
        started = run_task.call_args.args[4]
        self.assertEqual(started["id"], task["id"])
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(
            stored["requirements"], RESTART_SPEC["requirements"]
        )
        self.assertEqual(
            stored["result"].get("manual_restarts"), 1
        )
        spec_path = self.layout.artifact(
            f"docs/program/specs/{task['id']}.md"
        )
        self.assertTrue(spec_path.exists())
        stages = [
            event["stage"]
            for event in self.ledger.events(self.project["id"])
        ]
        self.assertIn("task_restart", stages)

    def test_task_restart_passes_requested_changes_to_the_writer(self) -> None:
        task = self._task(status="done")
        client = ScriptedModelClient([json.dumps(RESTART_SPEC)])
        changes = "The documentation test must be removed."
        with patch("forgel.runtime_ops._run_task"):
            run_operation(
                self.settings,
                self.ledger,
                self.project,
                "task_restart",
                {"task_id": task["id"], "changes": changes},
                client=client,
            )
        prompt = client.requests[0][-1].content
        self.assertIn("The owner requires these changes", prompt)
        self.assertIn(changes, prompt)


    def test_task_cancel_stops_work_and_marks_the_document(self) -> None:
        task = self._task(status="running")
        update_task(
            self.layout,
            task["id"],
            result={"git": {"base": "a" * 40, "head": "b" * 40}},
        )
        spec = self.layout.artifact(specs.spec_path(task["id"]))
        write_text(spec, "# Task\n\nDo the work.\n")

        text = run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_cancel",
            {"task_id": task["id"]},
        )

        self.assertIn("cancelled", text)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "cancelled")
        self.assertEqual(
            stored["result"].get("git", {}).get("head"), "b" * 40
        )
        document = spec.read_text(encoding="utf-8")
        self.assertTrue(document.startswith(specs.CANCEL_MARKER))
        self.assertIn("not accept", document)
        self.assertIn("Do the work.", document)
        self.assertEqual(listed_tasks(self.layout), [])

    def test_cancelling_the_last_task_cancels_its_release(self) -> None:
        release_id = self._release()
        task = create_task(
            self.layout,
            "Do work",
            ["A"],
            ["B"],
            repo_id="main",
            release_id=release_id,
        )

        text = run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_cancel",
            {"task_id": task["id"]},
        )

        stored = load_release(self.layout, release_id)
        assert stored is not None
        self.assertEqual(stored["status"], "cancelled")
        self.assertIn(release_id, text)

    def test_cancelling_one_of_two_tasks_keeps_the_release(self) -> None:
        release_id = self._release()
        first = create_task(
            self.layout,
            "First",
            ["A"],
            ["B"],
            repo_id="main",
            release_id=release_id,
        )
        create_task(
            self.layout,
            "Second",
            ["A"],
            ["B"],
            repo_id="main",
            release_id=release_id,
        )

        run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_cancel",
            {"task_id": first["id"]},
        )

        stored = load_release(self.layout, release_id)
        assert stored is not None
        self.assertEqual(stored["status"], "running")

    def test_a_cancelled_task_is_not_accepted_for_work(self) -> None:
        task = self._task(status="running")
        spec = self.layout.artifact(specs.spec_path(task["id"]))
        write_text(spec, "# Task\n")

        run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_cancel",
            {"task_id": task["id"]},
        )

        for operation in ("task_retry", "task_restart", "task_process"):
            with self.assertRaises(ValueError):
                run_operation(
                    self.settings,
                    self.ledger,
                    self.project,
                    operation,
                    {"task_id": task["id"]},
                )

    def test_a_marked_document_blocks_work_even_without_the_status(
        self,
    ) -> None:
        task = self._task(status="pending")
        spec = self.layout.artifact(specs.spec_path(task["id"]))
        write_text(spec, specs.CANCEL_NOTE + "\n# Task\n")

        self.assertTrue(specs.cancelled(self.layout, task))
        with self.assertRaises(ValueError):
            run_operation(
                self.settings,
                self.ledger,
                self.project,
                "task_process",
                {"task_id": task["id"]},
            )

    def test_an_implicit_operation_targets_the_running_task(self) -> None:
        running = self._task(status="running")
        newer = create_task(
            self.layout,
            "Newer work",
            ["A"],
            ["B"],
            repo_id="main",
            task_id="20260101000001_newer",
        )
        update_task(self.layout, newer["id"], status="review")

        run_operation(
            self.settings,
            self.ledger,
            self.project,
            "task_retry",
            {},
        )

        running_stored = get_task(self.layout, running["id"])
        newer_stored = get_task(self.layout, newer["id"])
        assert running_stored is not None
        assert newer_stored is not None
        self.assertEqual(running_stored["status"], "pending")
        self.assertEqual(newer_stored["status"], "review")

    def test_every_documented_operation_is_unique(self) -> None:
        self.assertEqual(len(OPERATIONS), len(set(OPERATIONS)))


if __name__ == "__main__":
    unittest.main()
