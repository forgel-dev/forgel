from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.agent import (
    ProjectAgent,
    append_history,
    build_context,
    conversation_path,
    load_history,
    parse_answer,
)
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger, new_project_id
from forgel.model import ScriptedModelClient
from forgel.project_config import render_project_config

REPO_ROOT = Path(__file__).resolve().parents[1]


class AgentTest(unittest.TestCase):
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

    def _project(self, name: str, brief: str) -> dict:
        project_id = new_project_id(name)
        workspace = self.settings.projects_dir / project_id
        workspace.mkdir(parents=True)
        write_text(
            workspace / "forgel.toml",
            render_project_config(name, recipe="hello-web@0.1.0"),
        )
        self.ledger.create_project(project_id, name, brief, str(workspace))
        project = self.ledger.get_project(project_id)
        assert project is not None
        return project

    def test_answer_builds_a_project_scoped_prompt(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "It is a demo."})]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "What is this?", "@tester")

        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "It is a demo.")
        system = client.requests[0][0].content
        user = client.requests[0][1].content
        self.assertIn("Alph", system)
        self.assertIn(project["id"], system)
        self.assertIn("An alpha brief.", user)
        self.assertTrue(conversation_path(ProjectLayout.detect(project["workspace"])).exists())

    def test_change_request_is_recorded_as_an_artifact(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        response = {
            "kind": "change_request",
            "reply": "I recorded the request.",
            "title": "Add a dark theme",
            "summary": "Support a dark theme on the landing page.",
            "acceptance": ["The theme can be toggled."],
        }
        client = ScriptedModelClient([json.dumps(response)])
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Please add dark mode.", "@tester")

        self.assertEqual(result.kind, "change_request")
        self.assertIsNotNone(result.request)
        assert result.request is not None
        artifact = Path(project["workspace"]) / result.request
        self.assertTrue(artifact.exists())
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("Change Request: Add a dark theme", text)
        self.assertIn("The theme can be toggled.", text)
        stages = [event["stage"] for event in self.ledger.events(project["id"])]
        self.assertIn("request", stages)
        self.assertIn("agent", stages)

    def test_non_json_answer_falls_back_to_text(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        client = ScriptedModelClient(["Just a plain answer."])
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Hello", "@tester")

        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "Just a plain answer.")

    def test_model_failure_is_reported_without_a_crash(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        agent = ProjectAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        result = agent.handle(project, "Hello", "@tester")
        self.assertEqual(result.kind, "error")
        self.assertIn("Model call failed", result.text)

    def test_context_and_history_do_not_cross_projects(self) -> None:
        alpha = self._project("Alpha Marker", "Alpha brief marker.")
        beta = self._project("Beta Marker", "Beta brief marker.")
        write_text(
            Path(beta["workspace"]) / "program.yaml",
            "project: beta-marker-secret\n",
        )
        append_history(
            ProjectLayout.detect(beta["workspace"]),
            "user",
            "beta conversation marker",
        )
        context = build_context(
            ProjectLayout.detect(alpha["workspace"]), alpha, self.ledger
        )
        self.assertIn("Alpha brief marker.", context)
        self.assertNotIn("Beta brief marker", context)
        self.assertNotIn("beta-marker-secret", context)
        self.assertNotIn("beta conversation marker", context)
        history = load_history(ProjectLayout.detect(alpha["workspace"]))
        self.assertEqual(history, [])

    def test_parse_answer_handles_fenced_json(self) -> None:
        parsed = parse_answer(
            '```json\n{"kind": "answer", "reply": "ok"}\n```'
        )
        self.assertEqual(parsed["kind"], "answer")
        self.assertEqual(parsed["reply"], "ok")


if __name__ == "__main__":
    unittest.main()
