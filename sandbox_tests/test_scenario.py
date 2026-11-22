from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.model import ScriptedModelClient
from forgel.release_train import load_release
from forgel.scenario import (
    apply_seed,
    create_sandbox,
    sandbox_create_repository,
)


class ScenarioTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name)
        self.fixture = self.base / "fixture"
        self.fixture.mkdir()
        (self.fixture / "README.md").write_text(
            "# fixture\n", encoding="utf-8"
        )
        self._git(self.fixture, "init", "-q", "-b", "main")
        self._git(self.fixture, "add", "-A")
        self._git(
            self.fixture,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "fixture",
        )

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

    def test_a_sandbox_creates_local_repositories_only(self) -> None:
        sandbox = create_sandbox(
            self.fixture, root=self.base / "sandbox"
        )
        self.addCleanup(sandbox.ledger.close)

        created = sandbox_create_repository(
            sandbox.settings,
            sandbox.ledger,
            sandbox.project,
            "code",
        )

        self.assertEqual(created.entry["provider"], "local")
        self.assertEqual(created.url, "")
        repo = sandbox.layout.repo_path("code")
        self.assertTrue((repo / ".git").exists())
        remotes = subprocess.run(
            ["git", "remote", "-v"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertEqual(remotes.strip(), "")

    def test_a_sandbox_runs_a_message_through_the_real_router(self) -> None:
        sandbox = create_sandbox(
            self.fixture, root=self.base / "sandbox", keep=True
        )
        self.addCleanup(sandbox.ledger.close)
        self.addCleanup(sandbox.close)
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "sandbox answer"})]
        )

        replies = sandbox.run(["hello"], client=client)

        self.assertEqual(replies, ["sandbox answer"])
        history = (
            sandbox.layout.root
            / ".forgel"
            / "conversations"
            / "0.jsonl"
        )
        self.assertTrue(history.exists())
        text = history.read_text(encoding="utf-8")
        self.assertIn("hello", text)
        self.assertIn("sandbox answer", text)

    def test_a_scenario_can_seed_a_blocked_release(self) -> None:
        sandbox = create_sandbox(
            self.fixture, root=self.base / "sandbox"
        )
        self.addCleanup(sandbox.ledger.close)

        apply_seed(
            sandbox,
            {
                "release": {
                    "id": "20260101000000_seeded",
                    "title": "Fix the installer",
                    "status": "blocked",
                    "detail": "the audit found a defect",
                }
            },
        )

        stored = load_release(
            sandbox.layout, "20260101000000_seeded"
        )
        assert stored is not None
        self.assertEqual(stored["status"], "blocked")
        self.assertEqual(
            stored["detail"], "the audit found a defect"
        )
        self.assertEqual(stored["audit"]["verdict"], "fail")


if __name__ == "__main__":
    unittest.main()
