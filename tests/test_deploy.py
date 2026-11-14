from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from forgel.deploy import (
    DeployConfig,
    DeployError,
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
