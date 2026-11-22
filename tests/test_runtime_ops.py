from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.projects import create_project
from forgel.release_train import save_release
from forgel.runtime_ops import OPERATIONS, run_operation
from forgel.tasks import create_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]


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

    def test_every_documented_operation_is_unique(self) -> None:
        self.assertEqual(len(OPERATIONS), len(set(OPERATIONS)))


if __name__ == "__main__":
    unittest.main()
