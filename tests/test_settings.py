from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from forgel.config import Settings


class SettingsTest(unittest.TestCase):
    def test_local_sandbox_is_the_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FORGEL_SANDBOX": ""}, clear=False):
                settings = Settings.from_env(tmp)
            self.assertEqual(settings.sandbox, "local")

    def test_docker_sandbox_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FORGEL_SANDBOX": "docker"}, clear=False):
                settings = Settings.from_env(tmp)
            self.assertEqual(settings.sandbox, "docker")

    def test_unknown_sandbox_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FORGEL_SANDBOX": "chroot"}, clear=False):
                with self.assertRaises(ValueError):
                    Settings.from_env(tmp)

    def test_sandbox_limits_and_policy_are_read_from_env(self) -> None:
        env = {
            "FORGEL_SANDBOX": "docker",
            "FORGEL_SANDBOX_NETWORK": "bridge",
            "FORGEL_SANDBOX_CPUS": "1.5",
            "FORGEL_SANDBOX_MEMORY": "512m",
            "FORGEL_SANDBOX_PIDS": "128",
            "FORGEL_SANDBOX_IMAGES": "python:, ghcr.io/forgel-dev/",
            "FORGEL_SANDBOX_REQUIRE_DIGEST": "1",
            "FORGEL_SANDBOX_READ_ONLY": "0",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, env, clear=False):
                settings = Settings.from_env(tmp)
        self.assertEqual(settings.sandbox_network, "bridge")
        self.assertEqual(settings.sandbox_cpus, "1.5")
        self.assertEqual(settings.sandbox_memory, "512m")
        self.assertEqual(settings.sandbox_pids, 128)
        self.assertEqual(
            settings.sandbox_images,
            ("python:", "ghcr.io/forgel-dev/"),
        )
        self.assertTrue(settings.sandbox_require_digest)
        self.assertFalse(settings.sandbox_read_only)

    def test_context_window_is_read_from_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ, {"FORGEL_CONTEXT_WINDOW": "65536"}, clear=False
            ):
                settings = Settings.from_env(tmp)
        self.assertEqual(settings.context_window, 65536)

    def test_peak_settings_are_read_from_env(self) -> None:
        env = {
            "FORGEL_PEAK_POLICY": "always",
            "FORGEL_PEAK_HOURS": "2-3",
            "FORGEL_TIMEZONE": "Europe/Moscow",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, env, clear=False):
                settings = Settings.from_env(tmp)
        self.assertEqual(settings.peak_policy, "always")
        self.assertEqual(settings.peak_hours, "2-3")
        self.assertEqual(settings.timezone, "Europe/Moscow")

    def test_peak_policy_defaults_to_off_peak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ,
                {"FORGEL_PEAK_POLICY": "", "FORGEL_PEAK_HOURS": ""},
                clear=False,
            ):
                settings = Settings.from_env(tmp)
        self.assertEqual(settings.peak_policy, "off_peak")
        self.assertEqual(settings.peak_hours, "1-4,6-10")

    def test_invalid_peak_settings_are_rejected(self) -> None:
        cases = (
            {"FORGEL_PEAK_POLICY": "sometimes"},
            {"FORGEL_PEAK_HOURS": "4-1"},
            {"FORGEL_PEAK_HOURS": "nope"},
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as tmp:
                    with patch.dict(os.environ, case, clear=False):
                        with self.assertRaises(ValueError):
                            Settings.from_env(tmp)

    def test_invalid_context_window_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ, {"FORGEL_CONTEXT_WINDOW": "100"}, clear=False
            ):
                with self.assertRaises(ValueError):
                    Settings.from_env(tmp)

    def test_invalid_sandbox_limits_are_rejected(self) -> None:
        cases = (
            {"FORGEL_SANDBOX_NETWORK": "host"},
            {"FORGEL_SANDBOX_CPUS": "lots"},
            {"FORGEL_SANDBOX_CPUS": "0"},
            {"FORGEL_SANDBOX_MEMORY": "2 gigabytes"},
            {"FORGEL_SANDBOX_PIDS": "0"},
            {"FORGEL_SANDBOX_REQUIRE_DIGEST": "maybe"},
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as tmp:
                    with patch.dict(
                        os.environ,
                        {"FORGEL_SANDBOX": "docker", **case},
                        clear=False,
                    ):
                        with self.assertRaises(ValueError):
                            Settings.from_env(tmp)


if __name__ == "__main__":
    unittest.main()
