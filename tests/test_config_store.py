from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel import config_store, daemon_config
from forgel.project_config import ConfigError, load_project_config
from forgel.toml_edit import set_value, toml_literal


class TomlEditTest(unittest.TestCase):
    def test_replace_keeps_comments_and_other_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forgel.toml"
            path.write_text(
                "# keep me\n[qa]\nruntime = \"auto\"  # inline\n\n[x]\na = 1\n",
                encoding="utf-8",
            )
            set_value(path, "qa", "runtime", toml_literal("docker"))
            text = path.read_text(encoding="utf-8")
            self.assertIn("# keep me", text)
            self.assertIn('runtime = "docker"', text)
            self.assertIn("[x]", text)

    def test_insert_into_existing_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forgel.toml"
            path.write_text("[qa]\nruntime = \"auto\"\n", encoding="utf-8")
            set_value(path, "qa", "extra", toml_literal(3))
            text = path.read_text(encoding="utf-8")
            self.assertIn("runtime = \"auto\"", text)
            self.assertIn("extra = 3", text)

    def test_create_missing_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "forgel.toml"
            path.write_text("[qa]\nruntime = \"auto\"\n", encoding="utf-8")
            set_value(path, "budget", "per_feature_usd", toml_literal(12.5))
            text = path.read_text(encoding="utf-8")
            self.assertIn("[budget]", text)
            self.assertIn("per_feature_usd = 12.5", text)


class ConfigStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.control = self.home / "project"
        self.control.mkdir()
        (self.control / "forgel.toml").write_text(
            "[project]\nname = \"demo\"\nrecipe = \"hello-web@0.1.0\"\n"
            "\n[qa]\nruntime = \"auto\"\n"
            "\n[jurisdiction]\npack = \"ru\"\n"
            "\n[models]\ndefault = \"deepseek-chat\"\n"
            "architecture = \"deepseek-reasoner\"\n"
            "\n[budget]\nper_feature_usd = 10\nper_project_usd = 300\n"
            "\n[release]\nauto_patch = false\npropose_minor = false\n"
            "\n[simplicity]\nenabled = true\nmax_added_lines = 400\n"
            "max_new_config_keys = 2\nmax_compat_markers = 0\n"
            "\n[refactoring]\nenabled = true\nbudget_percent = 10\n"
            "allow_auto_targeted = true\n",
            encoding="utf-8",
        )

    def test_set_valid_project_value(self) -> None:
        value = config_store.set_project_value(
            self.control, "qa.runtime", "docker"
        )
        self.assertEqual(value, "docker")
        config = load_project_config(self.control)
        assert config is not None
        self.assertEqual(config.qa.runtime, "docker")

    def test_invalid_value_restores_the_file(self) -> None:
        before = (self.control / "forgel.toml").read_text(encoding="utf-8")
        with self.assertRaises(ConfigError):
            config_store.set_project_value(
                self.control, "qa.runtime", "nope"
            )
        after = (self.control / "forgel.toml").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            config_store.parse_project_value("qa.nope", "1")

    def test_daemon_defaults_and_overrides(self) -> None:
        self.assertEqual(
            daemon_config.get_value(self.home, "daemon.interval"), 2.0
        )
        self.assertEqual(
            daemon_config.value_source(self.home, "telegram.poll_timeout"),
            "default",
        )
        daemon_config.set_value(self.home, "telegram.poll_timeout", "10")
        self.assertEqual(
            daemon_config.get_value(self.home, "telegram.poll_timeout"), 10
        )
        self.assertEqual(
            daemon_config.value_source(self.home, "telegram.poll_timeout"),
            "daemon",
        )
        with self.assertRaises(daemon_config.DaemonConfigError):
            daemon_config.set_value(self.home, "telegram.poll_timeout", "99")

    def test_view_includes_sources_and_secrets(self) -> None:
        view = config_store.effective_view(self.home, self.control)
        self.assertIn("qa.runtime = auto (project)", view)
        self.assertIn("daemon.interval = 2 (default)", view)


if __name__ == "__main__":
    unittest.main()
