from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.agent import ProjectAgent
from forgel.config import Settings
from forgel.console import (
    _explain_outcomes,
    _task_observation,
    _task_snapshot,
    run_console,
)
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.projects import create_project
from forgel.tasks import create_task, get_task, list_tasks, update_task

REPO_ROOT = Path(__file__).resolve().parents[1]


def _feed(lines: list[str]):
    remaining = list(lines)

    def read(_prompt: str) -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return read


class ConsoleTest(unittest.TestCase):
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
        )
        self.ledger = Ledger(self.settings.db_path)
        self.addCleanup(self.ledger.close)

    def _run(self, lines: list[str], agent=None):
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            daemon=False,
            input_fn=_feed(lines),
            output=output.append,
            agent=agent,
        )
        return "\n".join(output)

    def test_new_project_and_selection_work_without_telegram(self) -> None:
        text = self._run(["/new Demo | A demo brief.", "/projects", "/quit"])
        self.assertIn("Forgel console", text)
        projects = self.ledger.list_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Demo")
        self.assertEqual(self.ledger.get_session(0), projects[0]["id"])
        self.assertIn(projects[0]["id"], text)

    def test_starts_with_a_selected_project(self) -> None:
        project_id = create_project(
            self.settings, self.ledger, "Selected", "A brief."
        )
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            project_id=project_id,
            daemon=False,
            input_fn=_feed(["/status", "/quit"]),
            output=output.append,
        )
        self.assertIn(f"Selected {project_id}", "\n".join(output))
        self.assertEqual(self.ledger.get_session(0), project_id)

    def test_free_text_records_a_change_request(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Console agent",
            "A brief.",
            mode="brownfield",
        )
        layout = ProjectLayout.detect(
            self.ledger.get_project(project_id)["workspace"]
        )
        from forgel.program_manifest import set_entries

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
        self.ledger.set_session(0, project_id)
        response = {
            "kind": "change_request",
            "reply": "Recorded.",
            "title": "Add a page",
            "requirements": ["Add a page"],
            "acceptance": ["The page exists"],
            "repo_id": "main",
            "assumptions": ["The page goes in the main app"],
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        text = self._run(
            ["Add a page to the app", "/tasks", "/quit"], agent=agent
        )
        self.assertIn("Recorded.", text)
        self.assertIn("Add a page", text)

    def test_a_russian_free_text_request_stores_russian_language(
        self,
    ) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Russian console",
            "A brief.",
            mode="brownfield",
        )
        layout = ProjectLayout.detect(
            self.ledger.get_project(project_id)["workspace"]
        )
        from forgel.program_manifest import set_entries

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
        self.ledger.set_session(0, project_id)
        response = {
            "kind": "change_request",
            "reply": "Записал.",
            "title": "Добавить страницу",
            "requirements": ["Добавить страницу"],
            "acceptance": ["Страница существует"],
            "repo_id": "main",
            "assumptions": ["Страница в основном приложении"],
        }
        agent = ProjectAgent(
            self.settings,
            self.ledger,
            ScriptedModelClient([json.dumps(response)]),
        )
        self._run(["Добавь страницу", "/quit"], agent=agent)
        tasks = list_tasks(layout)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["language"], "ru")

    def test_task_observation_contains_the_real_cause(self) -> None:
        project_id = create_project(
            self.settings, self.ledger, "Tasks", "A brief."
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        task = create_task(
            layout,
            "Fix the README",
            ["Update README"],
            ["README is updated"],
            repo_id="main",
            test_command=[],
        )
        update_task(
            layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "repeated action loop: read_file:README.md",
                "failure": {
                    "kind": "agent",
                    "message": "the agent read README.md five times",
                },
                "files_changed": ["README.md"],
                "report": "docs/program/agent/run.md",
            },
        )
        stored = get_task(layout, task["id"])
        assert stored is not None
        observation = _task_observation(stored, layout)
        self.assertEqual(observation["status"], "failed")
        self.assertIn(
            "repeated action loop", observation["summary"]
        )
        self.assertIn(
            "read README.md five times",
            observation["failure"]["message"],
        )
        self.assertEqual(
            observation["files_changed"], ["README.md"]
        )

    def test_outcome_explanation_uses_the_model_and_the_request(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Outcomes",
            "A brief.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        layout = ProjectLayout.detect(project["workspace"])
        task = create_task(
            layout,
            "Fix the README",
            ["Update README"],
            ["README is updated"],
            repo_id="main",
            test_command=[],
        )
        before = _task_snapshot(layout)
        update_task(
            layout,
            str(task["id"]),
            status="failed",
            result={
                "summary": "repeated action loop: read_file:README.md",
                "failure": {
                    "kind": "agent",
                    "message": "the agent read README.md five times",
                },
                "files_changed": ["README.md"],
                "report": "docs/program/agent/run.md",
            },
        )
        reply = (
            "Агент зациклился на перечитывании README и не дошёл до правки. "
            "Задача не закрыта; её нужно перезапустить, иначе очередь стоит."
        )
        client = ScriptedModelClient([reply])
        answer = _explain_outcomes(
            ProjectAgent(self.settings, self.ledger, client),
            project,
            layout,
            before,
            "ru",
            "Продолжаем",
        )
        self.assertEqual(answer, reply)
        prompt = client.requests[0][-1].content
        self.assertIn("Продолжаем", prompt)
        self.assertIn("repeated action loop", prompt)
        self.assertIn("README.md", prompt)

    def test_quit_and_eof_end_the_console(self) -> None:
        text = self._run(["/quit"])
        self.assertIn("Bye.", text)
        text = self._run([])
        self.assertIn("Bye.", text)

    def test_a_missing_model_is_reported_with_the_setup_command(
        self,
    ) -> None:
        output: list[str] = []
        with patch(
            "forgel.console.build_model_client", return_value=None
        ):
            run_console(
                self.settings,
                self.ledger,
                daemon=False,
                input_fn=_feed(["/quit"]),
                output=output.append,
            )
        text = "\n".join(output)
        self.assertIn("not fully configured", text)
        self.assertIn("forgel setup", text)
        self.assertIn("FORGEL_MODEL_API_KEY", text)

    def test_daemon_mode_returns_when_there_is_nothing_to_do(self) -> None:
        output: list[str] = []
        run_console(
            self.settings,
            self.ledger,
            daemon=True,
            input_fn=_feed(["/projects", "/quit"]),
            output=output.append,
        )
        self.assertIn("Bye.", "\n".join(output))

    def test_a_model_configured_after_start_enables_free_text(self) -> None:
        project_id = create_project(
            self.settings,
            self.ledger,
            "Late model",
            "A brief.",
            mode="brownfield",
        )
        from forgel.program_manifest import set_entries

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
        client = ScriptedModelClient(
            [json.dumps({"kind": "answer", "reply": "late answer"})]
        )
        output: list[str] = []
        with patch(
            "forgel.console.build_model_client",
            side_effect=[None, client],
        ):
            run_console(
                self.settings,
                self.ledger,
                project_id=project_id,
                daemon=False,
                input_fn=_feed(["hello", "/quit"]),
                output=output.append,
            )
        self.assertIn("late answer", "\n".join(output))
        self.assertEqual(len(client.requests), 1)

    def test_help_puts_plain_language_first(self) -> None:
        text = self._run(["/help", "/quit"])
        self.assertIn("Talk in plain language", text)
        self.assertIn("/adopt", text)
        self.assertIn("accept the latest task", text)


if __name__ == "__main__":
    unittest.main()
