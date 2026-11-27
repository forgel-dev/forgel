from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.controller import (
    OPERATIONS,
    RELEASE_ACTIONS,
    TASK_ACTIONS,
    ControllerError,
    decide,
    release_action,
    task_action,
)
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.projects import create_project
from forgel.tasks import create_task

REPO_ROOT = Path(__file__).resolve().parents[1]


class ControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.settings = Settings(
            home=Path(self._tmp.name),
            registry_path=REPO_ROOT / "registry" / "recipes.json",
            templates_path=REPO_ROOT / "src" / "forgel" / "templates",
            jurisdiction_path=REPO_ROOT / "jurisdiction",
            qa_runtime="local",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        project_id = create_project(
            self.settings, self.ledger, "controller", "A brief."
        )
        self.project = self.ledger.get_project(project_id)
        assert self.project is not None
        self.layout = ProjectLayout.detect(self.project["workspace"])

    def _decide(self, response: str):
        return decide(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            "task_failure",
            {"failure": {"kind": "code", "message": "the test failed"}},
            ScriptedModelClient([response]),
            log=lambda _m: None,
        )

    def test_a_decision_is_parsed(self) -> None:
        decision = self._decide(
            json.dumps(
                {
                    "operation": "rework",
                    "reason": "the test is missing",
                    "feedback": ["Add the test for the new branch"],
                }
            )
        )
        self.assertEqual(decision.operation, "rework")
        self.assertEqual(decision.reason, "the test is missing")
        self.assertEqual(
            decision.feedback, ["Add the test for the new branch"]
        )

    def test_an_unknown_operation_is_rejected(self) -> None:
        with self.assertRaises(ControllerError):
            self._decide(json.dumps({"operation": "deploy"}))

    def test_the_controller_can_page_the_context(self) -> None:
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "context_page",
                        "key": "failure",
                        "page": 1,
                    }
                ),
                json.dumps(
                    {"operation": "stop", "reason": "seen the failure"}
                ),
            ]
        )

        decision = decide(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            "task_failure",
            {
                "failure": {
                    "kind": "code",
                    "message": "BOOM-MARKER",
                }
            },
            client,
            log=lambda _m: None,
        )

        self.assertEqual(decision.operation, "stop")
        self.assertIn(
            "context_page", client.requests[0][1].content
        )
        self.assertIn(
            "BOOM-MARKER", client.requests[1][-1].content
        )

    def test_a_stopped_release_carries_every_task_spec(self) -> None:
        first = create_task(
            self.layout,
            "Blocked installer",
            ["Ship the installer"],
            ["The installer runs"],
            spec="docs/program/specs/blocked.md",
        )
        write_text(
            self.layout.artifact("docs/program/specs/blocked.md"),
            "SPEC-MARKER-BLOCKED",
        )
        second = create_task(
            self.layout,
            "Failed startup",
            ["Check the startup"],
            ["The startup check runs"],
            spec="docs/program/specs/failed.md",
        )
        write_text(
            self.layout.artifact("docs/program/specs/failed.md"),
            "SPEC-MARKER-FAILED",
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"operation": "stop", "reason": "seen the tasks"}
                )
            ]
        )

        decide(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            "release_failed_task",
            {
                "release": {"id": "release-1"},
                "tasks": [
                    {"id": first["id"], "status": "blocked"},
                    {"id": second["id"], "status": "failed"},
                ],
            },
            client,
            log=lambda _m: None,
        )

        prompt = client.requests[0][1].content
        self.assertIn("SPEC-MARKER-BLOCKED", prompt)
        self.assertIn("SPEC-MARKER-FAILED", prompt)
        self.assertIn(f"specification:{first['id']}", prompt)
        self.assertIn(f"specification:{second['id']}", prompt)

    def test_tool_markup_is_retried_with_a_json_correction(self) -> None:
        client = ScriptedModelClient(
            [
                "<|DSML|> calls> <|DSML|> invoke "
                'name="action": "context_page", "key": "failure", '
                '"page": 1}</|DSML|> parameter>',
                json.dumps(
                    {"operation": "stop", "reason": "seen"}
                ),
            ]
        )

        decision = decide(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            "task_failure",
            {"failure": {"kind": "code", "message": "BOOM-MARKER"}},
            client,
            log=lambda _m: None,
        )

        self.assertEqual(decision.operation, "stop")
        self.assertIn(
            "Return exactly one JSON object",
            client.requests[1][-1].content,
        )

    def test_every_operation_maps_for_both_stages(self) -> None:
        for operation in OPERATIONS:
            self.assertIn(task_action(operation), TASK_ACTIONS)
            self.assertIn(release_action(operation), RELEASE_ACTIONS)

    def test_a_non_json_answer_is_rejected(self) -> None:
        with self.assertRaises(ControllerError):
            self._decide("I will retry the task.")


if __name__ == "__main__":
    unittest.main()
