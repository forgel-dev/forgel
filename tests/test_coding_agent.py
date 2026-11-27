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

from forgel.adopt import add_repository, adopt_repository
from forgel.agent import ProjectAgent
from forgel.artifacts import write_text
from forgel.coding_agent import (
    AgentError,
    CodingAgent,
    PROMPT_RUN_OBSERVATION,
    _preserved_evidence,
    _prompt_observation,
    _safe_env,
)
from forgel import limits
from forgel.config import Settings
from forgel.daemon import run_daemon
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.project_config import render_project_config
from forgel.repo_tools import read_text_page
from forgel.tasks import (
    create_task,
    get_task,
    recover_running,
    update_task,
)
from tests import pin_peak_always

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
        origin = self.home / "source-origin.git"
        _run(
            self.home,
            "init",
            "--bare",
            "-q",
            "-b",
            "main",
            str(origin),
        )
        _run(source, "remote", "add", "origin", str(origin))
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), brief="Test project",
            name="coding-agent",
        )
        self.project_id = adopted.project_id
        self.project = self.ledger.get_project(self.project_id)
        assert self.project is not None
        pin_peak_always(self.project["workspace"])
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
            json.dumps({"commit": ["calc.py", "tests/test_calc.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
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
        log = _run(self.repo, "log", "--format=%s").stdout
        self.assertIn("Agent: Add a calculator", log)
        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "agent_run"
        ]
        self.assertEqual(events[-1]["status"], "done")

    def test_done_without_changes_on_a_rework_fails(self) -> None:
        task = create_task(
            self.layout,
            "Rework without changes",
            ["Do it"],
            ["It is done"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout,
            task["id"],
            status="done",
            result={"summary": "implemented", "rework_count": 1},
        )
        current = get_task(self.layout, task["id"])
        assert current is not None
        client = ScriptedModelClient(
            [json.dumps({"action": "done", "summary": "fixed it"})]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, current, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("without changing anything", result.summary)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["failure"]["kind"], "agent"
        )

    def test_each_rework_records_its_own_run_and_cost(self) -> None:
        class UsageClient(ScriptedModelClient):
            last_usage = {
                "prompt_tokens": 100,
                "completion_tokens": 50,
            }

        task = self._task()
        first = CodingAgent(
            self.settings,
            self.ledger,
            UsageClient(self._responses()),
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(first.status, "done", first.summary)

        stored = get_task(self.layout, task["id"])
        assert stored is not None
        data = dict(stored.get("result") or {})
        data["rework_count"] = 1
        update_task(self.layout, task["id"], result=data)
        current = get_task(self.layout, task["id"])
        assert current is not None
        second = CodingAgent(
            self.settings,
            self.ledger,
            UsageClient(
                [
                    json.dumps(
                        {
                            "action": "write_file",
                            "path": "calc.py",
                            "content": (
                                "def add(a, b):\n    return b + a\n"
                            ),
                        }
                    ),
                    json.dumps(
                        {
                            "action": "done",
                            "summary": "rewrote add",
                        }
                    ),
                    json.dumps({"commit": ["calc.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
                ]
            ),
        ).run(self.project, current, log=lambda _m: None)
        self.assertEqual(second.status, "done", second.summary)

        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "agent_run"
        ]
        self.assertEqual(len(events), 2)
        self.assertEqual(
            [
                json.loads(event["payload"])["rework"]
                for event in events
            ],
            [0, 1],
        )
        self.assertTrue(
            all(float(event["cost"]) > 0 for event in events)
        )

    def test_a_rework_with_the_work_already_committed_is_done(self) -> None:
        (self.repo / ".gitignore").write_text(
            "__pycache__/\n", encoding="utf-8"
        )
        (self.repo / "work.py").write_text(
            "value = 1\n", encoding="utf-8"
        )
        _run(self.repo, "add", "-A")
        _run(
            self.repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "the work is committed",
        )
        sha = _run(
            self.repo, "rev-parse", "HEAD"
        ).stdout.strip()
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout,
            task["id"],
            status="pending",
            result={
                "summary": "the work is already committed",
                "files_changed": ["work.py"],
                "rework_count": 1,
                "git": {
                    "base": sha,
                    "head": sha,
                    "commit": sha,
                    "commits": [sha],
                },
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"action": "done", "summary": "already done"}
                )
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        final = get_task(self.layout, task["id"])
        assert final is not None
        self.assertIn("work.py", final["result"]["files_changed"])
        self.assertIn(
            sha, final["result"]["git"]["commits"]
        )

    def test_agent_executes_a_batch_of_actions(self) -> None:
        task = self._task()
        responses = self._responses()
        actions = [json.loads(item) for item in responses[:-1]]
        client = ScriptedModelClient(
            [json.dumps(actions), responses[-1]]
        )
        result = CodingAgent(self.settings, self.ledger, client).run(
            self.project, task, log=lambda _m: None
        )
        self.assertEqual(result.status, "done", result.summary)
        self.assertTrue((self.repo / "calc.py").exists())
        self.assertTrue((self.repo / "tests/test_calc.py").exists())
        self.assertIn("OK", result.test_output)

    def test_resumed_task_reads_previous_state(self) -> None:
        task = create_task(
            self.layout,
            "Resume after a crash",
            ["Finish the work"],
            ["The work is finished"],
            repo_id="main",
            test_command=[],
        )
        write_text(
            self.layout.artifact(
                f"docs/program/agent/{task['id']}.state.md"
            ),
            "# Session State: previous\n\n- Task: finish the work\n",
        )
        update_task(self.layout, task["id"], status="running")
        recovered = recover_running(self.layout)
        self.assertEqual(recovered[0]["status"], "pending")
        resumed = get_task(self.layout, task["id"])
        assert resumed is not None
        task = resumed
        client = ScriptedModelClient(
            [json.dumps({"action": "done", "summary": "resumed"})]
        )
        result = CodingAgent(self.settings, self.ledger, client).run(
            self.project, task, log=lambda _m: None
        )
        self.assertEqual(result.status, "done", result.summary)
        self.assertIn(
            "Previous session state", client.requests[0][1].content
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["result"]["resume_count"], 1)

    def test_a_linked_project_runs_tasks_in_another_repository(
        self,
    ) -> None:
        web = self.home / "sources" / "web"
        web.mkdir(parents=True)
        (web / "README.md").write_text("web\n", encoding="utf-8")
        _run(web, "init", "-q", "-b", "main")
        _run(web, "add", "-A")
        _run(
            web,
            "-c", "user.name=T", "-c", "user.email=t@example.com",
            "commit", "-q", "-m", "initial",
        )
        added = add_repository(
            self.settings,
            self.ledger,
            self.project,
            str(web),
            repo_id="web",
        )
        self.assertEqual(added.entry["id"], "web")
        self.assertEqual(
            self.layout.repo_path("web").resolve(), web.resolve()
        )
        task = create_task(
            self.layout,
            "Add a web page",
            ["Create page.py"],
            ["The file exists"],
            repo_id="web",
            test_command=[],
        )
        responses = [
            json.dumps(
                {
                    "action": "write_file",
                    "path": "page.py",
                    "content": "value = 1\n",
                }
            ),
            json.dumps(
                {"action": "done", "summary": "added the page"}
            ),
            json.dumps({"commit": ["page.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
        ]
        result = CodingAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(responses),
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        self.assertTrue((web / "page.py").exists())
        self.assertFalse((self.repo / "page.py").exists())
        log = _run(web, "log", "--format=%s").stdout
        self.assertIn("Agent: Add a web page", log)

    def test_test_removals_are_recorded(self) -> None:
        task = create_task(
            self.layout,
            "Update a test",
            ["Replace the old test"],
            ["The new test exists"],
            repo_id="main",
            test_command=[],
        )
        response = json.dumps(
            {
                "action": "done",
                "summary": "replaced the test",
                "test_removals": [
                    {
                        "test": "tests/test_old.py",
                        "reason": "replaced",
                        "replacement": "tests/test_new.py",
                    }
                ],
            }
        )
        result = CodingAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([response]),
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done")
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(
            stored["result"]["test_removals"][0]["reason"], "replaced"
        )
        report = (self.layout.root / result.report).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Test Removals", report)
        self.assertIn("tests/test_old.py", report)

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
        result = CodingAgent(
            self.settings, self.ledger, client, max_steps=4
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("step limit", result.summary)

    def test_context_handoff_writes_state_and_continues(self) -> None:
        write_text(
            self.layout.control / "forgel.toml",
            render_project_config("Test project", model_context_window=4096),
        )
        (self.repo / "large.txt").write_text(
            "x" * 30_000 + "\n", encoding="utf-8"
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
            json.dumps({"action": "read_file", "path": "large.txt"}),
            json.dumps(
                {"action": "done", "summary": "inspected and done"}
            ),
            json.dumps({"commit": [".gitignore"], "revert": ["large.txt"], "ignore": [], "escalate": []}),
        ]
        result = CodingAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(responses),
            max_steps=1000,
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
        self.assertIn("read_file", text)
        report = (self.layout.root / result.report).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Context", report)
        self.assertIn("Handoffs:", report)





    def test_handoff_records_the_failing_check_and_next_step(self) -> None:
        write_text(
            self.layout.control / "forgel.toml",
            render_project_config("Test project", model_context_window=4096),
        )
        (self.repo / "large.txt").write_text(
            "x" * 30_000 + "\n", encoding="utf-8"
        )
        task = create_task(
            self.layout,
            "Record the handoff",
            ["Record the failing check"],
            ["The handoff names the failure"],
            repo_id="main",
            test_command=[],
        )
        responses = [
            json.dumps(
                {
                    "action": "run",
                    "command": [
                        sys.executable,
                        "-c",
                        "import sys; sys.exit(3)",
                    ],
                }
            ),
            json.dumps({"action": "read_file", "path": "large.txt"}),
            json.dumps({"action": "done", "summary": "recorded"}),
            json.dumps(
                {
                    "commit": [],
                    "revert": ["large.txt"],
                    "ignore": [],
                    "escalate": [],
                }
            ),
        ]
        client = ScriptedModelClient(responses)
        result = CodingAgent(
            self.settings, self.ledger, client, max_steps=1000
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        state = self.layout.artifact(
            f"docs/program/agent/{task['id']}.state.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Last Test Outcome", state)
        self.assertIn("failed:", state)
        self.assertIn("exit 3", state)
        self.assertIn("## Failing Check", state)
        self.assertIn("## Next Step", state)
        self.assertIn("Investigate the failing command", state)

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
                json.dumps({"commit": ["feature.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
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

    def test_read_file_returns_large_files_without_slicing(self) -> None:
        (self.repo / "big.py").write_text(
            "x" * 10_000 + "\n", encoding="utf-8"
        )
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": "big.py"},
            set(),
        )
        self.assertGreater(len(observation), 9_000)

    def test_prompt_observation_is_bounded_and_preserves_both_ends(self) -> None:
        observation = "begin" + ("x" * 100_000) + "end"
        rendered = _prompt_observation("run", observation)
        self.assertTrue(rendered.startswith("begin"))
        self.assertTrue(rendered.endswith("end"))
        self.assertIn("observation truncated for prompt", rendered)
        self.assertLess(
            len(rendered), PROMPT_RUN_OBSERVATION + 200
        )
        self.assertEqual(
            _prompt_observation("run", "short output"),
            "short output",
        )

    def test_run_cannot_be_used_to_print_a_file(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "run",
                "command": [
                    sys.executable,
                    "-c",
                    "print(open('README.md').read())",
                ],
            },
            set(),
        )
        self.assertIn("read_file", observation)
        self.assertNotIn("source", observation)

    def test_history_is_not_trimmed_within_a_session(self) -> None:
        task = create_task(
            self.layout,
            "Read the README",
            ["Read README.md"],
            ["The file was read"],
            repo_id="main",
            test_command=[],
        )
        responses = [
            json.dumps(
                {"action": "read_file", "path": "README.md"}
            )
        ] + [
            json.dumps({"action": "list_files", "path": "."})
            for _ in range(8)
        ] + [
            json.dumps({"action": "done", "summary": "read it"})
        ]
        client = ScriptedModelClient(responses)
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        final_prompt = "\n".join(
            message.content for message in client.requests[-1]
        )
        self.assertIn("source", final_prompt)

    def test_read_file_pages_by_lines(self) -> None:
        lines = [f"line {index}" for index in range(2500)]
        (self.repo / "big.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        first, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": "big.txt"},
            set(),
        )
        self.assertIn("lines 1-2000 of 2500", first)
        self.assertIn("line 1999", first)
        self.assertIn("offset=2001", first)
        second, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "read_file",
                "path": "big.txt",
                "offset": 2001,
            },
            set(),
        )
        self.assertIn("lines 2001-2500 of 2500", second)
        self.assertIn("line 2499", second)

    def test_tool_markup_is_retried(self) -> None:
        task = create_task(
            self.layout,
            "Finish",
            ["Finish it"],
            ["It is finished"],
            repo_id="main",
            test_command=[],
        )
        markup = (
            "<｜｜DSML｜｜ calls><｜｜DSML｜｜ invoke name=\"action\">"
            "</｜｜DSML｜｜ invoke></｜｜DSML｜｜ calls>"
        )
        client = ScriptedModelClient(
            [
                markup,
                json.dumps({"action": "done", "summary": "done"}),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        self.assertIn(
            "tool-call markup", client.requests[1][-1].content
        )

    def test_docker_compose_is_allowed(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        self.assertEqual(
            agent._command(["docker", "compose", "up", "--build", "-d"]),
            ["docker", "compose", "up", "--build", "-d"],
        )
        self.assertEqual(
            agent._command(["docker", "compose", "version"]),
            ["docker", "compose", "version"],
        )
        with self.assertRaises(AgentError):
            agent._command(["docker", "ps"])

    def test_dependency_manager_commands_are_allowed(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        for argv in (
            ["python", "-m", "pip", "install", "pytest"],
            ["pip", "install", "pytest"],
            ["pip3", "install", "pytest"],
            ["npm", "install"],
            ["npm", "ci"],
            ["npm", "add", "vite"],
            ["yarn", "install"],
            ["pnpm", "install"],
            ["uv", "pip", "install", "pytest"],
            ["poetry", "add", "pytest"],
            ["bundle", "install"],
            ["composer", "install"],
        ):
            self.assertEqual(agent._command(argv), argv)

    def test_the_task_prompt_carries_project_and_repository_rules(
        self,
    ) -> None:
        write_text(
            self.layout.control / "FORGEL.md",
            "PROJECT-RULE-MARKER\n",
        )
        (self.repo / "AGENTS.md").write_text(
            "REPO-RULE-MARKER\n", encoding="utf-8"
        )
        task = self._task()
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        prompt = agent._task_prompt(
            self.layout, task, "main", self.repo
        )
        self.assertIn("PROJECT-RULE-MARKER", prompt)
        self.assertIn("REPO-RULE-MARKER", prompt)
        self.assertIn("take precedence", prompt)

    def test_reading_different_ranges_is_not_a_repeated_action(
        self,
    ) -> None:
        path = self.repo / "notes.txt"
        path.write_text(
            "one\ntwo\nthree\nfour\nfive\n", encoding="utf-8"
        )
        task = create_task(
            self.layout,
            "Read in ranges",
            ["Read the notes"],
            ["The notes are read"],
            repo_id="main",
            test_command=[],
        )
        responses = [
            json.dumps(
                {
                    "action": "read_file",
                    "path": "notes.txt",
                    "offset": number,
                    "limit": 1,
                }
            )
            for number in range(1, 6)
        ] + [
            json.dumps({"action": "done", "summary": "read"}),
            json.dumps({"commit": [".gitignore"], "revert": ["notes.txt"], "ignore": [], "escalate": []}),
        ]
        client = ScriptedModelClient(responses)
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)

    def _search_fixtures(self) -> None:
        src = self.repo / "src"
        src.mkdir()
        (src / "a.py").write_text("needle = 1\n", encoding="utf-8")
        (src / "b.txt").write_text("needle\n", encoding="utf-8")
        (src / "literal.py").write_text("a.b\naxb\n", encoding="utf-8")
        (self.repo / "other.py").write_text(
            "other = 'needle'\n", encoding="utf-8"
        )
        (self.repo / "untracked.py").write_text(
            "untracked needle\n", encoding="utf-8"
        )
        (self.repo / "secrets.toml").write_text(
            "token = 'needle'\n", encoding="utf-8"
        )
        docs = self.repo / "docs" / "program"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "note.md").write_text("needle\n", encoding="utf-8")
        _run(
            self.repo,
            "add",
            "src/a.py",
            "src/b.txt",
            "src/literal.py",
            "other.py",
            "secrets.toml",
            "docs/program/note.md",
        )
        _run(
            self.repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-q",
            "-m",
            "search fixtures",
        )

    def test_search_files_finds_tracked_and_untracked_and_filters_secrets(
        self,
    ) -> None:
        self._search_fixtures()
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "search_files", "pattern": "needle"},
            set(),
        )
        self.assertIn("src/a.py", observation)
        self.assertIn("src/b.txt", observation)
        self.assertIn("untracked.py", observation)
        self.assertNotIn("secrets.toml", observation)
        self.assertNotIn("docs/program", observation)

    def test_search_files_respects_glob_and_path(self) -> None:
        self._search_fixtures()
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        by_glob, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "search_files",
                "pattern": "needle",
                "glob": "*.py",
            },
            set(),
        )
        self.assertIn("src/a.py", by_glob)
        self.assertNotIn("src/b.txt", by_glob)
        by_path, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "search_files",
                "pattern": "needle",
                "path": "src",
            },
            set(),
        )
        self.assertIn("src/a.py", by_path)
        self.assertNotIn("other.py", by_path)

    def test_search_files_supports_literal_mode(self) -> None:
        self._search_fixtures()
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        literal, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "search_files",
                "pattern": "a.b",
                "path": "src/literal.py",
                "literal": True,
            },
            set(),
        )
        self.assertIn("a.b", literal)
        self.assertNotIn("axb", literal)
        regex, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "search_files",
                "pattern": "a.b",
                "path": "src/literal.py",
            },
            set(),
        )
        self.assertIn("a.b", regex)
        self.assertIn("axb", regex)

    def test_search_files_rejects_invalid_queries(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        empty, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "search_files", "pattern": ""},
            set(),
        )
        self.assertIn("needs a pattern", empty)
        long_pattern, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "search_files", "pattern": "x" * 257},
            set(),
        )
        self.assertIn("too long", long_pattern)
        outside, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "search_files",
                "pattern": "x",
                "path": "../outside",
            },
            set(),
        )
        self.assertIn("error", outside)
        invalid, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "search_files", "pattern": "["},
            set(),
        )
        self.assertIn("search failed", invalid)

    def test_read_cache_invalidates_when_content_changes(self) -> None:
        path = self.repo / "cache.txt"
        path.write_text("old\n", encoding="utf-8")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        first, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": "cache.txt"},
            set(),
        )
        self.assertIn("old", first)
        path.write_text("new\n", encoding="utf-8")
        second, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": "cache.txt"},
            set(),
        )
        self.assertIn("new", second)
        self.assertNotIn("old", second)

    def _read_digest(self, agent, path: str) -> str:
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": path},
            set(),
        )
        self.assertTrue(observation.startswith("sha256:"))
        return observation.splitlines()[0].split(":", 1)[1]

    def test_edit_file_applies_an_exact_unique_change(self) -> None:
        path = self.repo / "edit.txt"
        path.write_text("alpha\nbeta\n", encoding="utf-8")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        digest = self._read_digest(agent, "edit.txt")
        touched: set[str] = set()
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "edit.txt",
                "old": "beta",
                "new": "gamma",
                "expected_sha256": digest,
            },
            touched,
        )
        self.assertIn("edited", observation)
        self.assertEqual(
            path.read_text(encoding="utf-8"), "alpha\ngamma\n"
        )
        self.assertIn("edit.txt", touched)
        self.assertEqual(
            [item.name for item in self.repo.glob(".edit.txt.*.tmp")],
            [],
        )

    def test_edit_file_rejects_a_stale_or_non_unique_old_text(self) -> None:
        path = self.repo / "edit.txt"
        path.write_text("x\nx\n", encoding="utf-8")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        digest = self._read_digest(agent, "edit.txt")
        stale, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "edit.txt",
                "old": "x",
                "new": "y",
                "expected_sha256": "0" * 16,
            },
            set(),
        )
        self.assertIn("conflict", stale)
        repeated, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "edit.txt",
                "old": "x",
                "new": "y",
                "expected_sha256": digest,
            },
            set(),
        )
        self.assertIn("exactly once", repeated)
        missing, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "edit.txt",
                "old": "missing",
                "new": "y",
                "expected_sha256": digest,
            },
            set(),
        )
        self.assertIn("found 0", missing)
        self.assertEqual(path.read_text(encoding="utf-8"), "x\nx\n")

    def test_edit_file_rejects_secret_missing_file_and_no_hash(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        (self.repo / ".env").write_text("SECRET=1\n", encoding="utf-8")
        secret, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": ".env",
                "old": "SECRET=1",
                "new": "SECRET=2",
                "expected_sha256": "0" * 16,
            },
            set(),
        )
        self.assertIn("secret-like", secret)
        missing, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "missing.txt",
                "old": "a",
                "new": "b",
                "expected_sha256": "0" * 16,
            },
            set(),
        )
        self.assertIn("file not found", missing)
        path = self.repo / "edit.txt"
        path.write_text("alpha\n", encoding="utf-8")
        no_hash, _ = agent._execute(
            self.layout,
            self.repo,
            {
                "action": "edit_file",
                "path": "edit.txt",
                "old": "alpha",
                "new": "beta",
            },
            set(),
        )
        self.assertIn("expected_sha256", no_hash)
        self.assertEqual(path.read_text(encoding="utf-8"), "alpha\n")

    def test_signatures_are_content_and_state_aware(self) -> None:
        path = self.repo / "sig.txt"
        path.write_text("one\n", encoding="utf-8")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        read = {"action": "read_file", "path": "sig.txt"}
        first = agent._signature(read, self.repo)
        self.assertEqual(first, agent._signature(read, self.repo))
        path.write_text("two\n", encoding="utf-8")
        self.assertNotEqual(first, agent._signature(read, self.repo))

        run = {
            "action": "run",
            "command": [sys.executable, "-c", "pass"],
        }
        run_first = agent._signature(run, self.repo)
        self.assertEqual(run_first, agent._signature(run, self.repo))
        (self.repo / "changed.txt").write_text("x\n", encoding="utf-8")
        self.assertNotEqual(run_first, agent._signature(run, self.repo))


    def test_project_shell_scripts_are_allowed(self) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        agent._allowed_scripts = {
            "scripts/e2e.sh",
            "scripts/test.sh",
        }
        self.assertEqual(
            agent._command(["sh", "scripts/e2e.sh"]),
            ["sh", "scripts/e2e.sh"],
        )
        self.assertEqual(
            agent._command(["bash", "scripts/e2e.sh"]),
            ["bash", "scripts/e2e.sh"],
        )
        self.assertEqual(
            agent._command(["./scripts/test.sh"]),
            ["./scripts/test.sh"],
        )
        with self.assertRaises(AgentError):
            agent._command(["sh", "scripts/other.sh"])
        with self.assertRaises(AgentError):
            agent._command(["sh", "-c", "echo unsafe"])
        with self.assertRaises(AgentError):
            agent._command(["sh", "/tmp/outside.sh"])

    def test_env_local_is_not_readable(self) -> None:
        (self.repo / ".env.local").write_text(
            "FORGEL_MODEL_API_KEY=secret\n", encoding="utf-8"
        )
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        observation, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": ".env.local"},
            set(),
        )
        self.assertIn("secret-like", observation)
        (self.repo / ".env.example").write_text(
            "FORGEL_MODEL_API_KEY=\n", encoding="utf-8"
        )
        example, _ = agent._execute(
            self.layout,
            self.repo,
            {"action": "read_file", "path": ".env.example"},
            set(),
        )
        self.assertIn("FORGEL_MODEL_API_KEY", example)

    def test_a_symlink_into_git_is_rejected(self) -> None:
        link = self.repo / "link"
        link.symlink_to(self.repo / ".git" / "config")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        with self.assertRaises(AgentError):
            agent._path(self.repo, "link")

    def test_agent_event_records_cost_from_tokens(self) -> None:
        task = self._task()
        report = self.layout.artifact(
            "docs/program/agent/cost-event.md"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("report\n", encoding="utf-8")
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        agent._record_event(
            self.layout,
            self.project,
            task,
            "done",
            report,
            "summary",
            [],
            {
                "provider_input_tokens": 1_000_000,
                "provider_output_tokens": 1_000_000,
            },
        )
        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "agent_run"
        ]
        self.assertAlmostEqual(float(events[-1]["cost"]), 0.70)

    def test_existing_evidence_survives_report_regeneration(self) -> None:
        path = self.home / "report.md"
        path.write_text(
            "# Agent Run\n\n## Compose Evidence\n\nproof\n\n"
            "## Other\n\nnot evidence\n",
            encoding="utf-8",
        )
        evidence = _preserved_evidence(path)
        self.assertIn("Compose Evidence", evidence)
        self.assertIn("proof", evidence)
        self.assertNotIn("not evidence", evidence)


    def test_recall_reads_an_earlier_step_from_the_transcript(self) -> None:
        task = self._task()
        task["test_command"] = [
            sys.executable,
            "-c",
            "print('ok')",
        ]
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"action": "read_file", "path": "README.md"}
                ),
                json.dumps(
                    {"action": "recall", "from": 1, "count": 1}
                ),
                json.dumps(
                    {"action": "done", "summary": "read the readme"}
                ),
            ]
        )

        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, task, log=lambda _m: None)

        self.assertEqual(result.status, "done")
        transcript = (
            Path(self.project["workspace"])
            / "docs/program/agent"
            / f"{task['id']}.transcript.jsonl"
        )
        self.assertTrue(transcript.exists())
        self.assertIn(
            "README.md",
            transcript.read_text(encoding="utf-8"),
        )
        recalled = client.requests[2][-1].content
        self.assertIn("step 1", recalled)
        self.assertIn("source", recalled)

    def test_a_failed_run_reports_the_changed_files(self) -> None:
        task = self._task()
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "README.md",
                        "content": "changed\n",
                    }
                ),
                json.dumps({"action": "fail", "reason": "stop"}),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("README.md", result.files_changed)

    def test_a_timed_out_command_with_bytes_output_does_not_crash(
        self,
    ) -> None:
        agent = CodingAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        expired = subprocess.TimeoutExpired(
            cmd=["sleep", "1"],
            timeout=1,
            output=None,
            stderr=b"partial error",
        )
        with patch(
            "forgel.coding_agent.subprocess.run",
            side_effect=expired,
        ):
            code, output = agent._run_command(
                self.layout, self.repo, ["sleep", "1"], timeout=0.1
            )
        self.assertEqual(code, 124)
        self.assertIn("timed out", output)
        self.assertIn("partial error", output)

    def test_agent_env_keeps_docker_client_config(self) -> None:
        parent = self.home / "parent-home"
        (parent / ".docker").mkdir(parents=True)
        with patch.dict(
            os.environ,
            {
                "HOME": str(parent),
                "DOCKER_HOST": "unix:///tmp/docker.sock",
                "TOP_SECRET": "leak",
            },
            clear=False,
        ):
            os.environ.pop("DOCKER_CONFIG", None)
            env = _safe_env(self.layout)
        self.assertEqual(
            env["HOME"],
            str(self.layout.root / ".forgel" / "agent-home"),
        )
        self.assertEqual(
            env["DOCKER_HOST"], "unix:///tmp/docker.sock"
        )
        self.assertEqual(
            env["DOCKER_CONFIG"], str(parent / ".docker")
        )
        self.assertNotIn("TOP_SECRET", env)

    def test_a_retry_prompt_keeps_previous_work(self) -> None:
        task = create_task(
            self.layout,
            "Add the missing evidence",
            ["Produce the compose evidence"],
            ["The evidence exists"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout,
            task["id"],
            status="failed",
            result={
                "summary": "the template and its tests are already done",
                "failure": {
                    "kind": "agent",
                    "message": "the compose output is missing",
                },
                "review": {
                    "status": "fail",
                    "blocking": ["the Output section still says TODO"],
                    "requirements": [
                        {
                            "requirement": "compose evidence",
                            "verdict": "fail",
                            "note": "only expected output is provided",
                        }
                    ],
                },
                "files_changed": ["template/app.py"],
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [json.dumps({"action": "done", "summary": "added evidence"})]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        prompt = client.requests[0][1].content
        self.assertIn("This is a retry", prompt)
        self.assertIn("already done", prompt)
        self.assertIn("the compose output is missing", prompt)
        self.assertIn("the Output section still says TODO", prompt)
        self.assertIn("template/app.py", prompt)
        self.assertIn("Do not repeat finished work", prompt)
        self.assertNotIn("If the blocker is missing evidence", prompt)

    def test_done_commits_only_the_task_files(self) -> None:
        parallel = self.repo / "parallel.py"
        parallel.write_text("value = 0\n", encoding="utf-8")
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 2\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "finished"}),
                json.dumps({"commit": ["work.py", ".gitignore"], "revert": [], "ignore": [], "escalate": [{"path": "parallel.py", "reason": "unrelated"}]}),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        tracked = _run(
            self.repo, "ls-files", "parallel.py", "work.py"
        ).stdout.split()
        self.assertEqual(sorted(tracked), ["work.py"])
        status = _run(
            self.repo, "status", "--porcelain"
        ).stdout.strip()
        self.assertIn("parallel.py", status)
        self.assertIn("work.py", result.files_changed)
        self.assertNotIn("parallel.py", result.files_changed)

    def test_a_failed_attempt_does_not_commit(self) -> None:
        parallel = self.repo / "parallel.py"
        parallel.write_text("value = 0\n", encoding="utf-8")
        task = create_task(
            self.layout,
            "Partial work",
            ["Write a work file"],
            ["The work is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 2\n",
                    }
                ),
                json.dumps({"action": "fail", "reason": "not finished"}),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        tracked = _run(
            self.repo, "ls-files", "parallel.py", "work.py"
        ).stdout.split()
        self.assertEqual(tracked, [])
        status = _run(
            self.repo, "status", "--porcelain"
        ).stdout.strip()
        self.assertIn("work.py", status)
        self.assertIn("work.py", result.files_changed)

    def test_completion_attributes_earlier_session_files(self) -> None:
        leftover = self.repo / "leftover"
        leftover.mkdir()
        (leftover / "note.py").write_text("value = 1\n", encoding="utf-8")
        task = create_task(
            self.layout,
            "Finish a partial change",
            ["Keep the note", "Add a work file"],
            ["Everything is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 2\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "finished"}),
                json.dumps(
                    {"commit": ["work.py", "leftover/note.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}
                ),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        tracked = _run(
            self.repo, "ls-files", "leftover/note.py", "work.py"
        ).stdout.split()
        self.assertEqual(
            sorted(tracked), ["leftover/note.py", "work.py"]
        )
        self.assertEqual(
            _run(
                self.repo,
                "status",
                "--porcelain",
                "--",
                "leftover/note.py",
                "work.py",
            ).stdout.strip(),
            "",
        )
        self.assertIn("leftover/note.py", result.files_changed)

    def test_completion_reverts_temporary_files(self) -> None:
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 1\n",
                    }
                ),
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "probe.py",
                        "content": "print('probe')\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
                json.dumps(
                    {
                        "commit": ["work.py", ".gitignore"],
                        "revert": ["probe.py"],
                        "ignore": [],
                        "escalate": [],
                    }
                ),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        self.assertFalse((self.repo / "probe.py").exists())
        self.assertNotIn("probe.py", result.files_changed)
        tracked = _run(self.repo, "ls-files", "work.py").stdout.strip()
        self.assertEqual(tracked, "work.py")

    def test_completion_ignores_an_artifact(self) -> None:
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 1\n",
                    }
                ),
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "debug.log",
                        "content": "a log\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
                json.dumps(
                    {
                        "commit": ["work.py"],
                        "revert": [],
                        "ignore": ["debug.log"],
                        "escalate": [],
                    }
                ),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        self.assertTrue((self.repo / "debug.log").exists())
        tracked = _run(self.repo, "ls-files", "debug.log").stdout.strip()
        self.assertEqual(tracked, "")
        gitignore = (self.repo / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/debug.log", gitignore)
        self.assertIn(".gitignore", result.files_changed)
        status = _run(self.repo, "status", "--porcelain").stdout
        self.assertNotIn("debug.log", status)

    def test_completion_escalates_unrelated_work(self) -> None:
        (self.repo / "other.py").write_text(
            "other = 1\n", encoding="utf-8"
        )
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 1\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
                json.dumps(
                    {
                        "commit": ["work.py", ".gitignore"],
                        "revert": [],
                        "ignore": [],
                        "escalate": [
                            {
                                "path": "other.py",
                                "reason": "unrelated parallel work",
                            }
                        ],
                    }
                ),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        data = stored.get("result") or {}
        self.assertEqual(
            [item["path"] for item in data.get("escalated") or []],
            ["other.py"],
        )
        self.assertTrue((self.repo / "other.py").exists())
        status = _run(self.repo, "status", "--porcelain").stdout
        self.assertIn("other.py", status)
        artifact = self.layout.artifact(
            f"docs/program/escalations/{task['id']}.md"
        )
        self.assertTrue(artifact.exists())
        stages = [
            event["stage"]
            for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("escalation", stages)

    def test_the_completion_step_retries_an_incomplete_decision(self) -> None:
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 1\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
                json.dumps(
                    {
                        "commit": ["work.py"],
                        "revert": [],
                        "ignore": [],
                        "escalate": [],
                    }
                ),
                json.dumps(
                    {
                        "commit": ["work.py", ".gitignore"],
                        "revert": [],
                        "ignore": [],
                        "escalate": [],
                    }
                ),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        tracked = _run(self.repo, "ls-files", "work.py").stdout.strip()
        self.assertEqual(tracked, "work.py")


    def test_an_undecided_completion_falls_back_to_the_agents_files(self) -> None:
        parallel = self.repo / "parallel.py"
        parallel.write_text("value = 0\n", encoding="utf-8")
        task = create_task(
            self.layout,
            "Add a work file",
            ["Add a work file"],
            ["The work file is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout, task["id"], status="pending", result={}
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        invalid = json.dumps({"files": []})
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "work.py",
                        "content": "value = 1\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "done"}),
                invalid,
                invalid,
                invalid,
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        self.assertIn("did not decide", result.summary)
        tracked = _run(self.repo, "ls-files", "work.py").stdout.strip()
        self.assertEqual(tracked, "work.py")
        status = _run(self.repo, "status", "--porcelain").stdout
        self.assertIn("parallel.py", status)
        final = get_task(self.layout, task["id"])
        assert final is not None
        escalated = [
            item["path"]
            for item in (final["result"].get("escalated") or [])
        ]
        self.assertIn("parallel.py", escalated)

    def test_a_retry_commits_files_left_by_an_earlier_attempt(self) -> None:
        leftover = self.repo / "leftover"
        leftover.mkdir()
        (leftover / "note.py").write_text("value = 1\n", encoding="utf-8")
        task = create_task(
            self.layout,
            "Finish a partial change",
            ["Keep the note"],
            ["The note is committed"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            self.layout,
            task["id"],
            result={
                "summary": "earlier attempt",
                "files_changed": ["leftover/"],
            },
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"action": "done", "summary": "already written"}
                ),
                json.dumps({"commit": ["leftover/note.py", ".gitignore"], "revert": [], "ignore": [], "escalate": []}),
            ]
        )
        result = CodingAgent(
            self.settings, self.ledger, client
        ).run(self.project, stored, log=lambda _m: None)
        self.assertEqual(result.status, "done", result.summary)
        tracked = _run(
            self.repo, "ls-files", "leftover/note.py"
        ).stdout.strip()
        self.assertEqual(tracked, "leftover/note.py")
        self.assertIn("leftover/note.py", result.files_changed)

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
