from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.agent import (
    ProjectAgent,
    UNFORMATTED_REPLY,
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
from forgel.release_train import list_releases
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
        self.assertIn("Runtime capabilities (this agent):", user)
        self.assertIn("github:", user)
        self.assertIn("Runtime process:", user)
        self.assertIn("runtime release train", user)
        self.assertIn("published tag is immutable", user)
        self.assertTrue(conversation_path(ProjectLayout.detect(project["workspace"])).exists())

    def test_a_user_visible_report_keeps_its_producer(self) -> None:
        project = self._project("Reports", "A brief.")
        layout = ProjectLayout.detect(project["workspace"])
        append_history(
            layout,
            "report",
            "REPORT-MARKER: published 1.2.3",
            "runtime",
            session="0",
            agent="release",
        )
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "ok"})]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        agent.handle(project, "next", "@tester", session="0")

        prompt = client.requests[0][1].content
        self.assertIn(
            "Report from release: REPORT-MARKER: published 1.2.3",
            prompt,
        )
        self.assertNotIn(
            "Assistant: REPORT-MARKER: published 1.2.3", prompt
        )

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

    def test_context_includes_project_and_repository_instructions(
        self,
    ) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Rules",
            "A rules brief.",
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
        layout.control.mkdir(parents=True, exist_ok=True)
        (layout.control / "FORGEL.md").write_text(
            "PROJECT-CONTEXT-MARKER\n", encoding="utf-8"
        )
        repo = layout.repo_path("main")
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "AGENTS.md").write_text(
            "REPO-CONTEXT-MARKER\n", encoding="utf-8"
        )
        context = build_context(layout, project, self.ledger)
        self.assertIn("PROJECT-CONTEXT-MARKER", context)
        self.assertIn("REPO-CONTEXT-MARKER", context)
        self.assertIn("take precedence", context)

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

    def test_a_batch_of_actions_and_an_answer_is_handled(self) -> None:
        project = self._project("Batch", "A batch brief.")
        response = json.dumps(
            [
                {
                    "kind": "action",
                    "action": "list_files",
                    "action_args": {"path": "."},
                },
                {"kind": "answer", "reply": "Batch answer"},
            ]
        )
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([response]),
        )
        result = agent.handle(project, "What is here?", "@tester")
        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "Batch answer")

    def test_failure_is_explained_to_the_user(self) -> None:
        project = self._project("Failure", "A failure brief.")
        response = {
            "kind": "answer",
            "reply": "GitHub is unreachable; check the VPN and retry.",
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        text = agent.explain_failure(
            project,
            "создай репозиторий",
            "error: GitHub auth request failed",
        )
        self.assertIn("GitHub", text)
        self.assertIn("VPN", text)

    def test_structured_reply_aliases_are_read(self) -> None:
        for key in ("message", "text", "content", "explanation", "answer"):
            answer = parse_answer(json.dumps({key: "A visible answer."}))
            self.assertEqual(answer["reply"], "A visible answer.", key)

    def test_explain_uses_a_structured_explanation(self) -> None:
        project = self._project("Explain", "An explain brief.")
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(
                [json.dumps({"explanation": "The test command failed."})]
            ),
        )
        text = agent.explain(
            project, "what happened?", "observation", fallback="FALLBACK"
        )
        self.assertEqual(text, "The test command failed.")

    def test_explain_never_returns_the_unformatted_fallback(self) -> None:
        project = self._project("Explain2", "An explain brief.")
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(['{"kind": "answer"}']),
        )
        text = agent.explain(
            project, "what happened?", "observation", fallback="FALLBACK"
        )
        self.assertEqual(text, "FALLBACK")
        self.assertNotEqual(text, UNFORMATTED_REPLY)

    def test_narrate_never_returns_the_unformatted_fallback(self) -> None:
        project = self._project("Narrate", "A narrate brief.")
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient(['{"kind": "answer"}']),
        )
        text = agent.narrate(project, "what happened?", "observation")
        self.assertNotIn(UNFORMATTED_REPLY, text)
        self.assertTrue(text.strip())

    def test_persistent_change_request_without_reply_is_not_an_error(self) -> None:
        project = self._project("Gamma", "A gamma brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        response = json.dumps(
            {
                "kind": "change_request",
                "title": "Add a health check",
                "summary": "Expose a health endpoint.",
                "requirements": ["Expose /health"],
                "acceptance": ["GET /health returns 200"],
                "repo_id": repo_id,
            }
        )
        client = ScriptedModelClient([response] * 4)
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Add a health check", "@tester")

        self.assertEqual(result.kind, "change_request")
        self.assertNotIn(UNFORMATTED_REPLY, result.text)
        self.assertIsNotNone(result.request)

    def test_change_request_is_recorded_as_an_artifact(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        response = {
            "kind": "change_request",
            "reply": "I recorded the request.",
            "title": "Add a dark theme",
            "summary": "Support a dark theme on the landing page.",
            "acceptance": ["The theme can be toggled."],
            "repo_id": repo_id,
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
        self.assertIn("Feature: Add a dark theme", text)
        self.assertIn("The theme can be toggled.", text)
        for heading in (
            "## Document Information",
            "## User Decisions",
            "## Functional Requirements",
            "## Tests",
            "## Risks",
            "## Affected Files",
            "## Revision History",
        ):
            self.assertIn(heading, text)
        self.assertNotIn("Please add dark mode.", text)
        stages = [event["stage"] for event in self.ledger.events(project["id"])]
        self.assertIn("request", stages)
        self.assertIn("agent", stages)

    def test_the_runtime_does_not_choose_a_repository_itself(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Unclear",
            "A multi-repository brief.",
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
                },
                {
                    "id": "code",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": ["main"],
                },
            ],
        )
        response = {
            "kind": "change_request",
            "reply": "I will change it.",
            "title": "Fix the install guide",
            "summary": "Use plain pip.",
            "requirements": ["Use plain pip"],
            "acceptance": ["The first install command uses pip"],
            "repo_id": "",
        }
        client = ScriptedModelClient([json.dumps(response)])
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(project, "Поправь установку", "@tester")

        self.assertIsNotNone(result.request)
        self.assertIsNone(result.task_id)
        self.assertNotIn("Which repository", result.text)
        self.assertIn("No task was queued", result.text)

    def test_a_long_answer_keeps_the_previous_message_in_context(
        self,
    ) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        append_history(
            layout,
            "user",
            "REPO-DECISION-MARKER: use the code repository",
            session="0",
        )
        append_history(
            layout, "assistant", "x" * 30_000, session="0"
        )
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "ok"})]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)

        agent.handle(project, "Add test dependencies", "@tester", session="0")

        prompt = client.requests[0][1].content
        self.assertIn("REPO-DECISION-MARKER", prompt)
        self.assertIn("turn truncated", prompt)

    def test_the_agent_can_inspect_another_repository(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Inspect",
            "A multi-repository brief.",
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
                },
                {
                    "id": "code",
                    "role": "application",
                    "provider": "local",
                    "url": "",
                    "depends_on": ["main"],
                },
            ],
        )
        code = layout.repo_path("code")
        source = code / "src" / "client.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "FORGEL-CODE-MARKER = 1\n", encoding="utf-8"
        )
        reading = json.dumps(
            {
                "kind": "action",
                "action": "read_file",
                "action_args": {
                    "path": "src/client.py",
                    "repo_id": "code",
                },
            }
        )
        final = json.dumps(
            {
                "kind": "change_request",
                "reply": "I will update the install guide.",
                "title": "Install Forgel Code with pip",
                "summary": "Use plain pip.",
                "requirements": ["Use plain pip"],
                "acceptance": ["The first install command uses pip"],
                "repo_id": "code",
            }
        )
        client = ScriptedModelClient([reading, final])
        agent = ProjectAgent(self.settings, self.ledger, client)

        result = agent.handle(
            project, "По Forgel Code: замени pipx на pip", "@tester"
        )

        self.assertIsNotNone(result.task_id)
        assert result.task_id is not None
        task = get_task(layout, result.task_id)
        assert task is not None
        self.assertEqual(task["repo_id"], "code")
        self.assertIn(
            "FORGEL-CODE-MARKER", client.requests[1][-1].content
        )

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
            "product_intent": "A dark mode across the application.",
            "user_experience": "The owner toggles the theme in settings.",
            "roadmap": ["Add the toggle", "Persist the choice"],
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
        self.assertEqual(task["release_class"], "minor")
        self.assertTrue(task["release_id"])
        releases = list_releases(layout)
        self.assertEqual(len(releases), 1)
        self.assertEqual(releases[0]["id"], task["release_id"])
        self.assertEqual(releases[0]["release_class"], "minor")
        self.assertIn("main", releases[0]["repos"])
        self.assertEqual(task["requirements"], ["Add a dark theme toggle"])
        self.assertEqual(
            task["assumptions"],
            ["The toggle belongs to the main application"],
        )
        self.assertIn("Queued task", result.text)
        self.assertIn("Release plan", result.text)
        self.assertIn("main 0.1.0", result.text)
        assert result.request is not None
        request_text = layout.artifact(result.request).read_text(
            encoding="utf-8"
        )
        self.assertIn("## Assumptions", request_text)
        self.assertIn("main application", request_text)
        self.assertIn("## Product Intent", request_text)
        self.assertIn("A dark mode across the application.", request_text)
        self.assertIn(
            "The owner toggles the theme in settings.", request_text
        )
        self.assertIn("## Roadmap", request_text)
        self.assertIn("Persist the choice", request_text)

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

    def test_multiple_actions_are_parsed_in_order(self) -> None:
        answer = parse_answer(
            json.dumps(
                {
                    "kind": "actions",
                    "reply": "",
                    "actions": [
                        {"action": "accept"},
                        {"action": "plan", "action_args": {"goal": "M1"}},
                    ],
                }
            )
        )
        self.assertEqual(answer["kind"], "actions")
        self.assertEqual(
            [item["action"] for item in answer["actions"]],
            ["accept", "plan"],
        )
        self.assertEqual(
            answer["actions"][1]["action_args"], {"goal": "M1"}
        )

    def test_tool_call_markup_is_never_shown_to_the_user(self) -> None:
        markup = (
            "<｜｜DSML｜｜ calls><｜｜DSML｜｜ invoke name=\"action\">"
            "</｜｜DSML｜｜ invoke></｜｜DSML｜｜ calls>"
        )
        answer = parse_answer(markup)
        self.assertEqual(answer["reply"], UNFORMATTED_REPLY)
        self.assertNotIn("DSML", answer["reply"])

    def test_the_agent_retries_after_tool_call_markup(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        markup = (
            "<｜｜DSML｜｜ calls><｜｜DSML｜｜ invoke name=\"action\">"
            "</｜｜DSML｜｜ invoke></｜｜DSML｜｜ calls>"
        )
        client = ScriptedModelClient(
            [
                markup,
                json.dumps(
                    {"kind": "answer", "reply": "Вот план работы."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        result = agent.handle(project, "Какой план?", "@tester")
        self.assertEqual(result.text, "Вот план работы.")
        self.assertIn(
            "tool-call markup", client.requests[1][-1].content
        )

    def test_answer_retries_do_not_exhaust_the_research_loop(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        repo_id = manifest_entries(layout)[0]["id"]
        repo = layout.repo_path(repo_id)
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "README.md").write_text("marker\n", encoding="utf-8")
        reading = json.dumps(
            {
                "kind": "action",
                "action": "list_files",
                "action_args": {"path": ".", "repo_id": repo_id},
            }
        )
        client = ScriptedModelClient(
            [reading] * 6
            + [
                "<｜｜DSML｜｜ calls>",
                json.dumps(
                    {"kind": "answer", "reply": "After research."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        result = agent.handle(project, "Что здесь?", "@tester")
        self.assertEqual(result.text, "After research.")

    def test_a_change_request_without_a_reply_is_retried(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        client = ScriptedModelClient(
            [
                json.dumps(
                    {
                        "kind": "change_request",
                        "reply": "",
                        "title": "Something",
                        "requirements": ["Do it"],
                        "acceptance": ["It works"],
                    }
                ),
                json.dumps(
                    {"kind": "answer", "reply": "Just an answer."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        result = agent.handle(project, "Вопрос", "@tester")
        self.assertEqual(result.kind, "answer")
        self.assertEqual(result.text, "Just an answer.")

    def test_a_plan_object_is_retried_as_an_answer(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        client = ScriptedModelClient(
            [
                json.dumps({"notes": "plan", "tasks": []}),
                json.dumps(
                    {"kind": "answer", "reply": "План: сначала M0.5."}
                ),
            ]
        )
        agent = ProjectAgent(self.settings, self.ledger, client)
        result = agent.handle(project, "Какой план?", "@tester")
        self.assertEqual(result.text, "План: сначала M0.5.")
        self.assertIn(
            "cannot be shown", client.requests[1][-1].content
        )

    def test_process_tool_results_are_not_replayed(self) -> None:
        project = self._project("Alpha", "An alpha brief.")
        layout = ProjectLayout.detect(project["workspace"])
        append_history(
            layout,
            "tool",
            "PROCESS-MARKER",
            "@tester",
            session="s",
            tool="read_file",
            path="docs/program/state.md",
        )
        append_history(
            layout,
            "tool",
            "DOC-MARKER",
            "@tester",
            session="s",
            tool="read_file",
            path="README.md",
        )
        append_history(layout, "user", "hello", "@tester", session="s")
        append_history(
            layout, "assistant", UNFORMATTED_REPLY, "@tester", session="s"
        )
        agent = ProjectAgent(
            self.settings, self.ledger, ScriptedModelClient([])
        )
        history = agent._session_history(layout, "s")
        self.assertNotIn("PROCESS-MARKER", history)
        self.assertIn("DOC-MARKER", history)
        self.assertNotIn(UNFORMATTED_REPLY, history)

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
