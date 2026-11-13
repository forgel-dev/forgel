from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from forgel.secrets import (
    SecretError,
    delete_secret,
    get_secret,
    secret_status,
    secrets_path,
    set_secret,
)


class SecretsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_file_is_private_and_persistent(self) -> None:
        path = set_secret(self.home, "model.api_key", "sk-test")
        self.assertEqual(path, secrets_path(self.home))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(get_secret(self.home, "model.api_key", {}), "sk-test")

    def test_environment_wins(self) -> None:
        set_secret(self.home, "model.api_key", "from-file")
        value = get_secret(
            self.home,
            "model.api_key",
            {"FORGEL_MODEL_API_KEY": "from-env"},
        )
        self.assertEqual(value, "from-env")
        status = secret_status(
            self.home, {"FORGEL_MODEL_API_KEY": "from-env"}
        )
        self.assertEqual(status["model.api_key"], "env")

    def test_status_reports_file_and_missing(self) -> None:
        set_secret(self.home, "github.token", "ghp_test")
        status = secret_status(self.home, {})
        self.assertEqual(status["github.token"], "file")
        self.assertEqual(status["model.api_key"], "missing")

    def test_delete(self) -> None:
        set_secret(self.home, "github.token", "ghp_test")
        self.assertTrue(delete_secret(self.home, "github.token"))
        self.assertFalse(delete_secret(self.home, "github.token"))
        self.assertEqual(get_secret(self.home, "github.token", {}), "")

    def test_unknown_and_multiline_values_are_rejected(self) -> None:
        with self.assertRaises(SecretError):
            set_secret(self.home, "unknown.key", "value")
        with self.assertRaises(SecretError):
            set_secret(self.home, "model.api_key", "line1\nline2")
        with self.assertRaises(SecretError):
            set_secret(self.home, "model.api_key", "   ")


if __name__ == "__main__":
    unittest.main()
