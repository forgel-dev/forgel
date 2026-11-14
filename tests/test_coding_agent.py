from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from forgel.adopt import adopt_repository
from forgel.agent import ProjectAgent
from forgel.artifacts import write_text
from forgel.coding_agent import CodingAgent
from forgel.config import Settings
from forgel.daemon import run_daemon
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.project_config import render_project_config
from forgel.tasks import create_task, get_task

REPO_ROOT = Path(__file__).resolve().parents[1]


class _SandboxSession:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.repo_id = ""
        self.closed = False

    def __enter__(self) -> _SandboxSession:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.closed = True

    def run(self, command, timeout: float = 120.0):  # type: ignore[no-untyped-def]
        self.commands.append(list(command))
        return 0, "sandbox ok\n"


class _Sandbox:
    def __init__(self) -> None:
        self.session_obj = _SandboxSession()

    def available(self) -> tuple[bool, str]:
        return True, "27.5.1"

    def ensure_image(self, layout, environment, project_id):  # type: ignore[no-untyped-def]
        return "python:3.12-slim"

    def session(self, layout, environment, project_id, repo_id):  # type: ignore[no-untyped-def]
        self.session_obj.repo_id = repo_id
        return self.session_obj


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class CodingAgentTest(unittest.TestCase):
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
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        source = self.home / "source"
        source.mkdir()
        (source / "README.md").write_text("source\n", encoding="utf-8")
        _run(source, "init", "-q")
        _run(source, "add", "-A")
        _run(
            source,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "initial",
        )
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), brief="Test project"
        )
        self.project_id = adopted.project_id
        self.project = self.ledger.get_project(self.project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])
        self.repo = self.layout.repo_path("main")

    def _task(self):
        return create_task(
            self.layout,
            "Add a calculator",
            ["Expose add(a, b)", "Write tests"],
            ["python -m unittest passes"],
            constraints=["stdlib only"],
            repo_id="main",
            test_command=[
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
            ],
        )

    def _responses(self) -> list[str]:
        return [
            json.dumps(
                {
                    "action": "write_file",
                    "path": "calc.py",
                    "content": "def add(a, b):\n    return a + b\n",
                }
            ),
            json.dumps(
                {
                    "action": "write_file",
                    "path": "tests/test_calc.py",
                    "content": (
                        "import unittest\n"
                        "from calc import add\n\n"
                        "class CalcTest(unittest.TestCase):\n"
                        "    def test_add(self):\n"
                        "        self.assertEqual(add(2, 3), 5)\n"
                    ),
                }
            ),
            json.dumps(
                {
                    "action": "run",
                    "command": [
                        sys.executable,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                    ],
                }
            ),
            json.dumps(
                {
                    "action": "done",
                    "summary": "added add and tests",
                    "assumptions": ["The calculator is a plain module"],
                }
            ),
        ]

    def test_agent_implements_a_task(self) -> None:
        task = self._task()
        client = ScriptedModelClient(self._responses())
        result = CodingAgent(self.settings, self.ledger, client).run(
            self.project, task, log=lambda _m: None
        )
        self.assertEqual(result.status, "done", result.summary)
        self.assertTrue((self.repo / "calc.py").exists())
        self.assertTrue((self.repo / "tests/test_calc.py").exists())
        self.assertIn("OK", result.test_output)
        self.assertTrue((self.layout.root / result.report).exists())
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertIn("added add", stored["result"]["summary"])
        self.assertEqual(
            stored["result"]["assumptions"],
            ["The calculator is a plain module"],
        )
        report = (self.layout.root / result.report).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Assumptions", report)
        self.assertIn("plain module", report)
        log = _run(self.repo, "log", "-1", "--format=%s").stdout
        self.assertIn("Agent: Add a calculator", log)
        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "agent_run"
        ]
        self.assertEqual(events[-1]["status"], "done")

    def test_commands_run_in_the_sandbox_when_configured(self) -> None:
        settings = replace(
            self.settings,
            sandbox="docker",
            sandbox_image="python:3.12-slim",
        )
        sandbox = _Sandbox()
        task = self._task()
        client = ScriptedModelClient(self._responses())
        with patch(
            "forgel.coding_agent.docker_runner", return_value=sandbox
        ):
            result = CodingAgent(settings, self.ledger, client).run(
                self.project, task, log=lambda _m: None
            )
        self.assertEqual(result.status, "done", result.summary)
        self.assertTrue((self.repo / "calc.py").exists())
        self.assertEqual(sandbox.session_obj.repo_id, "main")
        self.assertEqual(len(sandbox.session_obj.commands), 2)
        self.assertEqual(
            sandbox.session_obj.commands[1][:3],
            [sys.executable, "-m", "unittest"],
        )
        self.assertTrue(sandbox.session_obj.closed)

    def test_invalid_actions_fail_the_task(self) -> None:
        task = self._task()
        client = ScriptedModelClient(["not json", "still not", "nope"])
        result = CodingAgent(self.settings, self.ledger, client).run(
            self.project, task, log=lambda _m: None
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("valid action", result.summary)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")

    def test_path_escape_and_secret_files_are_rejected(self) -> None:
        task = create_task(
            self.layout,
            "Rejected paths",
            ["nothing"],
            ["nothing"],
            repo_id="main",
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "../escape.txt",
                        "content": "x",
                    }
                ),
                json.dumps(
                    {
                        "action": "write_file",
                        "path": ".env",
                        "content": "TOKEN=x",
                    }
                ),
                json.dumps(
                    {
                        "action": "run",
                        "command": ["curl", "https://example.com"],
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
            ]
        )
        result = CodingAgent(self.settings, self.ledger, client).run(
            self.project, task, log=lambda _m: None
        )
        self.assertEqual(result.status, "done")
        self.assertFalse((self.layout.repos_root / "escape.txt").exists())
        self.assertFalse((self.repo / ".env").exists())
        self.assertEqual(result.commands, [])

    def test_step_limit_stops_the_loop(self) -> None:
        task = self._task()
        client = ScriptedModelClient(
            [json.dumps({"action": "list_files", "path": "."})] * 5
        )
        with patch.dict(
            os.environ, {"FORGEL_AGENT_MAX_SESSIONS": "1"}, clear=False
        ):
            result = CodingAgent(
                self.settings, self.ledger, client, max_steps=4
            ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("step limit", result.summary)

    def test_context_handoff_writes_state_and_continues(self) -> None:
        write_text(
            self.layout.control / "forgel.toml",
            render_project_config("Test project", model_context_window=16384),
        )
        task = create_task(
            self.layout,
            "Inspect and finish",
            ["Inspect the repository", "Report completion"],
            ["The task is done"],
            repo_id="main",
            test_command=[],
        )
        responses = [
            json.dumps({"action": "list_files", "path": "."})
            for _ in range(8)
        ] + [
            json.dumps(
                {"action": "done", "summary": "inspected and done"}
            )
        ]
        result = CodingAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(responses),
            max_steps=6,
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        context = stored["result"]["context"]
        self.assertGreaterEqual(context["sessions"], 2)
        self.assertGreaterEqual(context["compactions"], 1)
        state = self.layout.artifact(
            f"docs/program/agent/{task['id']}.state.md"
        )
        self.assertTrue(state.exists())
        text = state.read_text(encoding="utf-8")
        self.assertIn("Session State", text)
        self.assertIn("Inspect the repository", text)
        self.assertIn("list_files", text)
        report = (self.layout.root / result.report).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Context", report)
        self.assertIn("Handoffs:", report)

    def test_free_text_queues_a_task_the_daemon_runs(self) -> None:
        request = {
            "kind": "change_request",
            "reply": "I will add a feature module.",
            "title": "Add a feature module",
            "summary": "Add feature.py.",
            "requirements": ["Create feature.py"],
            "acceptance": ["feature.py exists"],
            "constraints": ["standard library only"],
            "repo_id": "main",
            "test_command": [],
        }
        intake = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(request)]),
        )
        result = intake.handle(
            self.project, "Please add a feature module", "@tester"
        )
        self.assertIsNotNone(result.task_id)
        assert result.task_id is not None

        coding = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "feature.py",
                        "content": "VALUE = 1\n",
                    }
                ),
                json.dumps(
                    {"action": "done", "summary": "added feature.py"}
                ),
            ]
        )
        run_daemon(
            self.settings,
            self.ledger,
            once=True,
            log=lambda _m: None,
            client=coding,
        )
        stored = get_task(self.layout, result.task_id)
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertTrue((self.repo / "feature.py").exists())

    def test_daemon_processes_a_pending_task(self) -> None:
        task = self._task()
        client = ScriptedModelClient(self._responses())
        run_daemon(
            self.settings,
            self.ledger,
            once=True,
            log=lambda _m: None,
            client=client,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertTrue((self.repo / "calc.py").exists())


if __name__ == "__main__":
    unittest.main()
