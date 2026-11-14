from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.daemon import handle_failure
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import create_task, get_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]

ACCEPT = json.dumps(
    {
        "verdict": "accept",
        "summary": "The change meets the requirements.",
        "rationale": "The endpoint and the test are present.",
        "proposed_criteria": [],
    }
)
CRITERIA = json.dumps(
    {
        "verdict": "criteria",
        "summary": "The criteria contradict each other.",
        "rationale": "One criterion requires X and another forbids it.",
        "proposed_criteria": ["Replace the conflicting pair with one rule."],
    }
)
FIX = json.dumps(
    {
        "verdict": "fix",
        "summary": "The endpoint is still missing.",
        "rationale": "The diff adds no route.",
        "proposed_criteria": [],
    }
)


class ArbiterTest(unittest.TestCase):
    def _settings(self, home: Path, **overrides) -> Settings:
        values = {
            "home": home,
            "registry_path": REPO_ROOT / "registry" / "recipes.json",
            "templates_path": REPO_ROOT / "src" / "forgel" / "templates",
            "jurisdiction_path": REPO_ROOT / "jurisdiction",
            "qa_runtime": "local",
            "task_reworks": 1,
            "task_arbiter": True,
            "task_accept": "auto",
        }
        values.update(overrides)
        return Settings(**values)

    def _project(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = Path(self._tmp.name)
        self.settings = self._settings(home)
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        project_id = create_project(
            self.settings,
            self.ledger,
            "Arbiter demo",
            "A demo.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
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
        return project, layout

    def _failed_task(
        self, layout, reworks: int = 1, kind: str = "review"
    ) -> dict:
        task = create_task(
            layout,
            "Add an endpoint",
            ["Add GET /health"],
            ["GET /health returns 200"],
            repo_id="main",
        )
        update_task(
            layout,
            task["id"],
            status="failed",
            result={
                "summary": "implemented",
                "failure": {
                    "kind": kind,
                    "message": "the reviewer rejected it",
                    "retryable": False,
                },
                "review": {
                    "status": "fail",
                    "summary": "missing endpoint",
                    "blocking": ["GET /health is missing"],
                    "requirements": [],
                },
                "qa": {"status": "pass", "checks": []},
                "rework_count": reworks,
                "attempts": 0,
            },
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        return stored

    def test_a_review_failure_is_sent_back_with_feedback(self) -> None:
        project, layout = self._project()
        task = self._failed_task(layout, reworks=0)
        handle_failure(
            self.settings,
            self.ledger,
            project,
            layout,
            task["id"],
            None,
            log=lambda _m: None,
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "pending")
        self.assertEqual(stored["result"]["rework_count"], 1)
        self.assertTrue(
            any(
                "GET /health is missing" in item
                for item in stored["result"]["feedback"]
            )
        )
        self.assertNotIn("failure", stored["result"])

    def test_exhausted_rework_goes_to_the_arbiter(self) -> None:
        project, layout = self._project()
        task = self._failed_task(layout, reworks=1)
        handle_failure(
            self.settings,
            self.ledger,
            project,
            layout,
            task["id"],
            ScriptedModelClient([ACCEPT]),
            log=lambda _m: None,
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "done")
        self.assertEqual(
            stored["result"]["acceptance"]["actor"], "arbiter"
        )
        self.assertEqual(
            stored["result"]["arbiter"]["verdict"], "accept"
        )

    def test_the_arbiter_can_rule_that_the_criteria_are_wrong(self) -> None:
        project, layout = self._project()
        task = self._failed_task(layout, reworks=1)
        dependent = create_task(
            layout,
            "Next",
            ["Next step"],
            ["It runs"],
            repo_id="main",
            depends_on=[task["id"]],
        )
        handle_failure(
            self.settings,
            self.ledger,
            project,
            layout,
            task["id"],
            ScriptedModelClient([CRITERIA]),
            log=lambda _m: None,
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["failure"]["kind"], "criteria"
        )
        self.assertEqual(
            stored["result"]["arbiter"]["proposed_criteria"],
            ["Replace the conflicting pair with one rule."],
        )
        blocked = get_task(layout, dependent["id"])
        assert blocked is not None
        self.assertEqual(blocked["status"], "blocked")

    def test_the_arbiter_can_confirm_the_reviewer(self) -> None:
        project, layout = self._project()
        task = self._failed_task(layout, reworks=1)
        handle_failure(
            self.settings,
            self.ledger,
            project,
            layout,
            task["id"],
            ScriptedModelClient([FIX]),
            log=lambda _m: None,
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["arbiter"]["verdict"], "fix"
        )


if __name__ == "__main__":
    unittest.main()
