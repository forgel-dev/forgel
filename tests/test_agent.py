from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.agent import (
    ProjectAgent,
    append_history,
    build_context,
    conversation_path,
    load_history,
    load_session_state,
    parse_answer,
)
from forgel.artifacts import write_text
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger, new_project_id
from forgel.model import ScriptedModelClient
from forgel.program_manifest import entries as manifest_entries
from forgel.program_manifest import set_entries
from forgel.repo_tools import RepoActionError, execute_repo_action
from forgel.project_config import render_project_config
from forgel.projects import create_project
from forgel.tasks import get_task

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

    def test_context_uses_documents_not_internal_bookkeeping(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        repo = layout.repo_path(repo_id)
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "README-MARKER\n\n# Roadmap\n", encoding="utf-8"
        )
        (repo / "PLAN.md").write_text(
            "PLAN-MARKER\n", encoding="utf-8"
        )
        (repo / "AGENTS.md").write_text(
            "AGENTS-MARKER\n", encoding="utf-8"
        )
        (repo / "FORGEL.md").write_text(
            "FORGEL-MARKER\n", encoding="utf-8"
        )
        context = build_context(layout, project, self.ledger)
        self.assertIn("README-MARKER", context)
        self.assertIn("PLAN-MARKER", context)
        self.assertIn("AGENTS-MARKER", context)
        self.assertIn("FORGEL-MARKER", context)
        self.assertNotIn("Workspace layout", context)
        self.assertNotIn("Recent ledger events", context)
        self.assertNotIn("adopted", context.lower())

    def test_context_reads_only_tracked_documents(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        repo = layout.repo_path(repo_id)
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "TRACKED-MARKER\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
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
            cwd=repo,
            check=True,
        )
        (repo / "LOCAL.md").write_text(
            "UNTRACKED-MARKER\n", encoding="utf-8"
        )
        context = build_context(layout, project, self.ledger)
        self.assertIn("TRACKED-MARKER", context)
        self.assertNotIn("UNTRACKED-MARKER", context)

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
        self.assertIsNone(result.task_id)
        assert result.request is not None
        artifact = Path(project["workspace"]) / result.request
        self.assertTrue(artifact.exists())
        text = artifact.read_text(encoding="utf-8")
        self.assertIn("Change Request: Add a dark theme", text)
        self.assertIn("The theme can be toggled.", text)
        stages = [event["stage"] for event in self.ledger.events(project["id"])]
        self.assertIn("request", stages)
        self.assertIn("agent", stages)

    def test_change_request_queues_a_task(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Beta",
            "A beta brief.",
            mode="brownfield",
        )
        layout = ProjectLayout.detect(
            self.ledger.get_project(project_id)["workspace"]
        )
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
        project = self.ledger.get_project(project_id)
        assert project is not None
        response = {
            "kind": "change_request",
            "reply": "Queued.",
            "title": "Add dark mode",
            "summary": "Add a dark theme toggle.",
            "requirements": ["Add a dark theme toggle"],
            "acceptance": ["The toggle is visible"],
            "constraints": ["standard library only"],
            "repo_id": "main",
            "test_command": ["python", "-m", "unittest"],
            "assumptions": ["The toggle belongs to the main application"],
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        result = agent.handle(project, "Add dark mode", "@tester")
        self.assertIsNotNone(result.task_id)
        assert result.task_id is not None
        task = get_task(layout, result.task_id)
        assert task is not None
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["repo_id"], "main")
        self.assertEqual(task["requirements"], ["Add a dark theme toggle"])
        self.assertEqual(
            task["assumptions"],
            ["The toggle belongs to the main application"],
        )
        self.assertIn("Queued task", result.text)
        assert result.request is not None
        request_text = layout.artifact(result.request).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Assumptions", request_text)
        self.assertIn("main application", request_text)

    def test_a_control_action_is_parsed_and_returned(self) -> None:
        project = self._project("Actions", "A brief.")
        response = {
            "kind": "action",
            "reply": "Planning the milestone.",
            "action": "plan",
            "action_args": {"goal": "Bring it to M1"},
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        result = agent.handle(project, "доведи до M1", "@tester")
        self.assertEqual(result.kind, "action")
        self.assertEqual(result.action, "plan")
        assert result.args is not None
        self.assertEqual(result.args["goal"], "Bring it to M1")
        self.assertIsNone(result.task_id)

    def test_an_unknown_action_falls_back_to_an_answer(self) -> None:
        project = self._project("Actions", "A brief.")
        response = {
            "kind": "action",
            "reply": "I cannot change secrets.",
            "action": "secret",
            "action_args": {},
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        result = agent.handle(project, "set the key", "@tester")
        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.action, "")

    def test_non_json_answer_falls_back_to_text(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        client = ScriptedModelClient(["Just a plain answer."])
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Hello", "@tester")

        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "Just a plain answer.")

    def test_action_without_a_reply_is_not_a_failed_answer(self) -> None:
        answer = parse_answer('{"kind": "action", "action": "status"}')
        self.assertEqual(answer["kind"], "action")
        self.assertEqual(answer["action"], "status")
        self.assertEqual(answer["reply"], "")

    def test_json_without_a_reply_is_not_dumped(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(['{"kind": "answer"}']),
        )

        result = agent.handle(project, "Hello", "@tester")

        self.assertNotIn("{", result.text)
        self.assertNotIn('"kind"', result.text)
        self.assertTrue(result.text.strip())

    def test_broken_json_is_not_dumped(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(['{"kind": "answer", broken']),
        )

        result = agent.handle(project, "Hello", "@tester")

        self.assertNotIn("{", result.text)
        self.assertTrue(result.text.strip())

    def test_narration_failure_returns_language_not_the_dump(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        agent = ProjectAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        text = agent.narrate(
            project, "status?", "project: alpha\nlayout: linked"
        )
        self.assertNotIn("project:", text)
        self.assertNotIn("layout:", text)
        self.assertTrue(text.strip())

    def test_research_cannot_read_process_artifacts(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        with self.assertRaises(RepoActionError):
            execute_repo_action(
                layout,
                manifest_entries(layout),
                {
                    "action": "read_file",
                    "path": "docs/program/state.md",
                },
            )

    def test_agent_reads_repository_files_before_answering(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        repo = layout.repo_path(repo_id)
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text(
            "PROJECT DOC MARKER\n", encoding="utf-8"
        )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "kind": "action",
                        "action": "read_file",
                        "action_args": {
                            "path": "README.md",
                            "repo_id": repo_id,
                        },
                    }
                ),
                json.dumps(
                    {"kind": "answer", "reply": "Документ прочитан."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Что в README?", "@tester")

        self.assertEqual(result.text, "Документ прочитан.")
        observation = client.requests[1][-1].content
        self.assertIn("PROJECT DOC MARKER", observation)
        turns = load_history(layout)
        self.assertTrue(
            any(
                turn["role"] == "tool"
                and "PROJECT DOC MARKER" in turn["text"]
                for turn in turns
            )
        )

    def test_session_history_keeps_more_than_eight_turns(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        for index in range(10):
            append_history(
                layout, "user", f"USER-{index}", session="7"
            )
            append_history(
                layout, "assistant", f"ANSWER-{index}", session="7"
            )
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "ok"})]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        agent.handle(project, "next", "@tester", session="7")

        prompt = client.requests[0][1].content
        self.assertIn("USER-0", prompt)
        self.assertIn("USER-9", prompt)

    def test_switching_projects_keeps_separate_sessions(self) -> None:
        first = self._project("First", "First brief.")
        second = self._project("Second", "Second brief.")
        client = ScriptedModelClient(
            [
                json.dumps({"kind": "answer", "reply": "A"}),
                json.dumps({"kind": "answer", "reply": "B"}),
                json.dumps({"kind": "answer", "reply": "A2"}),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        agent.handle(first, "FIRST-MARKER", "@tester", session="7")
        agent.handle(second, "SECOND-MARKER", "@tester", session="7")
        agent.handle(first, "again", "@tester", session="7")

        prompt = client.requests[2][1].content
        self.assertIn("FIRST-MARKER", prompt)
        self.assertNotIn("SECOND-MARKER", prompt)

    def test_older_turns_are_compacted_into_a_session_summary(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        for index in range(6):
            append_history(
                layout,
                "user",
                f"old turn {index} " + "x" * 60,
                session="0",
            )
        client = ScriptedModelClient(
            [
                json.dumps(
                    {"kind": "answer", "reply": "SUMMARY-MARKER"}
                ),
                json.dumps({"kind": "answer", "reply": "final"}),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        with patch("forgel.agent.HISTORY_COMPACT_CHARS", 100), patch(
            "forgel.agent.HISTORY_KEEP_TURNS", 2
        ), patch("forgel.agent.HISTORY_RECENT_CHARS", 500):
            agent.handle(project, "next", "@tester", session="0")
        state = load_session_state(layout, "0")
        self.assertEqual(state["summary"], "SUMMARY-MARKER")
        prompt = client.requests[1][1].content
        self.assertIn("SUMMARY-MARKER", prompt)

    def test_agent_cannot_read_outside_the_repository(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        repo = layout.repo_path(repo_id)
        repo.mkdir(parents=True, exist_ok=True)
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "kind": "action",
                        "action": "read_file",
                        "action_args": {
                            "path": "../../etc/passwd",
                            "repo_id": repo_id,
                        },
                    }
                ),
                json.dumps(
                    {"kind": "answer", "reply": "Не удалось прочитать."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        agent.handle(project, "Прочитай passwd", "@tester")

        observation = client.requests[1][-1].content
        self.assertIn("escapes the repository", observation)
        self.assertNotIn("root:", observation)

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
