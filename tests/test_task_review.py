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
    MAX_REVIEW_RETRIES,
    _review_prompt,
    accept_parked_green_tasks,
    accept_task,
    detected_test_removals,
    process_task_result,
    reject_task,
    rerun_review,
    retry_failed_pushes,
    run_task_review,
    task_diff,
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
PASS_PARTIAL = json.dumps(
    {
        "verdict": "pass",
        "summary": "Looks fine.",
        "requirements": [],
        "blocking": [],
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

    def _task(
        self, status: str = "done", checks: list[dict] | None = None
    ) -> dict:
        task = create_task(
            self.layout,
            "Do it",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            test_command=["python", "-c", "print('task')"],
            checks=checks,
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

    def test_diff_uses_only_attributed_commits(self) -> None:
        write_text(self.repo / "app.py", "value = 2\n")
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "agent change",
        )
        agent_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        write_text(self.repo / "other.py", "unrelated = True\n")
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "unrelated",
        )
        task = self._task()
        update_task(
            self.layout,
            task["id"],
            result={
                "summary": "implemented",
                "files_changed": ["app.py"],
                "git": {"commits": [agent_sha]},
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        diff = task_diff(self.layout, stored)
        self.assertIn("value = 2", diff)
        self.assertNotIn("unrelated", diff)

    def test_a_restored_test_is_not_reported_as_removed(self) -> None:
        test_file = self.repo / "tests" / "test_sample.py"
        test_file.parent.mkdir()
        test_file.write_text(
            "def test_old():\n    assert True\n", encoding="utf-8"
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "add test",
        )
        first = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        test_file.write_text(
            "def test_new():\n    assert True\n", encoding="utf-8"
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "rename test",
        )
        second = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        test_file.write_text(
            "def test_old():\n    assert True\n\n"
            "def test_new():\n    assert True\n",
            encoding="utf-8",
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "restore test",
        )
        third = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        task = self._task()
        update_task(
            self.layout,
            task["id"],
            result={
                **task["result"],
                "files_changed": ["tests/test_sample.py"],
                "git": {
                    "base": first,
                    "head": third,
                    "commits": [first, second, third],
                },
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            detected_test_removals(self.layout, stored), []
        )

    def test_a_deleted_test_is_still_reported(self) -> None:
        test_file = self.repo / "tests" / "test_sample.py"
        test_file.parent.mkdir()
        test_file.write_text(
            "def test_old():\n    assert True\n", encoding="utf-8"
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "add test",
        )
        first = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        test_file.write_text(
            "def test_new():\n    assert True\n", encoding="utf-8"
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "delete test",
        )
        second = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        task = self._task()
        update_task(
            self.layout,
            task["id"],
            result={
                **task["result"],
                "files_changed": ["tests/test_sample.py"],
                "git": {
                    "base": first,
                    "head": second,
                    "commits": [first, second],
                },
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        removals = detected_test_removals(self.layout, stored)
        self.assertTrue(removals)
        self.assertTrue(
            any("test_old" in item for item in removals)
        )

    def test_review_prompt_for_noop_uses_current_state(self) -> None:
        write_text(self.repo / "README.md", "README-MARKER\n")
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-s", "-m", "document it",
        )
        task = self._task()
        update_task(
            self.layout,
            task["id"],
            result={
                "summary": "already satisfied",
                "files_changed": [],
                "git": {},
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        prompt = _review_prompt(self.layout, stored)
        self.assertIn("README-MARKER", prompt)
        self.assertIn("Signed-off-by:", prompt)
        self.assertIn(
            "No product commits were attributed", prompt
        )

    def test_reviewer_retries_after_tool_markup(self) -> None:
        task = self._task()
        markup = (
            "<｜｜DSML｜｜ calls><｜｜DSML｜｜ invoke name=\"verdict\">"
            "</｜｜DSML｜｜ invoke></｜｜DSML｜｜ calls>"
        )
        client = ScriptedModelClient([markup, PASS])
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            client,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)
        self.assertIn(
            "tool-call markup", client.requests[1][-1].content
        )

    def test_reviewer_can_read_current_files(self) -> None:
        task = self._task()
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"action": "read_file", "path": "app.py"}
                ),
                PASS,
            ]
        )
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            client,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)
        self.assertIn(
            "value = 1", client.requests[1][-1].content
        )

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

    def test_each_rework_records_its_own_review_event(self) -> None:
        task = self._task()
        for attempt in (0, 1):
            stored = get_task(self.layout, task["id"])
            assert stored is not None
            data = dict(stored.get("result") or {})
            data["rework_count"] = attempt
            update_task(self.layout, task["id"], result=data)
            current = get_task(self.layout, task["id"])
            assert current is not None
            run_task_review(
                self.settings,
                self.ledger,
                self.project,
                current,
                ScriptedModelClient([FAIL]),
                log=lambda _m: None,
            )
        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "task_review"
        ]
        self.assertEqual(len(events), 2)
        reworks = [
            json.loads(event["payload"])["rework"]
            for event in events
        ]
        self.assertEqual(reworks, [0, 1])

    def test_an_errored_review_can_be_rerun(self) -> None:
        settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
            task_qa=False,
            task_review=True,
            task_accept="auto",
        )
        task = self._task()
        data = dict(task.get("result") or {})
        data["review"] = {
            "status": "error",
            "summary": "the review did not cover every acceptance criterion",
            "requirements": [],
            "blocking": [],
            "report": "",
        }
        update_task(
            self.layout,
            task["id"],
            status="review",
            result=data,
        )
        updated = rerun_review(
            settings,
            self.ledger,
            self.project,
            task["id"],
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        self.assertEqual(updated["status"], "done")
        self.assertEqual(
            updated["result"]["review"]["status"], "pass"
        )

    def test_only_a_review_task_can_be_rereviewed(self) -> None:
        task = create_task(
            self.layout,
            "Waiting",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            test_command=[],
        )
        with self.assertRaises(ValueError):
            rerun_review(
                self.settings,
                self.ledger,
                self.project,
                task["id"],
                ScriptedModelClient([PASS]),
                log=lambda _m: None,
            )

    def test_a_verdict_must_cover_every_criterion(self) -> None:
        task = self._task()
        client = ScriptedModelClient([PASS_PARTIAL, PASS])
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            client,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)
        self.assertEqual(len(client.requests), 2)
        self.assertIn(
            "cover every acceptance criterion",
            client.requests[1][-1].content,
        )

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

    def test_auto_policy_accepts_a_task_parked_for_a_human(self) -> None:
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
        task = self._task(status="review")
        update_task(
            self.layout,
            task["id"],
            status="review",
            result={
                **task["result"],
                "qa": {"status": "pass", "review_required": False},
                "review": {"status": "pass"},
                "acceptance": {
                    "status": "pending",
                    "reason": "review passed; acceptance required",
                },
            },
        )
        accepted = accept_parked_green_tasks(
            self.settings, self.ledger, self.project, self.layout
        )
        self.assertEqual(accepted, [task["id"]])
        final = get_task(self.layout, task["id"])
        assert final is not None
        self.assertEqual(final["status"], "done")
        self.assertEqual(
            final["result"]["acceptance"]["actor"], "auto"
        )

    def test_auto_policy_accepts_a_review_only_task(self) -> None:
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
        task = self._task(status="review")
        update_task(
            self.layout,
            task["id"],
            status="review",
            result={
                **task["result"],
                "qa": {"status": "pass", "review_required": True},
                "review": {"status": "pass"},
                "acceptance": {
                    "status": "pending",
                    "reason": "acceptance checks require review",
                },
            },
        )
        accepted = accept_parked_green_tasks(
            self.settings, self.ledger, self.project, self.layout
        )
        self.assertEqual(accepted, [task["id"]])
        final = get_task(self.layout, task["id"])
        assert final is not None
        self.assertEqual(final["status"], "done")
        self.assertTrue(final["result"]["qa"]["review_required"])

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

    def test_qa_failure_quarantines_dependent_tasks(self) -> None:
        write_text(
            self.layout.control / "environment.yaml",
            render_environment(
                Environment(
                    image="python:3.12-slim",
                    test=(
                        "python -c \"import sys; sys.exit(3)\"",
                    ),
                )
            ),
        )
        first = create_task(
            self.layout,
            "First",
            ["Write a note"],
            ["The note exists"],
            repo_id="main",
        )
        second = create_task(
            self.layout,
            "Second",
            ["Write another note"],
            ["The note exists"],
            repo_id="main",
            depends_on=[first["id"]],
        )
        responses = [
            json.dumps(
                {
                    "action": "write_file",
                    "path": "note.md",
                    "content": "# Note\n",
                }
            ),
            json.dumps({"action": "done", "summary": "added the note"}),
        ]
        run_once(
            self.settings,
            self.ledger,
            log=lambda _m: None,
            client=ScriptedModelClient(responses),
        )
        stored = get_task(self.layout, first["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["failure"]["kind"], "environment"
        )
        dependent = get_task(self.layout, second["id"])
        assert dependent is not None
        self.assertEqual(dependent["status"], "blocked")
        self.assertEqual(
            dependent["result"]["blocked_by"], first["id"]
        )

    def _deleted_test_diff(self) -> tuple[str, str]:
        test_dir = self.repo / "tests"
        test_dir.mkdir(exist_ok=True)
        (test_dir / "test_old.py").write_text(
            "def test_old():\n    assert True\n", encoding="utf-8"
        )
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "add test",
        )
        base = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        (test_dir / "test_old.py").unlink()
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "remove test",
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.repo, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return base, head

    def test_a_deleted_test_without_justification_fails_review(
        self,
    ) -> None:
        base, head = self._deleted_test_diff()
        task = self._task()
        data = dict(task.get("result") or {})
        data["git"] = {"base": base, "head": head}
        update_task(self.layout, task["id"], result=data)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            stored,
            None,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        self.assertTrue(
            any(
                "tests/test_old.py" in item
                for item in result.blocking
            )
        )

    def test_a_justified_deleted_test_goes_to_the_reviewer(self) -> None:
        base, head = self._deleted_test_diff()
        task = self._task()
        data = dict(task.get("result") or {})
        data["git"] = {"base": base, "head": head}
        data["test_removals"] = [
            {
                "test": "tests/test_old.py",
                "reason": "removed",
                "replacement": "",
            }
        ]
        update_task(self.layout, task["id"], result=data)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            stored,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)

    def test_auto_acceptance_requires_a_passing_review(self) -> None:
        self.settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
            task_qa=True,
            task_review=False,
            task_accept="auto",
        )
        task = self._task()
        process_task_result(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([]),
            log=lambda _m: None,
        )
        final = get_task(self.layout, task["id"])
        assert final is not None
        self.assertEqual(final["status"], "review")
        self.assertEqual(
            final["result"]["acceptance"]["status"], "pending"
        )

    def test_reviewer_handles_a_batch_of_actions_and_a_verdict(
        self,
    ) -> None:
        task = self._task()
        client = ScriptedModelClient(
            [
                json.dumps(
                    [
                        {"action": "list_files", "path": "."},
                        json.loads(PASS),
                    ]
                )
            ]
        )
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            client,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "pass", result.summary)

    def test_a_review_without_requirements_is_an_error(self) -> None:
        task = self._task()
        result = run_task_review(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient(
                [PASS_PARTIAL] * (MAX_REVIEW_RETRIES + 1)
            ),
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "error")
        self.assertIn("did not cover", result.summary)

    def test_review_only_checks_are_accepted_after_a_green_review(
        self,
    ) -> None:
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
        task = self._task(
            checks=[
                {
                    "criterion": "Docs are accurate",
                    "verification": "review",
                }
            ]
        )
        process_task_result(
            self.settings,
            self.ledger,
            self.project,
            task,
            ScriptedModelClient([PASS]),
            log=lambda _m: None,
        )
        final = get_task(self.layout, task["id"])
        assert final is not None
        self.assertEqual(final["status"], "done")
        self.assertTrue(
            final["result"]["qa"]["review_required"]
        )
        self.assertEqual(
            final["result"]["acceptance"]["actor"], "auto"
        )

    def test_a_rejected_review_goes_back_for_rework(self) -> None:
        settings = Settings(
            home=self.home,
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
            task_qa=True,
            task_review=True,
            task_accept="human",
            task_reworks=1,
            task_arbiter=False,
        )
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
            FAIL,
            json.dumps(
                {
                    "decisions": [
                        {
                            "index": 0,
                            "valid": True,
                            "scope": "code",
                            "reason": "the change does nothing",
                        },
                        {
                            "index": 1,
                            "valid": True,
                            "scope": "code",
                            "reason": "the requirement is missing",
                        },
                    ]
                }
            ),
            json.dumps(
                {
                    "action": "write_file",
                    "path": "note.md",
                    "content": "# Note\n\nFixed.\n",
                }
            ),
            json.dumps(
                {"action": "done", "summary": "addressed the review"}
            ),
            PASS,
        ]
        client = ScriptedModelClient(responses)
        run_once(
            settings, self.ledger, log=lambda _m: None, client=client
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(stored["result"]["rework_count"], 1)
        self.assertTrue(stored["result"]["feedback"])
        run_once(
            settings, self.ledger, log=lambda _m: None, client=client
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "review", stored["result"])
        self.assertEqual(
            stored["result"]["review"]["status"], "pass"
        )
        prompts = [
            request[1].content
            for request in client.requests
            if len(request) > 1
        ]
        self.assertTrue(
            any(
                "Previous attempt feedback" in prompt
                for prompt in prompts
            )
        )

    def test_acceptance_pushes_the_commit_to_the_remote(self) -> None:
        bare = self.home / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(bare)], check=True
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )
        self._git("push", "-u", "origin", "main")
        write_text(self.repo / "app.py", "value = 2\n")
        self._git("add", "-A")
        self._git(
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "accepted change",
        )
        task = self._task()
        updated = accept_task(
            self.settings,
            self.ledger,
            self.project,
            task,
            actor="tester",
        )
        self.assertEqual(updated["status"], "done")
        log = subprocess.run(
            ["git", "--git-dir", str(bare), "log", "--format=%s", "main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertIn("accepted change", log)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["push"]["status"], "pushed"
        )

    def test_a_failed_push_is_retried_after_acceptance(self) -> None:
        bare = self.home / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-q", str(bare)], check=True
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        )
        self._git("push", "-u", "origin", "main")
        write_text(self.repo / "app.py", "value = 2\n")
        self._git("add", "-A")
        self._git(
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "accepted change",
        )
        task = self._task()
        update_task(
            self.layout,
            str(task["id"]),
            status="done",
            result={
                "acceptance": {
                    "status": "accepted",
                    "actor": "auto",
                    "at": "2026-11-20T00:00:00+00:00",
                    "notes": "",
                },
                "files_changed": ["app.py"],
                "push": {
                    "status": "failed",
                    "repo": "main",
                    "branch": "",
                    "detail": "ssh: Could not resolve hostname",
                    "attempts": 1,
                    "next_at": "",
                },
            },
        )

        pushed = retry_failed_pushes(
            self.settings, self.ledger, self.project
        )

        self.assertEqual(pushed, [task["id"]])
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["push"]["status"], "pushed"
        )
        self.assertEqual(stored["result"]["push"]["attempts"], 2)
        log = subprocess.run(
            ["git", "--git-dir", str(bare), "log", "--format=%s", "main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertIn("accepted change", log)

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
