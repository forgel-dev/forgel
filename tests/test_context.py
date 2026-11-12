from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.context import effective_context, resolve_context


class ContextTest(unittest.TestCase):
    def test_priority_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("canon", encoding="utf-8")
            (workspace / "FORGEL.md").write_text("native", encoding="utf-8")
            (workspace / "CLAUDE.md").write_text("local", encoding="utf-8")

            files = resolve_context(workspace)
            self.assertEqual(
                [item.name for item in files],
                ["FORGEL.md", "AGENTS.md", "CLAUDE.md"],
            )
            self.assertTrue(files[0].native)
            self.assertFalse(files[1].native)

            text = effective_context(workspace)
            self.assertIn("# Source: FORGEL.md", text)
            self.assertIn("# Source: AGENTS.md", text)
            self.assertIn("# Source: CLAUDE.md", text)

    def test_missing_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "AGENTS.md").write_text("canon", encoding="utf-8")
            files = resolve_context(workspace)
            self.assertEqual([item.name for item in files], ["AGENTS.md"])
            self.assertEqual(effective_context(workspace), "# Source: AGENTS.md\n\ncanon")


if __name__ == "__main__":
    unittest.main()
