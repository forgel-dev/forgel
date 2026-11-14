from __future__ import annotations

import argparse
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from forgel.cli import cmd_doctor
from forgel.secrets import set_secret


class DoctorTest(unittest.TestCase):
    def test_doctor_reports_a_configured_installation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            set_secret(home, "github.token", "ghp_test")
            (home / "model-script.json").write_text(
                '{"responses": []}', encoding="utf-8"
            )
            env = {
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_ALLOWED_CHAT_IDS": "1",
                "FORGEL_MODEL_MODE": "script",
            }
            args = argparse.Namespace(home=str(home))
            out = io.StringIO()
            with patch.dict(os.environ, env, clear=False):
                with patch(
                    "forgel.cli.shutil.which", return_value="/usr/bin/tool"
                ):
                    with redirect_stdout(out):
                        code = cmd_doctor(args)
            text = out.getvalue()
            self.assertEqual(code, 0, text)
            self.assertIn("RESULT: OK", text)
            self.assertIn("ledger", text)
            self.assertIn("telegram", text)
            self.assertIn("model", text)

    def test_doctor_warns_without_telegram_and_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "TELEGRAM_BOT_TOKEN": "",
                "TELEGRAM_ALLOWED_CHAT_IDS": "",
                "FORGEL_MODEL_MODE": "off",
                "FORGEL_MODEL_API_KEY": "",
            }
            args = argparse.Namespace(home=tmp)
            out = io.StringIO()
            with patch.dict(os.environ, env, clear=False):
                with redirect_stdout(out):
                    code = cmd_doctor(args)
            self.assertEqual(code, 1)
            self.assertIn("WARN telegram", out.getvalue())
            self.assertIn("WARN model", out.getvalue())


if __name__ == "__main__":
    unittest.main()
