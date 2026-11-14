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

    def test_docker_sandbox_is_not_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"FORGEL_SANDBOX": "docker"}, clear=False):
                with self.assertRaises(ValueError):
                    Settings.from_env(tmp)


if __name__ == "__main__":
    unittest.main()
