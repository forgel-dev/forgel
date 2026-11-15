from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.adopt import adopt_repository
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.planner import (
    MAX_RESEARCH_STEPS,
    PlanningError,
    plan_project,
    plan_status,
)
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.tasks import list_tasks, update_task

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
            "checks": [
                {
                    "criterion": "GET /health returns 200",
                    "command": ["python", "-m", "unittest", "tests.test_health"],
                }
            ],
        },
        {
            "title": "Add an index page",
            "requirements": ["Add GET /"],
            "acceptance": ["GET / returns 200"],
            "repo_id": "main",
            "depends_on": [0],
            "checks": [
                {
                    "criterion": "GET / returns 200",
                    "command": ["python", "-m", "unittest", "tests.test_index"],
                }
            ],
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

    def test_plan_status_follows_its_tasks(self) -> None:
        result = self._plan()
        summary = plan_status(self.layout, result.plan_id)
        self.assertEqual(summary["status"], "running")
        first, second = list_tasks(self.layout)
        update_task(self.layout, first["id"], status="failed")
        summary = plan_status(self.layout, result.plan_id)
        self.assertEqual(summary["status"], "stalled")
        self.assertEqual(summary["counts"].get("failed"), 1)
        update_task(self.layout, first["id"], status="done")
        update_task(self.layout, second["id"], status="review")
        summary = plan_status(self.layout, result.plan_id)
        self.assertEqual(summary["status"], "review")
        update_task(self.layout, second["id"], status="done")
        summary = plan_status(self.layout, result.plan_id)
        self.assertEqual(summary["status"], "done")

    def test_dry_run_creates_nothing(self) -> None:
        result = self._plan(dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertNotIn("task_id", result.tasks[0])
        self.assertEqual(result.artifact, "")
        self.assertEqual(list_tasks(self.layout), [])

    def test_a_task_without_checks_is_rejected(self) -> None:
        payload = {
            "tasks": [
                {
                    "title": "No checks",
                    "requirements": ["x"],
                    "acceptance": ["y"],
                    "repo_id": "main",
                }
            ]
        }
        with self.assertRaises(PlanningError):
            self._plan(payload)

    def test_a_review_only_check_is_accepted(self) -> None:
        payload = {
            "tasks": [
                {
                    "title": "Docs",
                    "requirements": ["Write the docs"],
                    "acceptance": ["The prose is accurate"],
                    "repo_id": "main",
                    "checks": [
                        {
                            "criterion": "The prose is accurate",
                            "verification": "review",
                        }
                    ],
                }
            ]
        }
        result = self._plan(payload)
        self.assertEqual(
            result.tasks[0]["checks"][0]["verification"], "review"
        )

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

    def test_research_budget_forces_the_plan(self) -> None:
        responses = [
            json.dumps({"action": "list_files", "path": "."})
            for _ in range(MAX_RESEARCH_STEPS + 1)
        ] + [json.dumps(PLAN)]
        client = ScriptedModelClient(responses)
        result = plan_project(
            self.settings,
            self.ledger,
            self.project,
            "Bring the project to M1",
            client=client,
            dry_run=True,
            log=lambda _m: None,
        )
        self.assertEqual(len(result.tasks), 2)
        self.assertTrue(
            any(
                "Research budget exhausted" in message.content
                for message in client.requests[-1]
            )
        )

    def test_planner_retries_after_tool_markup(self) -> None:
        markup = (
            "<｜｜DSML｜｜ calls><｜｜DSML｜｜ invoke name=\"plan\">"
            "</｜｜DSML｜｜ invoke></｜｜DSML｜｜ calls>"
        )
        client = ScriptedModelClient([markup, json.dumps(PLAN)])
        result = plan_project(
            self.settings,
            self.ledger,
            self.project,
            "Bring the project to M1",
            client=client,
            dry_run=True,
            log=lambda _m: None,
        )
        self.assertEqual(len(result.tasks), 2)
        self.assertIn(
            "tool-call markup", client.requests[1][-1].content
        )

    def test_plan_works_for_an_adopted_linked_project(self) -> None:
        source = Path(self._tmp.name) / "linked-source"
        source.mkdir()
        (source / "README.md").write_text(
            "# Linked\n\nMilestone: ship M1.\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=source, check=True)
        subprocess.run(["git", "add", "-A"], cwd=source, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "initial",
            ],
            cwd=source,
            check=True,
        )
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), name="linked"
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"action": "read_file", "path": "README.md"}
                ),
                json.dumps(PLAN),
            ]
        )
        result = plan_project(
            self.settings,
            self.ledger,
            project,
            "Ship M1",
            client=client,
            log=lambda _m: None,
        )
        self.assertEqual(len(result.tasks), 2)
        self.assertTrue(
            (source / "docs" / "program" / "plans" / f"{result.plan_id}.md")
            .exists()
        )
        self.assertTrue(
            list((source / "docs" / "program" / "tasks").glob("*.json"))
        )
        observation = client.requests[1][-1].content
        self.assertIn("Milestone: ship M1", observation)

    def test_plan_research_cannot_escape_the_repository(self) -> None:
        source = Path(self._tmp.name) / "linked-source"
        source.mkdir()
        (source / "README.md").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=source, check=True)
        subprocess.run(["git", "add", "-A"], cwd=source, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-q",
                "-m",
                "initial",
            ],
            cwd=source,
            check=True,
        )
        adopted = adopt_repository(
            self.settings, self.ledger, str(source), name="linked"
        )
        project = self.ledger.get_project(adopted.project_id)
        assert project is not None
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "action": "read_file",
                        "path": "../../etc/passwd",
                    }
                ),
                json.dumps(PLAN),
            ]
        )
        plan_project(
            self.settings,
            self.ledger,
            project,
            "Ship M1",
            client=client,
            log=lambda _m: None,
        )
        observation = client.requests[1][-1].content
        self.assertIn("escapes the repository", observation)
        self.assertNotIn("root:", observation)


if __name__ == "__main__":
    unittest.main()
