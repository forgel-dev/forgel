from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.artifacts import write_json
from forgel.layout import ProjectLayout
from forgel.runtime_model import process_model


class RuntimeModelTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.layout = ProjectLayout.detect(self._tmp.name)

    def test_the_map_covers_every_main_stage_and_gate(self) -> None:
        text = process_model(self.layout, {"id": "demo"})

        for stage in (
            "intake and control",
            "project setup",
            "planning",
            "execution",
            "verification",
            "release",
            "deploy",
            "external changes",
        ):
            self.assertIn(stage, text)
        self.assertIn("Control and gates:", text)
        self.assertIn("Release policy:", text)
        self.assertIn("published tag is immutable", text)
        self.assertIn("never by an agent", text)
        self.assertIn("without its audit is not published", text)
        self.assertNotIn("Current releases:", text)

    def test_the_map_lists_the_current_releases(self) -> None:
        write_json(
            self.layout.artifact(
                "docs/program/releases/20260101000000_demo/release.json"
            ),
            {
                "id": "20260101000000_demo",
                "title": "Demo release",
                "status": "released",
                "repos": {"code": {"version": "1.2.3"}},
            },
        )

        text = process_model(self.layout, {"id": "demo"})

        self.assertIn("Current releases:", text)
        self.assertIn("Demo release: released (code 1.2.3)", text)


if __name__ == "__main__":
    unittest.main()
