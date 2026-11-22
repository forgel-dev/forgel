from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.adopt import adopt_repository
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


SPEC = {
    "problem": "The feature is missing.",
    "outcome": "The feature exists.",
    "scope": ["the feature"],
    "non_goals": [],
    "requirements": ["Create feature.py"],
    "acceptance": ["feature.py exists"],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["feature.py exists"],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "affected_files": ["feature.py"],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
    "checks": [
        {
            "criterion": "The fixture command exits 0",
            "verification": "command",
            "command": ["python", "-c", "print('ok')"],
        }
    ],
    "test_command": [],
    "external_dependencies": [],
}


class FreeTextSpecTest(unittest.TestCase):
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
            task_qa=False,
            task_review=False,
            free_text_spec=True,
            peak_policy="always",
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
            self.settings,
            self.ledger,
            str(source),
            brief="A free-text project",
            name="free-text",
        )
        self.project = self.ledger.get_project(adopted.project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])
        self.repo = self.layout.repo_path("main")

    def _task(self) -> dict:
        return create_task(
            self.layout,
            "Add a feature",
            ["Create feature.py"],
            ["feature.py exists"],
            repo_id="main",
            test_command=[],
            spec="docs/program/requests/req.md",
            task_id="task-1",
        )

    def test_a_free_text_task_gets_a_formal_spec_before_coding(self) -> None:
        task = self._task()
        client = ScriptedModelClient(
            [
                json.dumps(SPEC),
                json.dumps(
                    {
                        "action": "write_file",
                        "path": "feature.py",
                        "content": "VALUE = 1\n",
                    }
                ),
                json.dumps({"action": "done", "summary": "added"}),
            ]
        )
        with patch(
            "forgel.daemon.peak.project_policy", return_value="always"
        ):
            run_daemon(
                self.settings,
                self.ledger,
                once=True,
                log=lambda _m: None,
                client=client,
            )
        stored = get_task(self.layout, "task-1")
        assert stored is not None
        self.assertTrue(stored["spec"].endswith("docs/program/specs/task-1.md"))
        self.assertEqual(stored["request"], "docs/program/requests/req.md")
        self.assertEqual(len(stored["checks"]), 1)
        self.assertEqual(stored["status"], "done")
        self.assertTrue((self.repo / "feature.py").exists())

    def test_an_unavailable_dependency_blocks_the_task(self) -> None:
        task = self._task()
        spec = dict(SPEC)
        spec["external_dependencies"] = [
            {
                "name": "weather",
                "interface": "HTTP forecast",
                "docs": "",
            }
        ]
        client = ScriptedModelClient(
            [
                json.dumps(spec),
                json.dumps(
                    {
                        "dependencies": [
                            {
                                "name": "weather",
                                "mode": "unavailable",
                                "interface": "HTTP forecast",
                                "docs": "",
                                "evidence": "",
                                "stub": "",
                            }
                        ]
                    }
                ),
            ]
        )
        with patch(
            "forgel.daemon.peak.project_policy", return_value="always"
        ):
            run_daemon(
                self.settings,
                self.ledger,
                once=True,
                log=lambda _m: None,
                client=client,
            )
        stored = get_task(self.layout, "task-1")
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertIn(
            "controlling agent stopped", stored["result"]["summary"]
        )
        self.assertFalse((self.repo / "feature.py").exists())


if __name__ == "__main__":
    unittest.main()
