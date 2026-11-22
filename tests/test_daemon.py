from __future__ import annotations

import http.client
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from forgel import tasks
from forgel.approvals import awaits_approval, record_approval
from forgel.config import Settings
from forgel.daemon import (
    _classify_crash,
    _feedback_from,
    handle_failure,
    project_is_done,
    run_daemon,
    run_once,
)
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger, new_project_id
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import create_task, get_task

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC = {
    "problem": "The work is missing.",
    "outcome": "The work exists.",
    "scope": ["the work"],
    "non_goals": [],
    "requirements": ["Do the work"],
    "acceptance": ["The work is present"],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The work is present"],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "affected_files": ["work.py"],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
    "checks": [
        {"criterion": "The work is present", "verification": "review"}
    ],
    "test_command": [],
    "external_dependencies": [],
}


class DaemonTest(unittest.TestCase):
    def _settings(self, tmp: str) -> Settings:
        return Settings(
            home=Path(tmp),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )

    def _failed_task(self, tmp: str):
        base = self._settings(tmp)
        settings = Settings(
            home=base.home,
            registry_path=base.registry_path,
            templates_path=base.templates_path,
            jurisdiction_path=base.jurisdiction_path,
            qa_runtime="local",
            controller=True,
        )
        ledger = Ledger(settings.db_path)
        self.addCleanup(ledger.close)
        project_id = create_project(
            settings, ledger, "Controller", "A brief.", mode="brownfield"
        )
        project = ledger.get_project(project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        set_entries(
            layout,
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
        task = create_task(
            layout, "Do work", ["A"], ["B"], repo_id="main"
        )
        tasks.update_task(
            layout,
            task["id"],
            status="failed",
            result={
                "summary": "task QA failed",
                "qa": {"status": "fail"},
                "failure": {
                    "kind": "code",
                    "message": "the test failed",
                    "retryable": False,
                },
            },
        )
        return settings, ledger, project, layout, task

    def test_once_processes_a_pending_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id, "hello-web", "A minimal web app.", str(workspace)
            )

            cycles = run_daemon(
                settings, ledger, once=True, log=lambda message: None
            )

            self.assertEqual(cycles, 1)
            self.assertFalse(project_is_done(ledger, project_id))
            self.assertTrue(awaits_approval(ledger, project_id))

            record_approval(
                ledger, project_id, scope="staging", actor="test"
            )
            run_daemon(settings, ledger, once=True, log=lambda message: None)

            self.assertTrue(project_is_done(ledger, project_id))
            self.assertTrue(
                (workspace / "docs/program/iterations/1/close.md").exists()
            )

    def test_infrastructure_failure_is_retried_then_quarantined(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            settings = Settings(
                home=settings.home,
                registry_path=settings.registry_path,
                templates_path=settings.templates_path,
                jurisdiction_path=settings.jurisdiction_path,
                qa_runtime="local",
                task_retries=1,
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project_id = create_project(
                settings,
                ledger,
                "Retry demo",
                "A demo brief.",
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            assert project is not None
            layout = ProjectLayout.detect(project["workspace"])
            set_entries(
                layout,
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
            repo = layout.repo_path("main")
            repo.mkdir(parents=True)
            (repo / "README.md").write_text("demo\n", encoding="utf-8")
            subprocess.run(
                ["git", "init", "-q"], cwd=repo, check=True
            )
            subprocess.run(
                ["git", "add", "-A"], cwd=repo, check=True
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=T",
                    "-c",
                    "user.email=t@example.com",
                    "commit",
                    "-q",
                    "-m",
                    "initial",
                ],
                cwd=repo,
                check=True,
            )
            task = create_task(
                layout, "Do work", ["A"], ["B"], repo_id="main"
            )
            client = ScriptedModelClient([])
            run_once(settings, ledger, log=lambda _m: None, client=client)
            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "pending")
            self.assertEqual(stored["result"]["attempts"], 1)
            self.assertTrue(stored["result"]["retry_after"])
            # The backoff is not elapsed: the task is not picked up.
            self.assertIsNone(tasks.next_pending_task(layout))
            # Simulate the backoff elapsing.
            data = dict(stored["result"])
            data["retry_after"] = "2000-01-01T00:00:00+00:00"
            tasks.update_task(layout, task["id"], result=data)
            run_once(settings, ledger, log=lambda _m: None, client=client)
            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "failed")
            self.assertEqual(
                stored["result"]["failure"]["kind"], "infrastructure"
            )

    def test_an_incomplete_read_is_an_infrastructure_failure(self) -> None:
        failure = _classify_crash(http.client.IncompleteRead(b""))
        self.assertEqual(failure["kind"], "infrastructure")

    def test_qa_feedback_carries_the_command_workdir_and_output(
        self,
    ) -> None:
        feedback = "\n".join(
            _feedback_from(
                {
                    "qa": {
                        "failure_kind": "code",
                        "checks": [
                            {
                                "criterion": "The client tests pass",
                                "verdict": "fail",
                                "command": (
                                    "python -m unittest tests.test_cli"
                                ),
                                "exit_code": 1,
                                "repo": "code",
                                "workdir": "/project/repos/code",
                                "output": (
                                    "ModuleNotFoundError: No module "
                                    "named 'tests.test_cli'"
                                ),
                            }
                        ],
                    }
                }
            )
        )
        self.assertIn("python -m unittest tests.test_cli", feedback)
        self.assertIn("/project/repos/code", feedback)
        self.assertIn("ModuleNotFoundError", feedback)
        self.assertIn("repository: code", feedback)

    def test_a_spec_failure_rewrites_the_spec_without_a_coder_rework(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = self._settings(tmp)
            settings = Settings(
                home=base.home,
                registry_path=base.registry_path,
                templates_path=base.templates_path,
                jurisdiction_path=base.jurisdiction_path,
                qa_runtime="local",
                task_reworks=2,
            )
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project_id = create_project(
                settings,
                ledger,
                "Spec rewrite",
                "A demo brief.",
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            assert project is not None
            layout = ProjectLayout.detect(project["workspace"])
            set_entries(
                layout,
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
            repo = layout.repo_path("main")
            repo.mkdir(parents=True, exist_ok=True)
            (repo / "README.md").write_text("demo\n", encoding="utf-8")
            task = create_task(
                layout, "Do work", ["A"], ["B"], repo_id="main"
            )
            tasks.update_task(
                layout,
                task["id"],
                status="failed",
                result={
                    "summary": "task QA failed: bad check",
                    "failure": {
                        "kind": "spec",
                        "message": (
                            "check command references 'tests.test_cli', "
                            "which exists in repository 'main' but not in "
                            "the task repository 'code'"
                        ),
                    },
                },
            )
            client = ScriptedModelClient([json.dumps(SPEC)])
            handle_failure(
                settings,
                ledger,
                project,
                layout,
                task["id"],
                client,
                lambda _m: None,
            )
            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "pending")
            self.assertEqual(stored["result"]["spec_rework_count"], 1)
            self.assertFalse(stored["result"].get("rework_count"))
            self.assertTrue(
                layout.artifact(stored["spec"]).exists()
            )

    def test_the_controller_reworks_a_failed_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings, ledger, project, layout, task = (
                self._failed_task(tmp)
            )
            client = ScriptedModelClient(
                [
                    json.dumps(
                        {
                            "operation": "rework",
                            "reason": "the test is missing",
                            "feedback": ["Add the test"],
                        }
                    )
                ]
            )

            handle_failure(
                settings,
                ledger,
                project,
                layout,
                task["id"],
                client,
                lambda _m: None,
            )

            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "pending")
            self.assertEqual(
                stored["result"]["feedback"], ["Add the test"]
            )

    def test_the_controller_asks_the_owner_as_the_last_resort(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings, ledger, project, layout, task = (
                self._failed_task(tmp)
            )
            question = "Which behavior is wanted when the profile is unreadable?"
            client = ScriptedModelClient(
                [
                    json.dumps(
                        {
                            "operation": "ask_user",
                            "question": question,
                        }
                    )
                ]
            )

            handle_failure(
                settings,
                ledger,
                project,
                layout,
                task["id"],
                client,
                lambda _m: None,
            )

            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "blocked")
            self.assertIn("needs the owner", stored["result"]["summary"])
            self.assertIn(question, stored["result"]["summary"])

    def test_an_environment_failure_drops_stale_rework_feedback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project_id = create_project(
                settings,
                ledger,
                "Env gate",
                "A demo brief.",
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            assert project is not None
            layout = ProjectLayout.detect(project["workspace"])
            set_entries(
                layout,
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
            task = create_task(
                layout, "Do work", ["A"], ["B"], repo_id="main"
            )
            tasks.update_task(
                layout,
                task["id"],
                status="failed",
                result={
                    "summary": "task QA failed: environment test",
                    "feedback": ["QA check failed: stale code check"],
                    "failure": {
                        "kind": "environment",
                        "message": "task QA failed: environment test",
                        "retryable": False,
                    },
                },
            )

            handle_failure(
                settings,
                ledger,
                project,
                layout,
                task["id"],
                None,
                lambda _m: None,
            )

            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "failed")
            self.assertNotIn("feedback", stored["result"])

    def test_peak_hours_defer_model_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            project_id = create_project(
                settings,
                ledger,
                "Peak demo",
                "A demo brief.",
                mode="brownfield",
            )
            project = ledger.get_project(project_id)
            assert project is not None
            layout = ProjectLayout.detect(project["workspace"])
            task = create_task(
                layout,
                "Do the work",
                ["Do it"],
                ["It is done"],
                repo_id="main",
            )
            logs: list[str] = []
            with patch(
                "forgel.daemon.peak.should_defer", return_value=True
            ):
                processed = run_once(
                    settings, ledger, log=logs.append
                )
            self.assertEqual(processed, [])
            stored = get_task(layout, task["id"])
            assert stored is not None
            self.assertEqual(stored["status"], "pending")
            self.assertTrue(any("paused" in line for line in logs))

    def test_duplicate_workspaces_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)
            workspace = settings.projects_dir / "shared"
            (workspace / ".forgel").mkdir(parents=True)
            (workspace / ".forgel" / "project.json").write_text(
                '{"mode": "brownfield", "repos": []}',
                encoding="utf-8",
            )
            ledger.create_project(
                "newer", "Newer", "A newer project.", str(workspace)
            )
            ledger.create_project(
                "older", "Older", "An older project.", str(workspace)
            )
            newer = ledger.get_project("newer")
            older = ledger.get_project("older")
            assert newer is not None and older is not None
            logs: list[str] = []
            with patch.object(
                ledger, "list_projects", return_value=[newer, older]
            ):
                processed = run_once(settings, ledger, log=logs.append)
            self.assertEqual(processed, [])
            self.assertTrue(
                any(
                    "duplicate workspace" in line and "older" in line
                    for line in logs
                )
            )

    def test_done_project_is_not_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings = self._settings(tmp)
            ledger = Ledger(settings.db_path)
            self.addCleanup(ledger.close)

            project_id = new_project_id("hello-web")
            workspace = settings.projects_dir / project_id
            ledger.create_project(
                project_id, "hello-web", "A minimal web app.", str(workspace)
            )

            run_daemon(settings, ledger, once=True, log=lambda message: None)
            record_approval(
                ledger, project_id, scope="staging", actor="test"
            )
            run_daemon(settings, ledger, once=True, log=lambda message: None)
            events = len(ledger.events(project_id))
            run_daemon(settings, ledger, once=True, log=lambda message: None)

            self.assertEqual(len(ledger.events(project_id)), events)


if __name__ == "__main__":
    unittest.main()
