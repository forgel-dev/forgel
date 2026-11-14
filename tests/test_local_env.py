from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.local_env import (
    LocalEnvError,
    init_local_env,
    load_local_env,
    parse_env_file,
)


class ParseEnvFileTest(unittest.TestCase):
    def test_comments_export_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.local"
            path.write_text(
                "# comment\n"
                "FORGEL_A=one\n"
                "export FORGEL_B=\"two words\"\n"
                "FORGEL_C='three'\n"
                "\n",
                encoding="utf-8",
            )
            values = parse_env_file(path)
        self.assertEqual(
            values,
            {"FORGEL_A": "one", "FORGEL_B": "two words", "FORGEL_C": "three"},
        )

    def test_a_malformed_line_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.local"
            path.write_text("just a line\n", encoding="utf-8")
            with self.assertRaises(LocalEnvError):
                parse_env_file(path)


class LoadEnvTest(unittest.TestCase):
    def test_process_environment_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env.local").write_text(
                "FORGEL_TEST_VALUE=from-file\n", encoding="utf-8"
            )
            with patch.dict(
                os.environ, {"FORGEL_TEST_VALUE": "from-process"}, clear=False
            ):
                load_local_env(Path(tmp), None)
                self.assertEqual(
                    os.environ["FORGEL_TEST_VALUE"], "from-process"
                )

    def test_local_file_wins_over_plain_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                "FORGEL_TEST_VALUE=plain\n", encoding="utf-8"
            )
            (Path(tmp) / ".env.local").write_text(
                "FORGEL_TEST_VALUE=local\n", encoding="utf-8"
            )
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FORGEL_TEST_VALUE", None)
                loaded = load_local_env(Path(tmp), None)
                self.assertEqual(
                    os.environ["FORGEL_TEST_VALUE"], "local"
                )
        self.assertEqual(len(loaded), 2)

    def test_unrelated_keys_are_not_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env.local").write_text(
                "PATH=/evil\nFORGEL_OK=yes\n", encoding="utf-8"
            )
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("FORGEL_OK", None)
                load_local_env(Path(tmp), None)
                self.assertNotEqual(os.environ.get("PATH"), "/evil")
                self.assertEqual(os.environ.get("FORGEL_OK"), "yes")


class InitEnvTest(unittest.TestCase):
    def test_creates_a_local_file_and_ignores_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = init_local_env(Path(tmp))
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("FORGEL_MODEL_API_KEY", text)
            self.assertNotIn("DEPLOY_HOST", text)
            gitignore = (Path(tmp) / ".gitignore").read_text(
                encoding="utf-8"
            )
            self.assertIn(".env.local", gitignore)
            with self.assertRaises(LocalEnvError):
                init_local_env(Path(tmp))
            init_local_env(Path(tmp), force=True)


if __name__ == "__main__":
    unittest.main()
