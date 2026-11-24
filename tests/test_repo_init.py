from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.model import ScriptedModelClient
from forgel.repo_init import RepoInitAgent


class RepoInitAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")

    def _agent(self, responses: list[dict]) -> RepoInitAgent:
        client = ScriptedModelClient(
            [json.dumps(item) for item in responses]
        )
        return RepoInitAgent(client, "model", log=lambda _m: None)

    def test_a_run_command_is_accepted(self) -> None:
        agent = self._agent(
            [
                {
                    "action": "run",
                    "command": ["python3", "-c", "pass"],
                },
                {
                    "action": "done",
                    "test": ["python3 -c pass"],
                },
            ]
        )
        self.assertEqual(
            agent.commands(
                self.repo, "main", allow_write=False
            ),
            ["python3 -c pass"],
        )

    def test_a_command_not_run_is_rejected(self) -> None:
        agent = self._agent(
            [
                {
                    "action": "done",
                    "test": ["python3 -c pass"],
                }
            ]
        )
        self.assertEqual(
            agent.commands(
                self.repo, "main", allow_write=False
            ),
            [],
        )

    def test_a_test_failure_still_counts_as_a_run_command(self) -> None:
        agent = self._agent(
            [
                {
                    "action": "run",
                    "command": ["python3", "-c", "raise SystemExit(1)"],
                },
                {
                    "action": "done",
                    "test": ["python3 -c 'raise SystemExit(1)'"],
                },
            ]
        )
        accepted = agent.commands(
            self.repo, "main", allow_write=False
        )
        self.assertEqual(len(accepted), 1)
        self.assertIn("raise SystemExit(1)", accepted[0])

    def test_an_existing_repository_cannot_be_written(self) -> None:
        agent = self._agent(
            [
                {
                    "action": "write_file",
                    "path": "test_new.py",
                    "content": "pass\n",
                },
                {"action": "done", "test": []},
            ]
        )
        self.assertEqual(
            agent.commands(
                self.repo, "main", allow_write=False
            ),
            [],
        )
        self.assertFalse((self.repo / "test_new.py").exists())

    def test_a_new_repository_can_set_up_and_run_an_empty_suite(self) -> None:
        agent = self._agent(
            [
                {
                    "action": "write_file",
                    "path": "tests/__init__.py",
                    "content": "",
                },
                {
                    "action": "run",
                    "command": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                    ],
                },
                {
                    "action": "done",
                    "test": [
                        "python3 -m unittest discover -s tests"
                    ],
                },
            ]
        )
        accepted = agent.commands(
            self.repo, "main", allow_write=True
        )
        self.assertEqual(
            accepted,
            ["python3 -m unittest discover -s tests"],
        )
        self.assertTrue((self.repo / "tests" / "__init__.py").exists())

    def test_no_model_client_returns_an_empty_list(self) -> None:
        agent = RepoInitAgent(None, "model", log=lambda _m: None)
        self.assertEqual(
            agent.commands(
                self.repo, "main", allow_write=True
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
