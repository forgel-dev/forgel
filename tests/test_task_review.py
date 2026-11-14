from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.daemon import run_once
from forgel.environment import Environment, render_environment
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.task_review import (
    accept_task,
    process_task_result,
    reject_task,
    run_task_review,
)
from forgel.tasks import create_task, get_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]

PASS = json.dumps(
    {
        "verdict": "pass",
        "summary": "The change implements the requirements.",
        "requirements": [
            {"requirement": "Do it", "verdict": "pass", "note": ""}
        ],
        "blocking": [],
    }
)
FAIL = json.dumps(
    {
        "verdict": "fail",
        "summary": "The requirement is not met.",
        "requirements": [
            {"requirement": "Do it", "verdict": "fail", "note": "missing"}
        ],
        "blocking": ["The change does nothing"],
    }
)


class TaskReviewTest(unittest.TestCase):
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
            task_review=True,
            task_accept="human",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "Review demo",
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
        self.repo = self.layout.repo_path("main")
        self.repo.mkdir(parents=True)
        write_text(self.repo / "app.py", "value = 1\n")
        self._git("init", "-q", "-b", "main")
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "initial",
        )
        write_text(
            self.layout.control / "environment.yaml",
            render_environment(
                Environment(
                    image="python:3.12-slim",
                    test=("python -c \"print('ok')\"",),
                )
            ),
        )

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=self.repo, check=True,
            capture_output=True, text=True,
        )

    def _task(self, status: str = "done") -> dict:
        task = create_task(
            self.layout,
            "Do it",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            test_command=["python", "-c", "print('task')"],
        )
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        update_task(
            self.layout,
            task["id"],
            status=status,
            result={
                "summary": "implemented",
                "files_changed": ["app.py"],
                "git": {"base": sha, "head": sha},
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        return stored

    def test_review_pass_is_recorded(self) -> None:
        task = self._task()
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)
        self.assertTrue((self.layout.root / result.report).exists())
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["result"]["review"]["status"], "pass")
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("task_review", stages)

    def test_review_fail_fails_the_task(self) -> None:
        task = self._task()
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([FAIL]),
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertIn("task review failed", stored["result"]["summary"])

    def test_unusable_review_is_an_error_not_a_pass(self) -> None:
        task = self._task()
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient(["not json"]),
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "error")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")

    def test_process_requires_acceptance_after_a_green_review(self) -> None:
        task = self._task()
        process_task_result(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "review")
        self.assertEqual(
            stored["result"]["acceptance"]["status"], "pending"
        )
        accepted = accept_task(
            self.settings, self.ledger, self.project, stored,
            actor="tester", notes="looks good",
        )
        self.assertEqual(accepted["status"], "done")
        self.assertEqual(
            accepted["result"]["acceptance"]["status"], "accepted"
        )
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("task_accept", stages)

    def test_auto_acceptance_skips_the_review_gate(self) -> None:
        self.settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
            task_qa=True,
            task_review=True,
            task_accept="auto",
        )
        task = self._task()
        process_task_result(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertEqual(
            stored["result"]["acceptance"]["actor"], "auto"
        )

    def test_daemon_runs_qa_review_and_leaves_the_task_for_acceptance(
        self,
    ) -> None:
        task = create_task(
            self.layout,
            "Add a note",
            ["Create note.md"],
            ["The file exists"],
            repo_id="main",
            test_command=["python", "-c", "print('task')"],
        )
        responses = [
            json.dumps(
                {
                    "action": "write_file",
                    "path": "note.md",
                    "content": "# Note\n",
                }
            ),
            json.dumps(
                {"action": "done", "summary": "added the note"}
            ),
            PASS,
        ]
        processed = run_once(
            self.settings,
            self.ledger,
            log=lambda _m: None,
            client=ScriptedModelClient(responses),
        )
        self.assertIn(self.project_id, processed)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "review", stored["result"])
        self.assertEqual(
            stored["result"]["qa"]["status"], "pass"
        )
        self.assertEqual(
            stored["result"]["review"]["status"], "pass"
        )
        self.assertNotEqual(
            stored["result"]["git"]["base"],
            stored["result"]["git"]["head"],
        )
        accepted = accept_task(
            self.settings, self.ledger, self.project, stored,
            actor="tester", notes="accepted",
        )
        self.assertEqual(accepted["status"], "done")

    def test_rejecting_a_review_fails_the_task(self) -> None:
        task = self._task()
        process_task_result(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        rejected = reject_task(
            self.settings, self.ledger, self.project, stored,
            actor="tester", notes="wrong direction",
        )
        self.assertEqual(rejected["status"], "failed")
        self.assertIn("rejected", rejected["result"]["summary"])


if __name__ == "__main__":
    unittest.main()
