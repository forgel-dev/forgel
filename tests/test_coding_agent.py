from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forgel.adopt import adopt_repository
from forgel.coding_agent import CodingAgent
from forgel.config import Settings
from forgel.daemon import run_daemon
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.tasks import create_task, get_task

REPO_ROOT = Path(__file__).resolve().parents[1]


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
        log = _run(self.repo, "log", "-1", "--format=%s").stdout
        self.assertIn("Agent: Add a calculator", log)
        events = [
            event
            for event in self.ledger.events(self.project_id)
            if event["stage"] == "agent_run"
        ]
        self.assertEqual(events[-1]["status"], "done")

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
        result = CodingAgent(
            self.settings, self.ledger, client, max_steps=4
        ).run(self.project, task, log=lambda _m: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("step limit", result.summary)

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
