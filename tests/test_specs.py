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
    _normalize_spec,
    SpecError,
    documentation_problems,
    implementation_problems,
    render_spec,
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




class WorkPackageTest(unittest.TestCase):
    def _spec(self, packages=None):
        data = dict(VALID)
        data["requirements"] = ["First behavior", "Second behavior"]
        data["acceptance"] = [
            "First passes",
            "Second passes",
            "Third passes",
            "Fourth passes",
            "Fifth passes",
        ]
        if packages is not None:
            data["work_packages"] = packages
        return _normalize_spec(
            data,
            {"title": "Change", "summary": "A change", "repo_id": "main"},
        )

    def test_work_packages_partition_requirements_and_acceptance(self) -> None:
        spec = self._spec(
            [
                {
                    "title": "First package",
                    "requirements": [0],
                    "acceptance": [0, 1],
                },
                {
                    "title": "Second package",
                    "requirements": [1],
                    "acceptance": [2, 3, 4],
                },
            ]
        )
        self.assertEqual(len(spec["work_packages"]), 2)
        self.assertEqual(
            spec["work_packages"][0]["acceptance"], [0, 1]
        )
        self.assertEqual(
            spec["work_packages"][1]["requirements"], [1]
        )

    def test_a_missing_partition_defaults_to_one_package(self) -> None:
        data = dict(VALID)
        data["requirements"] = ["First behavior", "Second behavior"]
        data["acceptance"] = ["First passes", "Second passes"]
        spec = _normalize_spec(
            data,
            {"title": "Change", "summary": "A change", "repo_id": "main"},
        )
        self.assertEqual(len(spec["work_packages"]), 1)
        self.assertEqual(
            spec["work_packages"][0]["requirements"], [0, 1]
        )

    def test_a_large_spec_without_a_partition_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            self._spec()

    def test_a_package_over_four_acceptance_is_rejected(self) -> None:
        with self.assertRaises(SpecError):
            self._spec(
                [
                    {
                        "title": "Too broad",
                        "requirements": [0, 1],
                        "acceptance": [0, 1, 2, 3, 4],
                    }
                ]
            )

    def test_integer_like_package_indices_are_normalized(self) -> None:
        spec = self._spec(
            [
                {
                    "title": "First package",
                    "requirements": ["0"],
                    "acceptance": ["0", 1.0],
                },
                {
                    "title": "Second package",
                    "requirements": [1],
                    "acceptance": ["2", 3, 4],
                },
            ]
        )
        self.assertEqual(
            spec["work_packages"][0]["requirements"], [0]
        )
        self.assertEqual(
            spec["work_packages"][0]["acceptance"], [0, 1]
        )
        self.assertEqual(
            spec["work_packages"][1]["acceptance"], [2, 3, 4]
        )

    def test_non_integral_package_indices_are_rejected(self) -> None:
        for value in (True, 0.5, "one"):
            with self.assertRaises(SpecError):
                self._spec(
                    [
                        {
                            "title": "Bad package",
                            "requirements": [value],
                            "acceptance": [0, 1, 2, 3, 4],
                        }
                    ]
                )

    def test_work_packages_must_cover_every_item_once(self) -> None:
        with self.assertRaises(SpecError):
            self._spec(
                [
                    {
                        "title": "Partial",
                        "requirements": [0],
                        "acceptance": [0],
                    }
                ]
            )
        with self.assertRaises(SpecError):
            self._spec(
                [
                    {
                        "title": "One",
                        "requirements": [0, 1],
                        "acceptance": [0, 1],
                    },
                    {
                        "title": "Two",
                        "requirements": [1],
                        "acceptance": [2, 3, 4],
                    },
                ]
            )



    def test_rendered_spec_carries_the_work_packages(self) -> None:
        spec = self._spec(
            [
                {
                    "title": "First package",
                    "requirements": [0],
                    "acceptance": [0, 1],
                },
                {
                    "title": "Second package",
                    "requirements": [1],
                    "acceptance": [2, 3, 4],
                },
            ]
        )
        text = render_spec(spec, "task-1", "plan-1", "main")
        self.assertIn("## Work Packages", text)
        self.assertIn("First package", text)
        self.assertIn("First passes", text)
        self.assertIn("Second package", text)
        self.assertIn("Fifth passes", text)


if __name__ == "__main__":
    unittest.main()
