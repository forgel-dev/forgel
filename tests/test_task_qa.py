from __future__ import annotations

import os
import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.artifacts import write_text
from forgel.capabilities import Capability
from forgel.config import Settings
from forgel.environment import Environment, render_environment
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.task_qa import _run_local, run_task_qa
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

    def test_documentation_only_task_skips_executable_checks(self) -> None:
        task = self._task(
            ["python", "-c", "raise SystemExit(1)"]
        )
        update_task(
            self.layout,
            task["id"],
            result={
                "files_changed": ["README.md"],
                "summary": "documented",
            },
        )
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "skipped")
        self.assertEqual(result.runtime, "documentation-only")
        self.assertEqual(result.commands, [])

    def test_local_checks_do_not_inherit_forgel_environment(self) -> None:
        argv = [
            sys.executable,
            "-c",
            "import os; print(os.environ.get("
            "'FORGEL_MODEL_API_KEY', 'MISSING'))",
        ]
        check = {"command": shlex.join(argv)}
        with patch.dict(
            os.environ, {"FORGEL_MODEL_API_KEY": "secret"}, clear=False
        ):
            results = _run_local(
                self.layout, None, "main", [check]
            )
        _check, code, output = results[0]
        self.assertEqual(code, 0)
        self.assertIn("MISSING", output)
        self.assertNotIn("secret", output)

    def _environment(
        self, command: str, e2e: tuple[str, ...] = ()
    ) -> None:
        write_text(
            self.layout.control / "environment.yaml",
            render_environment(
                Environment(
                    image="python:3.12-slim",
                    test=(command,),
                    e2e=e2e,
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
        self.assertEqual(result.failure_kind, "environment")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["failure"]["kind"], "environment"
        )
        self.assertIn("task QA failed", stored["result"]["summary"])

    def _add_code_repo(
        self, depends_on: list[str] | None = None
    ) -> Path:
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                },
                {
                    "id": "code",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": list(depends_on or []),
                },
            ],
        )
        repo = self.layout.repo_path("code")
        repo.mkdir(parents=True, exist_ok=True)
        return repo

    def test_task_checks_run_in_the_task_repository(self) -> None:
        code = self._add_code_repo()
        self._environment(
            "python -c \"from pathlib import Path; "
            "Path('env.marker').write_text('env')\""
        )
        task = create_task(
            self.layout,
            "Client change",
            ["Do it"],
            ["It is done"],
            repo_id="code",
            checks=[
                {
                    "criterion": "task marker",
                    "command": [
                        "python",
                        "-c",
                        "from pathlib import Path; "
                        "Path('task.marker').write_text('task')",
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
        self.assertEqual(result.status, "pass", result.output)
        self.assertTrue((self.layout.root / "env.marker").exists())
        self.assertFalse((code / "env.marker").exists())
        self.assertTrue((code / "task.marker").exists())
        self.assertFalse((self.layout.root / "task.marker").exists())
        by_criterion = {item["criterion"]: item for item in result.checks}
        self.assertEqual(
            by_criterion["environment test"]["workdir"],
            str(self.layout.root),
        )
        self.assertEqual(
            by_criterion["task marker"]["workdir"], str(code)
        )
        self.assertEqual(by_criterion["task marker"]["repo"], "code")

    def test_a_task_module_check_runs_in_the_task_repository(self) -> None:
        code = self._add_code_repo()
        tests = code / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_cli.py").write_text(
            "import unittest\n"
            "\n"
            "class ClientTest(unittest.TestCase):\n"
            "    def test_client(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        task = create_task(
            self.layout,
            "Client change",
            ["Do it"],
            ["It is done"],
            repo_id="code",
            checks=[
                {
                    "criterion": "The client tests pass",
                    "command": [
                        "python",
                        "-m",
                        "unittest",
                        "tests.test_cli",
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
        self.assertEqual(result.status, "pass", result.output)
        self.assertNotIn("ModuleNotFoundError", result.output)

    def test_an_e2e_failure_returns_to_the_coder(self) -> None:
        self._environment(
            "python -c \"import sys; sys.exit(3)\"",
            e2e=("python -c \"import sys; sys.exit(4)\"",),
        )
        task = self._task([])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.failure_kind, "code")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["failure"]["kind"], "qa"
        )
        e2e = next(
            item
            for item in stored["result"]["qa"]["checks"]
            if item["scope"] == "e2e"
        )
        self.assertEqual(e2e["verdict"], "fail")

    def test_a_required_e2e_missing_is_a_project_failure(self) -> None:
        self._add_code_repo(depends_on=["main"])
        self._environment("python -c \"print('environment')\"")
        task = self._task([])
        result = run_task_qa(
            self.settings,
            self.ledger,
            self.project,
            task,
            log=lambda _m: None,
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.failure_kind, "environment")
        self.assertIn("needs a program e2e", result.output)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["failure"]["kind"], "environment"
        )

    def test_a_deferred_mobile_e2e_is_skipped_not_failing(self) -> None:
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "mobile",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                }
            ],
        )
        self._environment("python -c \"print('environment')\"")
        task = self._task([])
        missing = Capability(
            "mobile-simulator",
            False,
            "no simulator",
            "install one",
        )
        with patch(
            "forgel.task_qa.capabilities.unavailable",
            return_value=[missing],
        ):
            result = run_task_qa(
                self.settings,
                self.ledger,
                self.project,
                task,
                log=lambda _m: None,
            )
        self.assertEqual(result.status, "pass", result.output)
        self.assertEqual(result.failure_kind, "")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        skipped = [
            item
            for item in stored["result"]["qa"]["checks"]
            if item["verdict"] == "skipped"
        ]
        self.assertTrue(skipped)
        self.assertIn("install one", skipped[0]["output"])

    def test_an_unavailable_mobile_e2e_is_not_a_code_failure(self) -> None:
        set_entries(
            self.layout,
            [
                {
                    "id": "main",
                    "role": "mobile",
                    "provider": "local",
                    "url": "",
                    "depends_on": [],
                }
            ],
        )
        self._environment(
            "python -c \"print('environment')\"",
            e2e=("python -c \"import sys; sys.exit(3)\"",),
        )
        task = self._task([])
        missing = Capability(
            "mobile-simulator",
            False,
            "no simulator",
            "install one",
        )
        with patch(
            "forgel.task_qa.capabilities.unavailable",
            return_value=[missing],
        ):
            result = run_task_qa(
                self.settings,
                self.ledger,
                self.project,
                task,
                log=lambda _m: None,
            )
        self.assertEqual(result.status, "pass", result.output)
        self.assertEqual(result.failure_kind, "")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertNotIn("failure", stored["result"])
        e2e = [
            item
            for item in stored["result"]["qa"]["checks"]
            if item["scope"] == "e2e"
        ]
        self.assertTrue(e2e)
        self.assertEqual(e2e[0]["verdict"], "skipped")

    def test_mounts_expose_sibling_repositories_to_checks(self) -> None:
        code = self._add_code_repo()
        write_text(
            self.layout.control / "environment.yaml",
            render_environment(
                Environment(
                    image="python:3.12-slim",
                    mounts=("code",),
                    test=("python -c \"print('environment')\"",),
                    e2e=("python -c \"print('e2e')\"",),
                )
            ),
        )
        task = create_task(
            self.layout,
            "Mounted check",
            ["Do it"],
            ["It is done"],
            repo_id="code",
            checks=[
                {
                    "criterion": "The sibling repository is mounted",
                    "command": [
                        "python",
                        "-c",
                        "import os; print("
                        "os.environ.get('FORGEL_REPO_CODE', 'MISSING'))",
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
        self.assertEqual(result.status, "pass", result.output)
        self.assertIn(str(code), result.output)

    def test_a_cross_repository_check_is_a_spec_defect(self) -> None:
        self._add_code_repo()
        tests = self.layout.repo_path("main") / "tests"
        tests.mkdir(parents=True, exist_ok=True)
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_cli.py").write_text("", encoding="utf-8")
        task = create_task(
            self.layout,
            "Client change",
            ["Do it"],
            ["It is done"],
            repo_id="code",
            checks=[
                {
                    "criterion": "The client tests pass",
                    "command": [
                        "python",
                        "-m",
                        "unittest",
                        "tests.test_cli",
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
        self.assertEqual(result.failure_kind, "spec")
        self.assertIn("exists in repository 'main'", result.output)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["failure"]["kind"], "spec"
        )
        self.assertFalse(stored["result"].get("rework_count"))

    def test_failure_feedback_carries_the_command_and_output(self) -> None:
        task = create_task(
            self.layout,
            "Failing check",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            checks=[
                {
                    "criterion": "Fails loudly",
                    "command": [
                        "python",
                        "-c",
                        "import sys; print('CHECK-OUTPUT'); sys.exit(4)",
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
        failing = next(
            item
            for item in stored["result"]["qa"]["checks"]
            if item["verdict"] == "fail"
        )
        self.assertEqual(failing["criterion"], "Fails loudly")
        self.assertEqual(
            failing["workdir"], str(self.layout.repo_path("main"))
        )
        self.assertIn("CHECK-OUTPUT", failing["output"])
        from forgel.daemon import _feedback_from

        feedback = "\n".join(_feedback_from(stored["result"]))
        self.assertIn("CHECK-OUTPUT", feedback)
        self.assertIn("command:", feedback)
        self.assertIn("cwd:", feedback)

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
