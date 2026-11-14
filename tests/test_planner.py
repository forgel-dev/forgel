from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.planner import PlanningError, plan_project
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import list_tasks

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN = {
    "notes": "Two small steps, in order.",
    "tasks": [
        {
            "title": "Add a health endpoint",
            "requirements": ["Add GET /health"],
            "acceptance": ["GET /health returns 200"],
            "repo_id": "main",
            "test_command": ["python", "-m", "unittest"],
        },
        {
            "title": "Add an index page",
            "requirements": ["Add GET /"],
            "acceptance": ["GET / returns 200"],
            "repo_id": "main",
            "depends_on": [0],
        },
    ],
}


class PlannerTest(unittest.TestCase):
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
        self.project_id = create_project(
            self.settings,
            self.ledger,
            "Plan demo",
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

    def _plan(self, payload: dict = PLAN, **kwargs):
        client = ScriptedModelClient([json.dumps(payload)])
        return plan_project(
            self.settings,
            self.ledger,
            self.project,
            "Bring the project to M1",
            client=client,
            log=lambda _m: None,
            **kwargs,
        )

    def test_plan_creates_ordered_tasks_with_dependencies(self) -> None:
        result = self._plan()
        self.assertEqual(len(result.tasks), 2)
        created = list_tasks(self.layout)
        self.assertEqual(len(created), 2)
        first, second = created[0], created[1]
        self.assertEqual(first["order"], 1)
        self.assertEqual(second["order"], 2)
        self.assertEqual(second["depends_on"], [first["id"]])
        self.assertEqual(first["plan_id"], result.plan_id)
        self.assertEqual(first["plan_goal"], "Bring the project to M1")
        self.assertTrue(
            (self.layout.root / result.artifact).exists()
        )
        stages = [
            event["stage"] for event in self.ledger.events(self.project_id)
        ]
        self.assertIn("plan", stages)

    def test_dry_run_creates_nothing(self) -> None:
        result = self._plan(dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertNotIn("task_id", result.tasks[0])
        self.assertEqual(result.artifact, "")
        self.assertEqual(list_tasks(self.layout), [])

    def test_unknown_repository_is_rejected(self) -> None:
        payload = {
            "tasks": [
                {
                    "title": "Bad",
                    "requirements": ["x"],
                    "acceptance": ["y"],
                    "repo_id": "other",
                }
            ]
        }
        with self.assertRaises(PlanningError):
            self._plan(payload)

    def test_forward_dependency_is_rejected(self) -> None:
        payload = {
            "tasks": [
                {
                    "title": "First",
                    "requirements": ["x"],
                    "acceptance": ["y"],
                    "repo_id": "main",
                    "depends_on": [1],
                },
                {
                    "title": "Second",
                    "requirements": ["x"],
                    "acceptance": ["y"],
                    "repo_id": "main",
                },
            ]
        }
        with self.assertRaises(PlanningError):
            self._plan(payload)

    def test_too_many_tasks_are_rejected(self) -> None:
        payload = {
            "tasks": [
                {
                    "title": f"Task {index}",
                    "requirements": ["x"],
                    "acceptance": ["y"],
                    "repo_id": "main",
                }
                for index in range(3)
            ]
        }
        with self.assertRaises(PlanningError):
            self._plan(payload, max_tasks=2)

    def test_peak_hours_defer_planning(self) -> None:
        with patch(
            "forgel.planner.peak.should_defer", return_value=True
        ):
            with self.assertRaises(PlanningError) as ctx:
                self._plan()
        self.assertIn("paused", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
