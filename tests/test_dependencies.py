from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgel import dependencies
from forgel.config import Settings
from forgel.layout import ProjectLayout
from forgel.ledger import Ledger
from forgel.model import ScriptedModelClient
from forgel.program_manifest import set_entries
from forgel.projects import create_project

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC = {
    "title": "Use the weather service",
    "repo_id": "main",
    "external_dependencies": [
        {
            "name": "weather",
            "interface": "HTTP forecast",
            "docs": "docs/weather.md",
        }
    ],
}


class DependencyTest(unittest.TestCase):
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
        project_id = create_project(
            self.settings,
            self.ledger,
            "deps",
            "A demo.",
            mode="brownfield",
        )
        project = self.ledger.get_project(project_id)
        assert project is not None
        self.layout = ProjectLayout.detect(project["workspace"])
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

    def _investigate(self, dependencies_payload: list[dict]) -> list[dict]:
        client = ScriptedModelClient(
            [json.dumps({"dependencies": dependencies_payload})]
        )
        return dependencies.investigate(
            self.layout,
            {"title": "Use weather", "summary": "Forecast"},
            SPEC,
            client,
            log=lambda _m: None,
        )

    def test_a_direct_dependency_needs_evidence(self) -> None:
        result = self._investigate(
            [
                {
                    "name": "weather",
                    "mode": "direct",
                    "interface": "local fixture",
                    "docs": "docs/weather.md",
                    "evidence": "environment.yaml declares the local fixture",
                    "stub": "",
                }
            ]
        )
        self.assertEqual(result[0]["mode"], "direct")

    def test_a_stub_needs_evidence_and_code(self) -> None:
        result = self._investigate(
            [
                {
                    "name": "weather",
                    "mode": "stub",
                    "interface": "HTTP forecast",
                    "docs": "docs/weather.md",
                    "evidence": "docs/weather.md, forecast response example",
                    "stub": "def forecast():\n    return {'temp': 20}\n",
                }
            ]
        )
        self.assertEqual(result[0]["mode"], "stub")
        self.assertIn("forecast", result[0]["stub"])
        with self.assertRaises(dependencies.DependencyError):
            self._investigate(
                [
                    {
                        "name": "weather",
                        "mode": "stub",
                        "interface": "HTTP forecast",
                        "docs": "",
                        "evidence": "",
                        "stub": "",
                    }
                ]
            )

    def test_unavailable_documentation_blocks_planning(self) -> None:
        with self.assertRaises(dependencies.DependencyError):
            self._investigate(
                [
                    {
                        "name": "weather",
                        "mode": "unavailable",
                        "interface": "HTTP forecast",
                        "docs": "",
                        "evidence": "",
                        "stub": "",
                    }
                ]
            )

    def test_no_dependencies_makes_no_model_call(self) -> None:
        client = ScriptedModelClient([])
        result = dependencies.investigate(
            self.layout,
            {"title": "Local only"},
            {"external_dependencies": []},
            client,
            log=lambda _m: None,
        )
        self.assertEqual(result, [])
        self.assertEqual(client.requests, [])


if __name__ == "__main__":
    unittest.main()
