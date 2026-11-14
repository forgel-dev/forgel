from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.deploy import (
    DeployConfig,
    DeployError,
    RemoteEnv,
    Runner,
    deploy_backup,
    deploy_init,
    deploy_up,
)


class FakeRunner(Runner):
    def __init__(self, binary_output: bytes = b"backup") -> None:
        self.ssh_calls: list[dict] = []
        self.local_calls: list[dict] = []
        self.uploads: list[dict] = []
        self.binary_output = binary_output

    def ssh(
        self,
        command: str,
        input_data=None,
        binary: bool = False,
        stream: bool = False,
        allow_fail: bool = False,
        timeout: float = 300.0,
    ) -> subprocess.CompletedProcess:
        self.ssh_calls.append(
            {
                "command": command,
                "input": input_data,
                "binary": binary,
            }
        )
        stdout = self.binary_output if binary else "ok\n"
        return subprocess.CompletedProcess(["ssh"], 0, stdout, "")

    def local(
        self,
        command: list[str],
        input_data=None,
        env=None,
        timeout: float = 1800.0,
    ) -> subprocess.CompletedProcess[str]:
        self.local_calls.append({"command": command, "env": env})
        return subprocess.CompletedProcess(command, 0, "", "")

    def upload(self, files, directory: str) -> None:
        self.uploads.append({"files": files, "directory": directory})


class ScriptedRunner(Runner):
    """Remote shell double for the environment preflight."""

    def __init__(
        self,
        root: bool = False,
        sudo: bool = False,
        docker: bool = False,
        compose: bool = False,
        direct_docker: bool = True,
        os_id: str = "ubuntu",
        curl: bool = True,
    ) -> None:
        self.state = {
            "root": root,
            "sudo": sudo,
            "docker": docker,
            "compose": compose,
            "direct_docker": direct_docker,
            "daemon": False,
            "os": os_id,
            "curl": curl,
        }
        self.commands: list[str] = []
        self.config = DeployConfig(host="h", user="u")
        self.log = lambda _m: None
        self.env = RemoteEnv()

    def ssh(
        self,
        command: str,
        input_data=None,
        binary: bool = False,
        stream: bool = False,
        allow_fail: bool = False,
        timeout: float = 300.0,
    ) -> subprocess.CompletedProcess:
        self.commands.append(command)
        code, output = self._respond(command)
        return subprocess.CompletedProcess(["ssh"], code, output, "")

    def _respond(self, command: str) -> tuple[int, str]:
        state = self.state
        if command == "true":
            return 0, ""
        if command == "id -u":
            return 0, "0" if state["root"] else "1000"
        if command == "sudo -n true":
            return (0, "") if state["sudo"] else (1, "")
        if "etc/os-release" in command:
            return 0, "ID=" + state["os"] + "\n"
        if command.startswith("command -v "):
            name = command.split()[-1]
            if name == "docker":
                present = state["docker"]
            elif name in {"curl", "wget"}:
                present = state["curl"]
            elif name in {"systemctl", "service", "apt-get", "dnf", "apk"}:
                present = True
            else:
                present = False
            return (0, "/usr/bin/" + name) if present else (1, "")
        if command == "docker info":
            return (
                (0, "")
                if state["docker"] and state["daemon"] and state["direct_docker"]
                else (1, "")
            )
        if command == "sudo -n docker info":
            return (
                (0, "")
                if state["docker"] and state["daemon"] and state["sudo"]
                else (1, "")
            )
        if command in {"docker compose version", "docker-compose version",
                       "sudo -n docker compose version"}:
            return (0, "") if state["compose"] else (1, "")
        if any(
            marker in command
            for marker in (
                "get.docker.com",
                "apt-get",
                "dnf ",
                "apk ",
                "docker-compose",
            )
        ):
            state["docker"] = True
            state["compose"] = True
            state["daemon"] = True
            return 0, ""
        if "systemctl" in command or "service docker start" in command:
            state["daemon"] = True
            return 0, ""
        return 0, ""


class EnvironmentTest(unittest.TestCase):
    def test_installs_docker_with_consent(self) -> None:
        runner = ScriptedRunner(root=True, docker=False, compose=False)
        runner.ensure(assume_yes=True, interactive=False)
        self.assertTrue(
            any("get.docker.com" in item for item in runner.commands)
        )
        self.assertEqual(runner.env.docker, ("docker",))
        self.assertEqual(runner.env.compose, ("docker", "compose"))
        self.assertEqual(runner.state["docker"], True)

    def test_refuses_without_privileges(self) -> None:
        runner = ScriptedRunner(root=False, sudo=False, docker=False)
        with self.assertRaises(DeployError) as raised:
            runner.ensure(assume_yes=True, interactive=False)
        self.assertIn("root or passwordless sudo", str(raised.exception))
        self.assertFalse(
            any("get.docker.com" in item for item in runner.commands)
        )

    def test_requires_consent_without_a_tty(self) -> None:
        runner = ScriptedRunner(root=True, docker=False, compose=False)
        with self.assertRaises(DeployError) as raised:
            runner.ensure(assume_yes=False, interactive=False)
        self.assertIn("--yes", str(raised.exception))
        self.assertFalse(
            any("get.docker.com" in item for item in runner.commands)
        )

    def test_uses_sudo_for_docker_access(self) -> None:
        runner = ScriptedRunner(
            root=False,
            sudo=True,
            docker=True,
            compose=True,
            direct_docker=False,
        )
        runner.state["daemon"] = True
        runner.ensure(allow_install=False)
        self.assertEqual(runner.env.docker, ("sudo", "-n", "docker"))
        self.assertEqual(
            runner.env.compose, ("sudo", "-n", "docker", "compose")
        )

    def test_installs_compose_only(self) -> None:
        runner = ScriptedRunner(root=True, docker=True, compose=False)
        runner.state["daemon"] = True
        runner.ensure(assume_yes=True, interactive=False)
        self.assertTrue(
            any("docker-compose" in item for item in runner.commands)
        )
        self.assertEqual(runner.env.compose, ("docker", "compose"))


