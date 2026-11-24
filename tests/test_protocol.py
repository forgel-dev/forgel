from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel import protocol, specs
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.daemon import _handle_spec_issues, handle_failure
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import create_task, get_task, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC = {
    "problem": "The task needs a contract.",
    "outcome": "The contract is implemented.",
    "scope": ["the change"],
    "non_goals": [],
    "requirements": ["Do the thing"],
    "acceptance": ["The thing works"],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The thing works"],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "affected_files": ["app.py"],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
}


class PlannerGateTest(unittest.TestCase):
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
            task_reworks=5,
            task_accept="auto",
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "Gate demo",
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

    def _task(self, reworks: int = 0) -> dict:
        task = create_task(
            self.layout,
            "Implement the contract",
            [],
            [],
            repo_id="main",
            spec=specs.spec_path("task-1"),
            task_id="task-1",
        )
        write_text(
            self.layout.artifact(specs.spec_path("task-1")),
            "# Task Spec\n\nThe contract is fixed here.\n",
        )
        update_task(
            self.layout,
            task["id"],
            result={"rework_count": reworks},
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        return stored

    def _failed_review(self, task: dict, **review) -> dict:
        data = dict(task.get("result") or {})
        data["review"] = {
            "status": "fail",
            "summary": review.get("summary", "the change is incomplete"),
            "blocking": list(review.get("blocking") or []),
            "requirements": list(review.get("requirements") or []),
        }
        data["failure"] = {
            "kind": "review",
            "message": "task review failed",
            "retryable": False,
        }
        return update_task(
            self.layout,
            task["id"],
            status="failed",
            result=data,
        )

    def _run_failure(self, task: dict, client: ScriptedModelClient) -> None:
        handle_failure(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            task["id"],
            client,
            log=lambda _m: None,
        )

    def test_a_rejected_deviation_sends_the_task_back(self) -> None:
        task = self._task(reworks=1)
        update_task(
            self.layout,
            task["id"],
            status="done",
            result={
                **dict(task.get("result") or {}),
                "spec_issues": [
                    {
                        "requirement": "Do the thing",
                        "problem": "the thing cannot be done",
                        "proposal": "do another thing",
                    }
                ],
            },
        )
        current = get_task(self.layout, task["id"])
        assert current is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "decisions": [
                            {
                                "index": 0,
                                "rewrite": False,
                                "reason": "the requirement is achievable",
                            }
                        ]
                    }
                )
            ]
        )
        _handle_spec_issues(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            current,
            list(current["result"]["spec_issues"]),
            client,
            log=lambda _m: None,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertEqual(
            stored["result"]["failure"]["kind"], "spec"
        )
        self.assertIn(
            "follow the accepted specification",
            stored["result"]["spec_feedback"][0],
        )

    def test_an_accepted_deviation_rewrites_the_specification(self) -> None:
        task = self._task(reworks=1)
        update_task(
            self.layout,
            task["id"],
            status="done",
            result={
                **dict(task.get("result") or {}),
                "spec_issues": [
                    {
                        "requirement": "Do the thing",
                        "problem": "the thing contradicts the outcome",
                        "proposal": "do the corrected thing",
                    }
                ],
            },
        )
        current = get_task(self.layout, task["id"])
        assert current is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "decisions": [
                            {
                                "index": 0,
                                "rewrite": True,
                                "reason": "the requirement contradicts "
                                "the outcome",
                            }
                        ]
                    }
                ),
                json.dumps(SPEC),
            ]
        )
        _handle_spec_issues(
            self.settings,
            self.ledger,
            self.project,
            self.layout,
            current,
            list(current["result"]["spec_issues"]),
            client,
            log=lambda _m: None,
        )
        stored = get_task(self.layout, task["id"])
        assert stored is not None
        self.assertEqual(stored["status"], "failed")
        self.assertIn(
            "rewrote the specification",
            stored["result"]["spec_feedback"][0],
        )
        text = self.layout.artifact(specs.spec_path("task-1")).read_text(
            encoding="utf-8"
        )
        self.assertIn("The thing works", text)
        self.assertEqual(stored["requirements"], SPEC["requirements"])
        self.assertEqual(stored["acceptance"], SPEC["acceptance"])

