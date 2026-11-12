from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.project_config import (
    ConfigError,
    load_project_config,
    render_project_config,
)


class ProjectConfigTest(unittest.TestCase):
    def test_render_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forgel.toml"
            path.write_text(
                render_project_config(
                    "demo",
                    "hello-web@0.1.0",
                    qa_runtime="docker",
                    jurisdiction_pack="eu",
                ),
                encoding="utf-8",
            )
            config = load_project_config(Path(tmp))
            self.assertIsNotNone(config)
            assert config is not None
            self.assertEqual(config.name, "demo")
            self.assertEqual(config.recipe, "hello-web@0.1.0")
            self.assertEqual(config.qa.runtime, "docker")
            self.assertEqual(config.jurisdiction.pack, "eu")
            self.assertEqual(config.budget.per_feature_usd, 10.0)
            self.assertEqual(config.budget.per_project_usd, 300.0)
            self.assertFalse(config.release.auto_patch)
            self.assertFalse(config.release.propose_minor)
            self.assertTrue(config.simplicity.enabled)
            self.assertEqual(config.simplicity.max_added_lines, 400)
            self.assertTrue(config.refactoring.enabled)
            self.assertEqual(config.refactoring.budget_percent, 10)

    def test_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_project_config(Path(tmp)))

    def test_invalid_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                '[qa]\nruntime = "bogus"\n', encoding="utf-8"
            )
            with self.assertRaises(ConfigError):
                load_project_config(Path(tmp))

    def test_invalid_toml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text("[qa\n", encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_project_config(Path(tmp))

    def test_negative_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                "[budget]\nper_feature_usd = -1\n", encoding="utf-8"
            )
            with self.assertRaises(ConfigError):
                load_project_config(Path(tmp))

    def test_release_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                "[release]\nauto_patch = true\npropose_minor = true\n",
                encoding="utf-8",
            )
            config = load_project_config(Path(tmp))
            self.assertIsNotNone(config)
            assert config is not None
            self.assertTrue(config.release.auto_patch)
            self.assertTrue(config.release.propose_minor)

    def test_release_flags_must_be_boolean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                '[release]\nauto_patch = "yes"\n', encoding="utf-8"
            )
            with self.assertRaises(ConfigError):
                load_project_config(Path(tmp))

    def test_simplicity_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                "[simplicity]\nenabled = false\nmax_added_lines = 50\n",
                encoding="utf-8",
            )
            config = load_project_config(Path(tmp))
            self.assertIsNotNone(config)
            assert config is not None
            self.assertFalse(config.simplicity.enabled)
            self.assertEqual(config.simplicity.max_added_lines, 50)

    def test_refactoring_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "forgel.toml").write_text(
                "[refactoring]\nenabled = false\nbudget_percent = 0\n",
                encoding="utf-8",
            )
            config = load_project_config(Path(tmp))
            self.assertIsNotNone(config)
            assert config is not None
            self.assertFalse(config.refactoring.enabled)
            self.assertEqual(config.refactoring.budget_percent, 0)


if __name__ == "__main__":
    unittest.main()
