from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project
from forgel.specs import (
    MAX_SPEC_RETRIES,
    SpecError,
    documentation_problems,
    implementation_problems,
    write_task_spec,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

VALID = {
    "problem": "The client needs the change.",
    "outcome": "The change is in the client.",
    "scope": ["the client"],
    "non_goals": [],
    "requirements": ["Make the change"],
    "acceptance": ["The change is present"],
    "constraints": [],
    "assumptions": [],
    "risks": [],
    "goals": ["The change is present"],
    "user_decisions": [],
    "user_stories": [],
    "open_questions": [],
    "affected_files": ["forgel_code/cli.py"],
    "related_documents": [],
    "revision_history": ["1.0.0 — initial"],
    "external_dependencies": [],
}


class ImplementationDetailTest(unittest.TestCase):
    def test_commands_files_and_runtime_steps_are_rejected(self) -> None:
        problems = implementation_problems(
            {
                "requirements": [
                    "Run `git commit` and update README.md"
                ],
                "acceptance": ["The file tests/test_cli.py changes"],
                "goals": ["curl https://example.com"],
                "constraints": ["The runtime commit step passes"],
            }
        )
        self.assertGreaterEqual(len(problems), 4)

    def test_behavior_text_is_accepted(self) -> None:
        self.assertEqual(
            implementation_problems(
                {
                    "requirements": [
                        "The install command points to the current release."
                    ],
                    "acceptance": [
                        "A reader who copies the command gets the current "
                        "release."
                    ],
                    "goals": ["The documented install path is current."],
                    "constraints": ["No network access is required."],
                }
            ),
            [],
        )


class DocumentationRuleTest(unittest.TestCase):
    def test_a_documentation_task_rejects_a_documentation_test(self) -> None:
        problems = documentation_problems(
            {
                "title": "Update README.md install instructions",
                "summary": "Documentation fix",
            },
            {
                "problem": "README.md is stale",
                "outcome": "The documentation is current",
                "requirements": ["Add a test that reads README.md."],
                "acceptance": ["A reader sees the current release."],
            },
        )
        self.assertTrue(problems)

    def test_a_documentation_task_without_tests_is_clean(self) -> None:
        self.assertEqual(
            documentation_problems(
                {
                    "title": "Update the documentation",
                    "summary": "Documentation fix",
                },
                {
                    "problem": "The documentation is stale",
                    "outcome": "The documentation is current",
                    "requirements": [
                        "The documentation names the current release."
                    ],
                    "acceptance": ["A reader sees the current release."],
                },
            ),
            [],
        )

    def test_a_code_task_is_clean(self) -> None:
        self.assertEqual(
            documentation_problems(
                {"title": "Add a module", "summary": "Code"},
                {
                    "problem": "The module is missing",
                    "outcome": "The module exists",
                    "requirements": ["The module exists."],
                    "acceptance": ["The module works."],
                },
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