class DeployConfigTest(unittest.TestCase):
    def test_parse_filters_deploy_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deploy"
            path.write_text(
                "# comment\n"
                "export DEPLOY_HOST=example.com\n"
                "DEPLOY_USER=root\n"
                "DEPLOY_PORT=2200\n"
                "DEPLOY_BUILD=remote\n"
                "DEPLOY_DIR=/srv/forgel\n"
                'TELEGRAM_BOT_TOKEN="secret"\n'
                "FORGEL_MODEL_NAME=deepseek-chat\n",
                encoding="utf-8",
            )
            config = DeployConfig.from_file(path)
            self.assertEqual(config.host, "example.com")
            self.assertEqual(config.user, "root")
            self.assertEqual(config.port, 2200)
            self.assertEqual(config.build, "remote")
            self.assertEqual(
                config.env,
                {
                    "TELEGRAM_BOT_TOKEN": "secret",
                    "FORGEL_MODEL_NAME": "deepseek-chat",
                },
            )

    def test_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.deploy"
            path.write_text("DEPLOY_USER=root\n", encoding="utf-8")
            with self.assertRaises(DeployError):
                DeployConfig.from_file(path)
            path.write_text(
                "DEPLOY_HOST=h\nDEPLOY_USER=u\nDEPLOY_BUILD=magic\n",
                encoding="utf-8",
            )
            with self.assertRaises(DeployError):
                DeployConfig.from_file(path)
            path.write_text(
                "DEPLOY_HOST=h\nDEPLOY_USER=u\nDEPLOY_DIR=relative\n",
                encoding="utf-8",
            )
            with self.assertRaises(DeployError):
                DeployConfig.from_file(path)


class DeployFlowTest(unittest.TestCase):
    def test_remote_build_uploads_context_and_starts(self) -> None:
        config = DeployConfig(
            host="h",
            user="u",
            directory="/srv/forgel",
            image="forgel:test",
            build="remote",
            env={"TELEGRAM_BOT_TOKEN": "secret"},
        )
        runner = FakeRunner()
        deploy_up(config, runner=runner, log=lambda _m: None)
        self.assertEqual(len(runner.uploads), 1)
        files = runner.uploads[0]["files"]
        self.assertIn("compose.yaml", files)
        self.assertIn(".env", files)
        self.assertIn("context/Dockerfile", files)
        env_text = files[".env"][0].decode("utf-8")
        self.assertIn('TELEGRAM_BOT_TOKEN="secret"', env_text)
        self.assertIn('FORGEL_IMAGE="forgel:test"', env_text)
        self.assertNotIn("DEPLOY_", env_text)
        commands = "\n".join(item["command"] for item in runner.ssh_calls)
        self.assertIn("docker build -t forgel:test context", commands)
        self.assertIn("docker compose up -d", commands)
        self.assertIn("forgel doctor", commands)
        self.assertEqual(runner.local_calls, [])

    def test_local_build_pushes_and_pulls(self) -> None:
        config = DeployConfig(
            host="h",
            user="u",
            image="ghcr.io/owner/app:1",
            build="local",
            push=True,
            registry_user="owner",
            registry_token="token",
            env={"TELEGRAM_BOT_TOKEN": "secret"},
        )
        runner = FakeRunner()
        deploy_up(config, runner=runner, log=lambda _m: None)
        local_commands = [
            " ".join(item["command"]) for item in runner.local_calls
        ]
        self.assertTrue(
            any("docker login ghcr.io" in item for item in local_commands)
        )
        self.assertTrue(any("docker build" in item for item in local_commands))
        self.assertTrue(any("docker push" in item for item in local_commands))
        logins = [
            item
            for item in runner.ssh_calls
            if "docker login" in item["command"]
        ]
        self.assertEqual(logins[0]["input"], "token")
        commands = "\n".join(item["command"] for item in runner.ssh_calls)
        self.assertIn("docker compose pull", commands)

    def test_local_build_requires_push(self) -> None:
        config = DeployConfig(
            host="h", user="u", build="local", push=False
        )
        with self.assertRaises(DeployError):
            deploy_up(config, runner=FakeRunner(), log=lambda _m: None)

    def test_init_and_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".env.deploy"
            path = deploy_init(target)
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn("DEPLOY_HOST", path.read_text(encoding="utf-8"))
            with self.assertRaises(DeployError):
                deploy_init(target)

            output = Path(tmp) / "backup.tgz"
            config = DeployConfig(host="h", user="u")
            deploy_backup(
                config,
                output,
                runner=FakeRunner(binary_output=b"archive"),
                log=lambda _m: None,
            )
            self.assertEqual(output.read_bytes(), b"archive")
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
