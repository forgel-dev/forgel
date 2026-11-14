from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgel.providers import (
    GitProvider,
    GithubProvider,
    ProviderError,
    get_provider,
)
from forgel.secrets import set_secret


def _make_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "initial",
        ],
        cwd=path,
        check=True,
    )
    return path


class ProviderTest(unittest.TestCase):
    def test_provider_selection(self) -> None:
        self.assertIsInstance(
            get_provider("https://github.com/o/r"), GithubProvider
        )
        self.assertIsInstance(get_provider("owner/repo"), GithubProvider)
        self.assertIsInstance(
            get_provider("https://gitlab.com/o/r"), GitProvider
        )
        self.assertIsInstance(get_provider("/tmp/local"), GitProvider)

    def test_github_parse_forms(self) -> None:
        provider = GithubProvider()
        for value in (
            "o/r",
            "https://github.com/o/r",
            "https://github.com/o/r.git",
            "git@github.com:o/r.git",
            "ssh://git@github.com/o/r.git",
        ):
            remote = provider.parse(value)
            self.assertEqual(remote.provider, "github")
            self.assertEqual(remote.slug, "o/r")
            self.assertNotIn("token", remote.url)
        self.assertEqual(
            provider.parse("o/r").url, "https://github.com/o/r.git"
        )
        self.assertEqual(
            provider.parse("git@github.com:o/r.git").url,
            "git@github.com:o/r.git",
        )

    def test_credentials_in_urls_are_rejected(self) -> None:
        provider = GithubProvider()
        for value in (
            "https://token@github.com/o/r",
            "https://user:pass@github.com/o/r",
        ):
            with self.assertRaises(ProviderError):
                provider.parse(value)
        # An SSH user is not a credential.
        self.assertEqual(
            provider.parse("ssh://git@github.com/o/r.git").slug, "o/r"
        )

    def test_git_provider_clones_a_local_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            source = _make_repo(Path(tmp) / "source")
            provider = GitProvider()
            remote = provider.parse(str(source))
            self.assertEqual(remote.provider, "local")
            destination = Path(tmp) / "clone"
            provider.clone(remote, destination, home)
            self.assertTrue((destination / ".git").exists())
            self.assertEqual(
                (destination / "README.md").read_text(encoding="utf-8"),
                "hello\n",
            )

    def test_github_clone_passes_the_token_in_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            set_secret(home, "github.token", "ghp_test")
            provider = GithubProvider()
            remote = provider.parse("o/r")
            with patch(
                "forgel.providers.github.clone_repository"
            ) as clone:
                provider.clone(remote, home / "clone", home)
            _args, kwargs = clone.call_args
            env = kwargs["env"]
            self.assertEqual(env["GIT_CONFIG_COUNT"], "1")
            self.assertIn("AUTHORIZATION: basic", env["GIT_CONFIG_VALUE_0"])
            self.assertNotIn("ghp_test", remote.url)
            self.assertNotIn("ghp_test", _args[0])

    def test_whitespace_urls_are_rejected(self) -> None:
        with self.assertRaises(ProviderError):
            GithubProvider().parse("https://github.com/o/r repo")


if __name__ == "__main__":
    unittest.main()
