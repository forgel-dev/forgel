from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.environment import Environment, render_environment
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.task_qa import run_task_qa
from forgel.tasks import create_task, get_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]


class TaskQATest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
            task_qa=True,
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "QA demo",
            "A demo project.",
            mode="brownfield",
        )
        self.project = self.ledger.get_project(self.project_id)
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
        (self.layout.repo_path("main")).mkdir(parents=True)

    def _task(self, test_command: list[str]) -> dict:
        task = create_task(
            self.layout,
            "Do work",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            test_command=test_command,
        )
        update_task(self.layout, task["id"], status="done")
        return task

    def _environment(self, command: str) -> None:
        write_text(
            self.layout.control / "environment.yaml",
            render_environment(
                Environment(
                    image="python:3.12-slim", test=(command,)
                )
            ),
        )

    def test_green_environment_passes(self) -> None:
        self._environment("python -c \"print('ok')\"")
        task = self._task([])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.output)
        self.assertTrue(
            (self.layout.root / result.report).exists()
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertEqual(stored["result"]["qa"]["status"], "pass")
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("task_qa", stages)

    def test_red_environment_fails_the_task(self) -> None:
        self._environment("python -c \"import sys; sys.exit(3)\"")
        task = self._task([])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertIn("task QA failed", stored["result"]["summary"])

    def test_the_task_test_runs_alongside_the_environment_gate(self) -> None:
        self._environment("python -c \"print('gate')\"")
        task = self._task(
            ["python", "-c", "import sys; sys.exit(5)"]
        )
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(len(result.commands), 2)
        self.assertIn("environment.yaml", result.runtime)

    def test_task_test_command_is_the_fallback(self) -> None:
        task = self._task(["python", "-c", "print('fallback')"])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.output)
        self.assertNotIn("environment.yaml", result.runtime)

    def test_a_task_check_is_executed(self) -> None:
        task = create_task(
            self.layout,
            "Check it",
            ["Do it"],
            ["It passes"],
            repo_id="main",
            checks=[
                {
                    "criterion": "The check passes",
                    "command": ["python", "-c", "print('check')"],
                }
            ],
        )
        update_task(self.layout, task["id"], status="done")
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.output)
        self.assertTrue(
            any(
                item["criterion"] == "The check passes"
                and item["verdict"] == "pass"
                for item in result.checks
            )
        )

    def test_a_failing_check_fails_qa(self) -> None:
        task = create_task(
            self.layout,
            "Check it",
            ["Do it"],
            ["It passes"],
            repo_id="main",
            checks=[
                {
                    "criterion": "The check passes",
                    "command": [
                        "python",
                        "-c",
                        "import sys; sys.exit(3)",
                    ],
                }
            ],
        )
        update_task(self.layout, task["id"], status="done")
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["failure"]["kind"], "qa"
        )

    def test_a_review_only_check_requires_review(self) -> None:
        task = create_task(
            self.layout,
            "Review it",
            ["Write docs"],
            ["The prose is accurate"],
            repo_id="main",
            checks=[
                {
                    "criterion": "The prose is accurate",
                    "verification": "review",
                }
            ],
        )
        update_task(self.layout, task["id"], status="done")
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "review")
        self.assertTrue(result.review_required)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertTrue(
            stored["result"]["qa"]["review_required"]
        )

    def test_without_anything_to_run_qa_is_skipped(self) -> None:
        task = self._task([])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "skipped")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")


if __name__ == "__main__":
    unittest.main()
