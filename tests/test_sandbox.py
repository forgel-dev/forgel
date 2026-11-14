from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from forgel.config import Settings
from forgel.environment import Environment
from forgel.layout import ProjectLayout
from forgel.sandbox import (
    WORKDIR,
    DockerSandbox,
    DockerSession,
    SandboxError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _settings(root: Path, **overrides: object) -> Settings:
    values = {
        "home": root,
        "registry_path": REPO_ROOT / "registry" / "recipes.json",
        "templates_path": REPO_ROOT / "src" / "forgel" / "templates",
        "jurisdiction_path": REPO_ROOT / "jurisdiction",
        "sandbox": "docker",
    }
    values.update(overrides)
    return Settings(**values)


def _result(code: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=code, stdout=stdout, stderr=""
    )


class RecordingSandbox(DockerSandbox):
    """A sandbox that records CLI calls instead of touching a daemon."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings, log=lambda _message: None)
        self.calls: list[list[str]] = []

    def _run(
        self,
        argv: list[str] | tuple[str, ...],
        timeout: float,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = list(argv)
        self.calls.append(command)
        if command and command[0] == "version":
            return _result(0, "27.5.1\n")
        if command and command[0] == "exec":
            target = command[2] if len(command) > 2 else ""
            if target == "slow":
                raise subprocess.TimeoutExpired(cmd="docker exec", timeout=timeout)
            if target == "fail":
                return _result(2, "boom\n")
            return _result(0, "ok\n")
        return _result(0, "")

    def call(self, name: str) -> list[str]:
        for command in reversed(self.calls):
            if command and command[0] == name:
                return command
        raise AssertionError(f"no {name} call: {self.calls}")


class SandboxAvailabilityTest(unittest.TestCase):
    def test_version_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = RecordingSandbox(_settings(Path(tmp)))
            self.assertEqual(sandbox.available(), (True, "27.5.1"))

    def test_unreachable_daemon_is_reported(self) -> None:
        class Broken(RecordingSandbox):
            def _run(self, argv, timeout, input_text=None):  # type: ignore[override]
                return _result(1, "")

        with tempfile.TemporaryDirectory() as tmp:
            available, detail = Broken(_settings(Path(tmp))).available()
        self.assertFalse(available)
        self.assertIn("daemon check failed", detail)


class ImagePolicyTest(unittest.TestCase):
    def test_allowlist_accepts_a_prefix_and_rejects_others(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = RecordingSandbox(
                _settings(Path(tmp), sandbox_images=("python:",))
            )
        self.assertEqual(
            sandbox.check_image("python:3.12-slim"), "python:3.12-slim"
        )
        with self.assertRaises(SandboxError):
            sandbox.check_image("node:20")

    def test_digest_pinning_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = RecordingSandbox(
                _settings(Path(tmp), sandbox_require_digest=True)
            )
        with self.assertRaises(SandboxError):
            sandbox.check_image("python:3.12-slim")
        pinned = "python:3.12-slim@sha256:" + "a" * 64
        self.assertEqual(sandbox.check_image(pinned), pinned)

    def test_an_image_or_build_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sandbox = RecordingSandbox(_settings(Path(tmp)))
            layout = ProjectLayout(root=Path(tmp), kind="legacy")
            with self.assertRaises(SandboxError):
                sandbox.ensure_image(layout, None, "proj")

    def test_build_context_is_passed_to_docker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "env").mkdir()
            (root / "env" / "Dockerfile").write_text("FROM scratch\n")
            sandbox = RecordingSandbox(_settings(root))
            layout = ProjectLayout(root=root, kind="legacy")
            tag = sandbox.ensure_image(
                layout, Environment(build="env"), "proj"
            )
        expected = root.resolve() / "env"
        build = sandbox.call("build")
        self.assertEqual(tag, "forgel-env-proj:latest")
        self.assertIn("-t", build)
        self.assertIn(str(expected / "Dockerfile"), build)
        self.assertEqual(build[-1], str(expected))


class SessionTest(unittest.TestCase):
    def _sandbox(self, root: Path, **overrides: object):
        repo = root / "main"
        repo.mkdir(exist_ok=True)
        layout = ProjectLayout(root=root, kind="legacy")
        sandbox = RecordingSandbox(_settings(root, **overrides))
        return sandbox, layout, repo

    def test_container_is_isolated_and_mounts_only_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, repo = self._sandbox(root)
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ):
                pass
        run = sandbox.call("run")
        self.assertIn("--network", run)
        self.assertEqual(run[run.index("--network") + 1], "none")
        self.assertEqual(run[run.index("--cpus") + 1], "2")
        self.assertEqual(run[run.index("--memory") + 1], "2g")
        self.assertEqual(run[run.index("--pids-limit") + 1], "512")
        self.assertIn("--cap-drop", run)
        self.assertEqual(run[run.index("--cap-drop") + 1], "ALL")
        self.assertIn("no-new-privileges", run)
        self.assertIn("--read-only", run)
        self.assertEqual(
            run[run.index("--user") + 1],
            f"{os.getuid()}:{os.getgid()}",
        )
        self.assertEqual(
            run[run.index("-v") + 1], f"{repo.resolve()}:{WORKDIR}:rw"
        )
        self.assertIn("forgel.kind=sandbox", run)
        joined = " ".join(run)
        self.assertNotIn("docker.sock", joined)
        self.assertNotIn("/data", joined)
        self.assertIn("--entrypoint", run)
        self.assertEqual(run[-3:], ["sleep", "python:3.12-slim", "infinity"])

    def test_setup_runs_before_the_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            environment = Environment(
                image="python:3.12-slim",
                setup=("python -m pip install x",),
                test=("python -m unittest",),
            )
            with sandbox.session(layout, environment, "proj", "main") as session:
                code, output = session.run(["python", "-m", "unittest"])
        self.assertEqual((code, output), (0, "ok\n"))
        execs = [call for call in sandbox.calls if call[0] == "exec"]
        self.assertEqual(len(execs), 2)
        self.assertEqual(execs[0][2], sys.executable)
        self.assertEqual(execs[0][3:], ["-m", "pip", "install", "x"])
        self.assertEqual(execs[1][2:], ["python", "-m", "unittest"])

    def test_a_failing_command_returns_its_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ) as session:
                self.assertEqual(session.run(["fail"]), (2, "boom\n"))

    def test_a_failing_setup_stops_the_container(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            environment = Environment(
                image="python:3.12-slim", setup=("fail",)
            )
            with self.assertRaises(SandboxError):
                with sandbox.session(
                    layout, environment, "proj", "main"
                ):
                    pass
        sandbox.call("stop")

    def test_a_timeout_stops_the_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ) as session:
                code, output = session.run(["slow"], timeout=5)
                self.assertEqual(code, 124)
                self.assertIn("timed out", output)
                with self.assertRaises(SandboxError):
                    session.run(["python", "-V"])
        sandbox.call("stop")

    def test_the_container_is_stopped_on_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ):
                pass
        stop = sandbox.call("stop")
        self.assertIn("--rm", sandbox.call("run"))
        self.assertEqual(stop[0], "stop")

    def test_the_sandbox_requires_one_repository(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with self.assertRaises(SandboxError):
                sandbox.session(
                    layout, Environment(image="python:3.12-slim"), "proj", ""
                )

    def test_contract_env_is_passed_to_the_container(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with sandbox.session(
                layout,
                Environment(
                    image="python:3.12-slim",
                    env=(("PYTHONPATH", "src"),),
                ),
                "proj",
                "main",
            ):
                pass
        run = sandbox.call("run")
        self.assertIn("PYTHONPATH=src", run)
        self.assertEqual(run[run.index("PYTHONPATH=src") - 1], "-e")

    def test_sibling_repositories_are_mounted_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            (root / "web").mkdir()
            with sandbox.session(
                layout,
                Environment(image="python:3.12-slim", mounts=("web",)),
                "proj",
                "main",
            ):
                pass
        run = sandbox.call("run")
        self.assertIn(
            f"{root.resolve() / 'web'}:/web:ro", run
        )

    def test_an_unknown_sibling_mount_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(root)
            with self.assertRaises(SandboxError):
                sandbox.session(
                    layout,
                    Environment(image="python:3.12-slim", mounts=("web",)),
                    "proj",
                    "main",
                )

    def test_network_may_be_enabled_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(
                root, sandbox_network="bridge"
            )
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ):
                pass
        run = sandbox.call("run")
        self.assertEqual(run[run.index("--network") + 1], "bridge")

    def test_read_only_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox, layout, _repo = self._sandbox(
                root, sandbox_read_only=False
            )
            with sandbox.session(
                layout, Environment(image="python:3.12-slim"), "proj", "main"
            ):
                pass
        self.assertNotIn("--read-only", sandbox.call("run"))

    def test_container_names_are_stable_and_labelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox = RecordingSandbox(_settings(root))
            session = DockerSession(
                sandbox=sandbox,
                project_id="Proj_One",
                image="python:3.12-slim",
                mount="/repo",
                name="forgel-sbx-proj-one-abc123",
            )
            self.assertTrue(session.name.startswith("forgel-sbx-"))
            self.assertIn("forgel.project=Proj_One", session._run_argv())


class DaemonPathTest(unittest.TestCase):
    def test_projects_root_maps_the_daemon_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "projects" / "p1" / "repos" / "main"
            repo.mkdir(parents=True)
            sandbox = RecordingSandbox(
                _settings(
                    root, sandbox_projects_root="/sandbox-data/projects"
                )
            )
            self.assertEqual(
                sandbox.daemon_path(repo),
                "/sandbox-data/projects/p1/repos/main",
            )

    def test_a_path_outside_projects_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / "elsewhere"
            outside.mkdir()
            sandbox = RecordingSandbox(
                _settings(
                    root, sandbox_projects_root="/sandbox-data/projects"
                )
            )
            with self.assertRaises(SandboxError):
                sandbox.daemon_path(outside)


if __name__ == "__main__":
    unittest.main()
