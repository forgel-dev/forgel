from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel import git_ops
from forgel.git_ops import GitOperationError


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


class GitOpsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.remote = self.root / "remote.git"
        _run(self.root, "init", "--bare", "-q", str(self.remote))
        _run(
            self.remote,
            "symbolic-ref",
            "HEAD",
            "refs/heads/main",
        )
        self.repo = self.root / "work"
        _run(self.root, "clone", "-q", str(self.remote), str(self.repo))
        _run(
            self.repo,
            "-c",
            "user.name=T",
            "-c",
            "user.email=t@example.com",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "initial",
        )
        git_ops.push(self.repo, "main")

    def test_branch_commit_push_and_basics(self) -> None:
        self.assertEqual(git_ops.current_branch(self.repo), "main")
        self.assertFalse(git_ops.is_dirty(self.repo))
        self.assertEqual(
            git_ops.origin_url(self.repo), str(self.remote)
        )
        git_ops.fetch(self.repo)
        git_ops.create_branch(self.repo, "feature")
        (self.repo / "file.txt").write_text("hello\n", encoding="utf-8")
        git_ops.commit_all(self.repo, "add file")
        self.assertTrue(git_ops.is_dirty(self.repo) is False)
        self.assertIn("add file", git_ops.last_commit_subject(self.repo))
        self.assertTrue(
            git_ops.is_ancestor(self.repo, "origin/main", "HEAD")
        )
        git_ops.push(self.repo, "feature")
        branches = _run(
            self.remote, "branch", "--list", "feature"
        ).stdout
        self.assertIn("feature", branches)

    def test_existing_branch_is_not_recreated(self) -> None:
        with self.assertRaises(GitOperationError):
            git_ops.create_branch(self.repo, "main")

    def test_remote_mismatch_is_rejected(self) -> None:
        with self.assertRaises(GitOperationError):
            git_ops.ensure_remote(
                self.repo, "https://example.com/other.git"
            )

    def test_secret_files_are_not_committed(self) -> None:
        (self.repo / ".env").write_text("TOKEN=x\n", encoding="utf-8")
        with self.assertRaises(GitOperationError):
            git_ops.commit_all(self.repo, "leak")
        self.assertTrue(git_ops.is_dirty(self.repo))

    def test_auth_env_does_not_contain_the_raw_token(self) -> None:
        env = git_ops.auth_env("super-secret-token")
        assert env is not None
        self.assertNotIn(
            "super-secret-token", env["GIT_CONFIG_VALUE_0"]
        )


if __name__ == "__main__":
    unittest.main()
