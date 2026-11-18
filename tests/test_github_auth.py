from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.providers.github_auth import GithubAuth, GithubAuthError
from forgel.secrets import set_secret


class GithubAuthTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)

    def test_pat_resolution(self) -> None:
        set_secret(self.home, "github.token", "ghp_test")
        auth = GithubAuth(self.home, environ={})
        token = auth.resolve("auto")
        self.assertEqual(token.kind, "pat")
        self.assertEqual(token.token, "ghp_test")
        self.assertIn("PAT configured", auth.status())

    def test_missing_credentials(self) -> None:
        auth = GithubAuth(self.home, environ={})
        self.assertIn("no API token", auth.status())
        with self.assertRaises(GithubAuthError):
            auth.resolve("auto")
        with self.assertRaises(GithubAuthError):
            auth.resolve("pat")
        with self.assertRaises(GithubAuthError):
            auth.resolve("github_app")

    def test_deploy_key_has_no_api_token(self) -> None:
        auth = GithubAuth(self.home, environ={})
        with self.assertRaises(GithubAuthError):
            auth.resolve("deploy_key")

    def test_app_needs_a_private_key_or_crypto(self) -> None:
        set_secret(self.home, "github.app_id", "123")
        key_path = self.home / "app.pem"
        key_path.write_text("not a real key", encoding="utf-8")
        set_secret(
            self.home, "github.app_private_key_path", str(key_path)
        )
        auth = GithubAuth(self.home, environ={})
        self.assertTrue(auth.app_ready())
        with self.assertRaises(GithubAuthError):
            auth.resolve("github_app")

    def test_bad_key_path_is_reported_in_status(self) -> None:
        set_secret(self.home, "github.app_id", "123")
        set_secret(
            self.home,
            "github.app_private_key_path",
            str(self.home / "missing.pem"),
        )
        auth = GithubAuth(self.home, environ={})
        self.assertIn("misconfigured", auth.status())

    def test_a_failed_app_falls_back_to_a_pat(self) -> None:
        set_secret(self.home, "github.app_id", "123")
        set_secret(
            self.home,
            "github.app_private_key_path",
            str(self.home / "missing.pem"),
        )
        set_secret(self.home, "github.token", "ghp_test")
        auth = GithubAuth(self.home, environ={})
        token = auth.resolve("github_app")
        self.assertEqual(token.kind, "pat")
        self.assertEqual(token.token, "ghp_test")

    def test_gh_token_and_cli_session_are_sources(self) -> None:
        env_auth = GithubAuth(self.home, environ={"GH_TOKEN": "ghp_env"})
        self.assertEqual(env_auth.resolve("auto").kind, "pat")
        session = GithubAuth(self.home, environ={})
        with patch.object(
            GithubAuth, "session_token", return_value="gho_session"
        ):
            token = session.resolve("auto")
            self.assertEqual(token.kind, "session")
            self.assertIn("GitHub CLI session", session.status())


if __name__ == "__main__":
    unittest.main()
