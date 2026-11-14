"""One-command deployment of the Forgel daemon to a remote host.

The operator edits one local file, ``.env.deploy``, and runs
``forgel deploy up``. The utility talks to the server over SSH: it builds or
pushes the image, uploads the production Compose file and a filtered runtime
``.env`` (mode 0600), starts the service and runs the doctor.

Two image strategies:

* ``local`` + ``push`` — build locally, push to a registry (GHCR recommended),
  pull on the server;
* ``remote`` — send the build context and build on the server (no registry).

Secrets never appear in argv or logs. Registry tokens are passed on stdin, and
the remote environment file is written through an SSH tar stream.
"""

from __future__ import annotations

import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "deploy" / "compose.yaml"
EXAMPLE_PATH = ROOT / ".env.deploy.example"
DEFAULT_DIRECTORY = "/srv/forgel"
RUNTIME_PREFIX = "DEPLOY_"
VALID_BUILD_MODES = {"auto", "local", "remote"}


class DeployError(RuntimeError):
    """The deployment cannot continue safely."""


def _parse_env_file(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, separator, value = line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DeployConfig:
    host: str
    user: str = ""
    port: int | None = None
    ssh_key: str = ""
    directory: str = DEFAULT_DIRECTORY
    image: str = ""
    build: str = "auto"
    push: bool = False
    registry_user: str = ""
    registry_token: str = ""
    app_key_file: str = ""
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> DeployConfig:
        path = Path(path)
        if not path.exists():
            raise DeployError(
                f"{path} does not exist; create it with `forgel deploy init`"
            )
        values = _parse_env_file(path.read_text(encoding="utf-8"))
        host = values.get("DEPLOY_HOST", "").strip()
        if not host:
            raise DeployError("DEPLOY_HOST is required")
        user = values.get("DEPLOY_USER", "").strip()
        raw_port = values.get("DEPLOY_PORT", "").strip()
        port: int | None = None
        if raw_port:
            try:
                port = int(raw_port)
            except ValueError as exc:
                raise DeployError("DEPLOY_PORT must be an integer") from exc
        build = values.get("DEPLOY_BUILD", "auto").strip().lower()
        if build not in VALID_BUILD_MODES:
            raise DeployError(
                f"DEPLOY_BUILD must be one of {sorted(VALID_BUILD_MODES)}"
            )
        directory = values.get("DEPLOY_DIR", DEFAULT_DIRECTORY).strip()
        if not directory.startswith("/"):
            raise DeployError("DEPLOY_DIR must be an absolute remote path")
        env: dict[str, str] = {}
        for key, value in values.items():
            if key.startswith(RUNTIME_PREFIX):
                continue
            if not key.replace("_", "").isalnum() or key[0].isdigit():
                raise DeployError(f"invalid environment key: {key!r}")
            env[key] = value
        return cls(
            host=host,
            user=user,
            port=port,
            ssh_key=values.get("DEPLOY_SSH_KEY", "").strip(),
            directory=directory,
            image=values.get("DEPLOY_IMAGE", "").strip(),
            build=build,
            push=_as_bool(values.get("DEPLOY_PUSH", "false")),
            registry_user=values.get("DEPLOY_REGISTRY_USER", "").strip(),
            registry_token=values.get("DEPLOY_REGISTRY_TOKEN", "").strip(),
            app_key_file=values.get("DEPLOY_APP_KEY_FILE", "").strip(),
            env=env,
        )

    @property
    def target(self) -> str:
        return f"{self.user}@{self.host}" if self.user else self.host


@dataclass(frozen=True)
class RemoteEnv:
    docker: tuple[str, ...] = ("docker",)
    compose: tuple[str, ...] = ("docker", "compose")
    root: bool = False
    sudo: bool = False
    os_id: str = ""
    daemon: bool = False
    remote_user: str = ""

    @property
    def privilege(self) -> tuple[str, ...]:
        return () if self.root else (("sudo", "-n") if self.sudo else ())


def _manual_instructions(
    os_id: str, can_install: bool, user: str
) -> str:
    lines = [
        "Install Docker Engine and Docker Compose v2 on the server, then "
        "rerun `forgel deploy up`.",
    ]
    if os_id in {"ubuntu", "debian"}:
        lines.append(
            "  sudo apt-get update && sudo apt-get install -y docker.io "
            "docker-compose-v2"
        )
    elif os_id in {"fedora", "rhel", "centos", "rocky", "almalinux"}:
        lines.append(
            "  sudo dnf install -y docker docker-compose-plugin"
        )
    elif os_id == "alpine":
        lines.append("  sudo apk add docker docker-cli-compose")
    else:
        lines.append("  use your distribution's Docker package")
    lines.append("  sudo systemctl enable --now docker")
    who = f" {user!r}" if user else ""
    if not can_install:
        lines.append(
            f"The SSH user{who} has no root or passwordless sudo; ask "
            "the server administrator to install Docker, or grant that user "
            "passwordless sudo / docker-group access."
        )
    return "\n".join(lines)


class Runner:
    """SSH and local command runner. Injectable for tests."""

    def __init__(
        self,
        config: DeployConfig,
        log: Callable[[str], None] = print,
    ) -> None:
        self.config = config
        self.log = log
        self.env = RemoteEnv()

    def _ssh_args(self) -> list[str]:
        args = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
        ]
        if self.config.port is not None:
            args.extend(["-p", str(self.config.port)])
        if self.config.ssh_key:
            args.extend(["-i", os.path.expanduser(self.config.ssh_key)])
        args.append(self.config.target)
        return args

    def ssh(
        self,
        command: str,
        input_data: str | bytes | None = None,
        binary: bool = False,
        stream: bool = False,
        allow_fail: bool = False,
        timeout: float = 300.0,
    ) -> subprocess.CompletedProcess:
        self.log(f"ssh {self.config.target}: {command}")
        try:
            completed = subprocess.run(
                self._ssh_args() + [command],
                input=input_data,
                capture_output=not stream,
                text=not binary,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeployError(f"ssh failed: {exc}") from exc
        if not allow_fail and completed.returncode != 0:
            detail = ""
            if completed.stderr:
                detail = (
                    completed.stderr
                    if isinstance(completed.stderr, str)
                    else completed.stderr.decode("utf-8", "replace")
                )
            raise DeployError(
                f"remote command failed ({completed.returncode}): "
                f"{command}\n{detail.strip()}"
            )
        return completed

    def local(
        self,
        command: list[str],
        input_data: str | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float = 1800.0,
    ) -> subprocess.CompletedProcess[str]:
        self.log("local: " + " ".join(shlex.quote(item) for item in command))
        try:
            completed = subprocess.run(
                command,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **dict(env or {})},
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DeployError(f"local command failed: {exc}") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise DeployError(
                f"local command failed ({completed.returncode}): "
                f"{' '.join(command)}\n{detail}"
            )
        return completed

    def upload(
        self, files: dict[str, tuple[bytes, int]], directory: str
    ) -> None:
        buffer = io.BytesIO()
        now = int(datetime.now(timezone.utc).timestamp())
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name, (content, mode) in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = mode
                info.mtime = now
                archive.addfile(info, io.BytesIO(content))
        command = (
            f"umask 077; mkdir -p {shlex.quote(directory)}; "
            f"tar -xzf - -C {shlex.quote(directory)}"
        )
        self.ssh(command, input_data=buffer.getvalue(), binary=True)

    # -------------------------------------------------------- environment

    def docker_command(self, *args: str) -> str:
        return shlex.join(list(self.env.docker) + list(args))

    def compose_command(self, *args: str) -> str:
        return shlex.join(list(self.env.compose) + list(args))

    def _probe(
        self, command: str, timeout: float = 30.0
    ) -> tuple[int, str]:
        result = self.ssh(command, allow_fail=True, timeout=timeout)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        return result.returncode, stdout + stderr

    def _command_exists(self, name: str) -> bool:
        return self._probe(f"command -v {shlex.quote(name)}")[0] == 0

    @staticmethod
    def _compose_v1_prefix(
        docker_prefix: tuple[str, ...],
    ) -> tuple[str, ...]:
        if docker_prefix[:2] == ("sudo", "-n"):
            return ("sudo", "-n", "docker-compose")
        return ("docker-compose",)

    def _daemon_ok(self, prefix: tuple[str, ...]) -> bool:
        return self._probe(
            shlex.join(list(prefix) + ["info"]), timeout=60
        )[0] == 0

    def _compose_ok(self, prefix: tuple[str, ...]) -> bool:
        return self._probe(
            shlex.join(list(prefix) + ["version"])
        )[0] == 0

    def ensure(
        self,
        allow_install: bool = True,
        assume_yes: bool = False,
        interactive: bool | None = None,
    ) -> None:
        """Check SSH, Docker and Compose; offer an installation if missing."""

        self.ssh("true", timeout=30)
        root = self._probe("id -u")[1].strip() == "0"
        sudo = self._probe("sudo -n true")[0] == 0
        remote_user = self._probe("whoami")[1].strip()
        os_id = ""
        release_rc, release = self._probe("cat /etc/os-release")
        if release_rc == 0:
            for line in release.splitlines():
                if line.startswith("ID="):
                    os_id = line.split("=", 1)[1].strip().strip('"')
        can_install = root or sudo
        self.env = RemoteEnv(
            root=root,
            sudo=sudo,
            os_id=os_id,
            remote_user=remote_user,
        )
        manual = _manual_instructions(os_id, can_install, self.config.user)

        if not self._command_exists("docker"):
            self.log(
                f"warning: Docker is not installed on {self.config.target} "
                f"({os_id or 'unknown OS'})"
            )
            self._offer_install(
                "Docker and Docker Compose",
                allow_install,
                assume_yes,
                interactive,
                can_install,
                manual,
                need_docker=True,
                os_id=os_id,
            )
            if not self._command_exists("docker"):
                raise DeployError(
                    "Docker is still not available after installation\n"
                    + manual
                )

        prefix: tuple[str, ...] = ("docker",)
        if not self._daemon_ok(prefix):
            privileged = tuple(self.env.privilege) + ("docker",)
            if sudo and not root and self._daemon_ok(privileged):
                prefix = privileged
            else:
                self._start_daemon()
                if root and self._daemon_ok(("docker",)):
                    prefix = ("docker",)
                elif sudo and self._daemon_ok(privileged):
                    prefix = privileged
                else:
                    raise DeployError(
                        "Docker is installed but the SSH user cannot access "
                        "the daemon\n" + manual
                    )

        compose = prefix + ("compose",)
        if not self._compose_ok(compose):
            compose = self._compose_v1_prefix(prefix)
            if not self._compose_ok(compose):
                self.log(
                    f"warning: Docker Compose is not installed on "
                    f"{self.config.target}"
                )
                self._offer_install(
                    "Docker Compose",
                    allow_install,
                    assume_yes,
                    interactive,
                    can_install,
                    manual,
                    need_docker=False,
                    os_id=os_id,
                )
                compose = prefix + ("compose",)
                if not self._compose_ok(compose):
                    compose = self._compose_v1_prefix(prefix)
                    if not self._compose_ok(compose):
                        raise DeployError(
                            "Docker Compose is still not available\n"
                            + manual
                        )
        self.env = RemoteEnv(
            docker=prefix,
            compose=compose,
            root=root,
            sudo=sudo,
            os_id=os_id,
            daemon=True,
            remote_user=remote_user,
        )

    def _offer_install(
        self,
        label: str,
        allow_install: bool,
        assume_yes: bool,
        interactive: bool | None,
        can_install: bool,
        manual: str,
        need_docker: bool,
        os_id: str,
    ) -> None:
        if not can_install:
            raise DeployError(
                f"{label} is missing and the SSH user has no root or "
                "passwordless sudo\n" + manual
            )
        if not allow_install:
            raise DeployError(
                f"{label} is missing and --no-install was given\n" + manual
            )
        if not assume_yes:
            if interactive is None:
                interactive = sys.stdin.isatty()
            if not interactive:
                raise DeployError(
                    f"{label} is missing; rerun with --yes to allow the "
                    "installer, or install it manually\n" + manual
                )
            answer = input(
                f"Install {label} on {self.config.target}? [y/N] "
            )
            if answer.strip().lower() not in {"y", "yes"}:
                raise DeployError(
                    f"installation of {label} was declined\n" + manual
                )
        self.log(f"installing {label} on {self.config.target}")
        self._install(need_docker=need_docker, os_id=os_id)
        self._start_daemon()
        self.log("installer finished")

    def _install(self, need_docker: bool, os_id: str) -> None:
        privilege = "" if self.env.root else "sudo -n "
        if need_docker and self._command_exists("curl"):
            script = (
                "curl -fsSL https://get.docker.com "
                "-o /tmp/forgel-get-docker.sh && "
                "sh /tmp/forgel-get-docker.sh"
            )
        elif need_docker and self._command_exists("wget"):
            script = (
                "wget -qO /tmp/forgel-get-docker.sh "
                "https://get.docker.com && sh /tmp/forgel-get-docker.sh"
            )
        else:
            script = self._package_install(need_docker)
        self.ssh(
            privilege + "sh -c " + shlex.quote(script),
            timeout=1800,
        )

    def _package_install(self, need_docker: bool) -> str:
        if self._command_exists("apt-get"):
            packages = "docker.io docker-compose-v2"
            fallback = "docker.io docker-compose"
            if not need_docker:
                packages = "docker-compose-v2"
                fallback = "docker-compose"
            return (
                "apt-get update && DEBIAN_FRONTEND=noninteractive "
                f"apt-get install -y {packages} || "
                "DEBIAN_FRONTEND=noninteractive "
                f"apt-get install -y {fallback}"
            )
        for manager in ("dnf", "yum"):
            if self._command_exists(manager):
                packages = "docker docker-compose-plugin"
                fallback = "docker docker-compose"
                if not need_docker:
                    packages = "docker-compose-plugin"
                    fallback = "docker-compose"
                return (
                    f"{manager} install -y {packages} || "
                    f"{manager} install -y {fallback}"
                )
        if self._command_exists("apk"):
            packages = "docker docker-cli-compose"
            if not need_docker:
                packages = "docker-cli-compose"
            return f"apk add --no-cache {packages}"
        if self._command_exists("zypper"):
            packages = "docker docker-compose"
            if not need_docker:
                packages = "docker-compose"
            return f"zypper --non-interactive install {packages}"
        raise DeployError(
            "no supported package manager found; install Docker manually"
        )

    def _start_daemon(self) -> None:
        privilege = list(self.env.privilege)
        remote_user = self.env.remote_user or self.config.user
        if not self.env.root and self.env.sudo and remote_user:
            self.ssh(
                shlex.join(
                    privilege + ["usermod", "-aG", "docker", remote_user]
                ),
                allow_fail=True,
                timeout=60,
            )
        if self._command_exists("systemctl"):
            result = self.ssh(
                shlex.join(
                    privilege + ["systemctl", "enable", "--now", "docker"]
                ),
                allow_fail=True,
                timeout=120,
            )
            if result.returncode == 0:
                return
        if self._command_exists("service"):
            result = self.ssh(
                shlex.join(privilege + ["service", "docker", "start"]),
                allow_fail=True,
                timeout=120,
            )
            if result.returncode == 0:
                return
        if self.env.os_id == "alpine":
            self.ssh(
                shlex.join(
                    privilege + ["rc-update", "add", "docker", "default"]
                ),
                allow_fail=True,
                timeout=60,
            )
            self.ssh(
                shlex.join(privilege + ["service", "docker", "start"]),
                allow_fail=True,
                timeout=120,
            )


def _resolve_image(config: DeployConfig) -> tuple[str, str]:
    image = config.image or (
        "forgel:" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )
    mode = config.build
    if mode == "auto":
        mode = "local" if config.push else "remote"
    if mode == "local" and not config.push:
        raise DeployError(
            "DEPLOY_BUILD=local needs DEPLOY_PUSH=true; use remote build "
            "otherwise"
        )
    return image, mode


def _registry(image: str) -> str:
    first = image.split("/", 1)[0]
    if "." in first or ":" in first or first == "localhost":
        return first
    return "docker.io"


def _runtime_env(config: DeployConfig, image: str) -> dict[str, str]:
    env = dict(config.env)
    env["FORGEL_IMAGE"] = image
    env.setdefault("COMPOSE_PROJECT_NAME", "forgel")
    if config.app_key_file:
        env["FORGEL_GITHUB_APP_PRIVATE_KEY_PATH"] = (
            "/run/secrets/forge-github-app.pem"
        )
    return env


def _env_bytes(env: Mapping[str, str]) -> bytes:
    lines = [f"{key}={json.dumps(value)}" for key, value in env.items()]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _compose_files(
    config: DeployConfig, image: str
) -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {
        "compose.yaml": (COMPOSE_PATH.read_bytes(), 0o644),
        ".env": (_env_bytes(_runtime_env(config, image)), 0o600),
    }
    if config.app_key_file:
        key_path = Path(config.app_key_file).expanduser()
        if not key_path.exists():
            raise DeployError(f"app key file not found: {key_path}")
        files["secrets/forge-github-app.pem"] = (
            key_path.read_bytes(),
            0o600,
        )
    return files


def _context_files() -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {}
    for name in (
        "Dockerfile",
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "deploy/entrypoint.sh",
    ):
        path = ROOT / name
        if not path.exists():
            raise DeployError(f"build context file missing: {path}")
        files[f"context/{name}"] = (path.read_bytes(), 0o644)
    for directory in ("src", "registry", "jurisdiction"):
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file():
                continue
            if any(
                part in {"__pycache__", ".git"} for part in path.parts
            ):
                continue
            if path.suffix == ".pyc":
                continue
            files[f"context/{path.relative_to(ROOT).as_posix()}"] = (
                path.read_bytes(),
                0o644,
            )
    return files


def _use_runner(
    config: DeployConfig,
    runner: Runner | None,
    log: Callable[[str], None],
) -> Runner:
    if runner is None:
        return Runner(config, log=log)
    runner.config = config
    runner.log = log
    return runner


def deploy_up(
    config: DeployConfig,
    runner: Runner | None = None,
    log: Callable[[str], None] = print,
    assume_yes: bool = False,
    allow_install: bool = True,
    interactive: bool | None = None,
) -> None:
    runner = _use_runner(config, runner, log)
    log(f"target: {config.target}:{config.directory}")
    runner.ensure(
        allow_install=allow_install,
        assume_yes=assume_yes,
        interactive=interactive,
    )

    image, mode = _resolve_image(config)
    log(f"image: {image} ({mode} build)")

    if mode == "local":
        docker_config: str | None = None
        env: dict[str, str] = {}
        if config.registry_token:
            if not config.registry_user:
                raise DeployError(
                    "DEPLOY_REGISTRY_USER is required with "
                    "DEPLOY_REGISTRY_TOKEN"
                )
            docker_config = tempfile.mkdtemp(prefix="forgel-docker-")
            env = {"DOCKER_CONFIG": docker_config}
        try:
            if config.registry_token and docker_config is not None:
                runner.local(
                    [
                        "docker",
                        "login",
                        _registry(image),
                        "-u",
                        config.registry_user,
                        "--password-stdin",
                    ],
                    input_data=config.registry_token,
                    env=env,
                )
            runner.local(["docker", "build", "-t", image, str(ROOT)], env=env)
            runner.local(["docker", "push", image], env=env)
        finally:
            if docker_config is not None:
                shutil.rmtree(docker_config, ignore_errors=True)

    files = _compose_files(config, image)
    if mode == "remote":
        files.update(_context_files())
    runner.upload(files, config.directory)

    if mode == "remote":
        runner.ssh(
            f"cd {shlex.quote(config.directory)} && "
            + runner.docker_command("build", "-t", image, "context"),
            timeout=3600,
        )
    elif config.registry_token:
        runner.ssh(
            runner.docker_command(
                "login",
                _registry(image),
                "-u",
                config.registry_user,
                "--password-stdin",
            ),
            input_data=config.registry_token,
            timeout=60,
        )
        runner.ssh(
            f"cd {shlex.quote(config.directory)} && "
            + runner.compose_command("pull", "--quiet"),
            timeout=600,
        )

    runner.ssh(
        f"cd {shlex.quote(config.directory)} && chmod 700 . && "
        "chmod 600 .env && " + runner.compose_command("up", "-d", "--remove-orphans"),
        timeout=900,
    )
    status = runner.ssh(
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command("ps")
    )
    if status.stdout:
        log(status.stdout.strip())
    doctor = runner.ssh(
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command(
            "exec",
            "-T",
            "--user",
            "10001:10001",
            "forgel",
            "forgel",
            "doctor",
        ),
        allow_fail=True,
        timeout=120,
    )
    if doctor.stdout:
        log(doctor.stdout.strip())
    log("deploy: up")


def deploy_status(
    config: DeployConfig,
    runner: Runner | None = None,
    log: Callable[[str], None] = print,
) -> None:
    runner = _use_runner(config, runner, log)
    runner.ensure(allow_install=False, assume_yes=True)
    completed = runner.ssh(
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command("ps")
    )
    print(completed.stdout.rstrip() if completed.stdout else "")


def deploy_logs(
    config: DeployConfig,
    follow: bool = False,
    runner: Runner | None = None,
    log: Callable[[str], None] = print,
) -> None:
    runner = _use_runner(config, runner, log)
    runner.ensure(allow_install=False, assume_yes=True)
    args = ["logs", "--tail=200"]
    if follow:
        args.append("-f")
    args.append("forgel")
    command = (
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command(*args)
    )
    completed = runner.ssh(command, stream=follow, timeout=3600)
    if not follow and completed.stdout:
        print(completed.stdout.rstrip())


def deploy_restart(
    config: DeployConfig,
    runner: Runner | None = None,
    log: Callable[[str], None] = print,
) -> None:
    runner = _use_runner(config, runner, log)
    runner.ensure(allow_install=False, assume_yes=True)
    completed = runner.ssh(
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command("restart", "forgel")
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    log("deploy: restarted")


def deploy_backup(
    config: DeployConfig,
    output: Path,
    runner: Runner | None = None,
    log: Callable[[str], None] = print,
) -> Path:
    runner = _use_runner(config, runner, log)
    runner.ensure(allow_install=False, assume_yes=True)
    completed = runner.ssh(
        f"cd {shlex.quote(config.directory)} && "
        + runner.compose_command(
            "exec",
            "-T",
            "--user",
            "10001:10001",
            "forgel",
            "tar",
            "czf",
            "-",
            "-C",
            "/data",
            ".",
        ),
        binary=True,
        timeout=900,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(completed.stdout or b"")
    output.chmod(0o600)
    log(f"backup: {output}")
    return output


def deploy_init(target: Path) -> Path:
    target = Path(target)
    if target.exists():
        raise DeployError(f"{target} already exists; edit it instead")
    target.write_text(
        EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    target.chmod(0o600)
    return target
