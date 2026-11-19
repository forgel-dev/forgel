"""Per-project sandbox (D-073).

``FORGEL_SANDBOX=docker`` runs project commands in a container on a separate
Docker daemon. The daemon the CLI talks to is configured with ``DOCKER_HOST``
(a remote engine or a DinD sidecar); the host socket is never mounted into a
project container, and the project container gets one writable repository plus
the declared read-only siblings, nothing else.

The boundary is deliberately small:

- a fresh container per session, labelled ``forgel.kind=sandbox``;
- the selected repository at ``/workspace``, sibling repositories from the
  contract's ``mounts`` read-only at ``/<id>``;
- the container runs as the daemon's UID/GID, not root, with all capabilities
  dropped, ``no-new-privileges``, a read-only root filesystem and a small
  writable ``/tmp``;
- CPU, memory and pid limits and a configurable network;
- an optional registry allowlist and mandatory digest pinning.

``local`` remains the single-tenant fallback and is not implemented here.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from .config import Settings
from .environment import Environment, command_argv, mount_env_name
from .layout import ProjectLayout
from .proc import merge_output

WORKDIR = "/workspace"
CONTAINER_NAME = re.compile(r"forgel-sbx-[a-z0-9-]+")
MAX_OUTPUT = 20_000
DOCKER_ENV_KEYS = (
    "DOCKER_HOST",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
)


class SandboxError(RuntimeError):
    """The sandbox cannot run a command."""


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], timeout: float) -> tuple[int, str]: ...


@dataclass(frozen=True)
class SandboxInfo:
    name: str
    detail: str


def _cap(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text)} chars]"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "project"


class DockerSandbox:
    """A sandbox backed by a Docker daemon that runs project code."""

    name = "docker"

    def __init__(
        self,
        settings: Settings,
        log: Callable[[str], None] = print,
    ) -> None:
        self.settings = settings
        self.log = log

    # ------------------------------------------------------------- plumbing

    def _cli(self) -> list[str]:
        binary = shutil.which("docker")
        if binary is None:
            raise SandboxError(
                "the docker CLI is not installed; the sandbox cannot run"
            )
        return [binary]

    def _env(self) -> dict[str, str]:
        env = {
            key: os.environ[key]
            for key in DOCKER_ENV_KEYS
            if os.environ.get(key)
        }
        if self.settings.sandbox_host:
            env["DOCKER_HOST"] = self.settings.sandbox_host
        env["PATH"] = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        # The CLI runs as the daemon user, whose home may not be writable (in
        # the container HOME is root's home). Fall back to the Forgel home so
        # the CLI can read its config; keep the real home on the host so the
        # Docker context and credentials still work.
        home = os.environ.get("HOME", "")
        if not home or not os.access(home, os.W_OK):
            home = str(self.settings.home)
        env["HOME"] = home
        return env

    def _run(
        self,
        argv: Sequence[str],
        timeout: float,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one docker CLI call. Tests override this method."""

        try:
            return subprocess.run(
                [*self._cli(), *argv],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env(),
                input=input_text,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise
        except (OSError, subprocess.SubprocessError) as exc:
            raise SandboxError(f"docker CLI failed: {exc}") from exc

    def _checked(
        self, argv: Sequence[str], timeout: float, what: str
    ) -> str:
        try:
            result = self._run(argv, timeout)
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"{what} timed out after {timeout:g}s") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise SandboxError(f"{what} failed: {detail[-MAX_OUTPUT:]}")
        return result.stdout

    # -------------------------------------------------------------- checks

    def available(self) -> tuple[bool, str]:
        try:
            version = self._checked(
                ["version", "--format", "{{.Server.Version}}"],
                timeout=15,
                what="docker daemon check",
            ).strip()
        except SandboxError as exc:
            return False, str(exc)
        if not version:
            return False, "docker daemon returned no version"
        return True, version

    def info(self) -> SandboxInfo:
        ok, detail = self.available()
        if not ok:
            return SandboxInfo(self.name, detail)
        host = self.settings.sandbox_host or os.environ.get(
            "DOCKER_HOST", "default socket"
        )
        return SandboxInfo(self.name, f"docker {detail} at {host}")

    def check_image(self, ref: str) -> str:
        """Enforce the registry policy and return the image reference."""

        ref = ref.strip()
        if not ref:
            raise SandboxError("the environment has no image")
        digest = "@sha256:" in ref
        name = ref.split("@", 1)[0]
        if self.settings.sandbox_require_digest and not digest:
            raise SandboxError(
                f"image {ref!r} is not pinned by digest; set "
                "FORGEL_SANDBOX_REQUIRE_DIGEST=0 or pin @sha256:..."
            )
        allowlist = self.settings.sandbox_images
        if allowlist and not any(name.startswith(item) for item in allowlist):
            raise SandboxError(
                f"image {name!r} is not in FORGEL_SANDBOX_IMAGES "
                f"({', '.join(allowlist)})"
            )
        return ref

    # --------------------------------------------------------------- images

    def ensure_image(
        self,
        layout: ProjectLayout,
        environment: Environment | None,
        project_id: str,
    ) -> str:
        if environment is not None and environment.build:
            return self._build(layout, environment, project_id)
        ref = (
            environment.image
            if environment is not None and environment.image
            else self.settings.sandbox_image
        )
        if not ref:
            raise SandboxError(
                "the project has no environment.yaml and "
                "FORGEL_SANDBOX_IMAGE is empty; the sandbox needs an image"
            )
        return self.check_image(ref)

    def _build(
        self,
        layout: ProjectLayout,
        environment: Environment,
        project_id: str,
    ) -> str:
        base = environment.base or layout.root
        context = (base / environment.build).resolve()
        dockerfile = context / "Dockerfile"
        if not dockerfile.is_file():
            raise SandboxError(
                f"environment build context has no Dockerfile: {context}"
            )
        tag = f"forgel-env-{_slug(project_id)}:latest"
        self._checked(
            [
                "build",
                "-t",
                tag,
                "-f",
                self.daemon_path(dockerfile),
                self.daemon_path(context),
            ],
            timeout=1800,
            what=f"build of {tag}",
        )
        return tag

    def daemon_path(self, path: Path) -> str:
        """Path as the Docker daemon sees it.

        With a remote daemon or a DinD sidecar the local projects directory is
        mounted there under ``FORGEL_SANDBOX_PROJECTS_ROOT``. Bind-mount
        sources are resolved on the daemon, not on this host.
        """

        resolved = path.resolve()
        root = self.settings.sandbox_projects_root
        if not root:
            return str(resolved)
        try:
            relative = resolved.relative_to(
                self.settings.projects_dir.resolve()
            )
        except ValueError as exc:
            raise SandboxError(
                f"{resolved} is outside the projects directory; the sandbox "
                "cannot mount it"
            ) from exc
        return str(Path(root) / relative)

    # -------------------------------------------------------------- session

    def session(
        self,
        layout: ProjectLayout,
        environment: Environment | None,
        project_id: str,
        repo_id: str,
    ) -> DockerSession:
        if not repo_id:
            raise SandboxError(
                "the sandbox mounts exactly one repository; set 'repo' in "
                "environment.yaml"
            )
        repo = layout.repo_path(repo_id)
        if not repo.is_dir():
            raise SandboxError(f"repository not found: {repo}")
        image = self.ensure_image(layout, environment, project_id)
        setup = environment.setup if environment is not None else ()
        env = list(environment.env if environment is not None else ())
        extra: list[tuple[str, str]] = []
        if environment is not None:
            for sibling in environment.mounts:
                path = layout.repo_path(sibling)
                if not path.is_dir():
                    raise SandboxError(
                        f"repository {sibling!r} from 'mounts' not found"
                    )
                extra.append((self.daemon_path(path), f"/{sibling}"))
                env.append((mount_env_name(sibling), f"/{sibling}"))
        return DockerSession(
            sandbox=self,
            project_id=project_id,
            image=image,
            mount=self.daemon_path(repo),
            setup=setup,
            env=tuple(env),
            extra_mounts=extra,
            log=self.log,
        )


class DockerSession:
    """One live sandbox container for a project session."""

    def __init__(
        self,
        sandbox: DockerSandbox,
        project_id: str,
        image: str,
        mount: str,
        setup: Sequence[str] = (),
        env: Sequence[tuple[str, str]] = (),
        extra_mounts: Sequence[tuple[str, str]] = (),
        log: Callable[[str], None] = print,
        name: str | None = None,
    ) -> None:
        self.sandbox = sandbox
        self.project_id = project_id
        self.image = image
        self.mount = mount
        self.setup = tuple(setup)
        self.env = tuple(env)
        self.extra_mounts = tuple(extra_mounts)
        self.log = log
        self.name = name or (
            f"forgel-sbx-{_slug(project_id)}-{secrets.token_hex(4)}"
        )
        if not CONTAINER_NAME.fullmatch(self.name):
            raise SandboxError(f"invalid sandbox container name: {self.name}")
        self._running = False
        self._dead = False

    # -------------------------------------------------------------- lifecycle

    def __enter__(self) -> DockerSession:
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.stop()

    def start(self) -> None:
        argv = self._run_argv()
        result = self.sandbox._run(argv, timeout=180)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            raise SandboxError(f"sandbox container failed to start: {detail}")
        self._running = True
        self.log(f"[sandbox] {self.project_id}: {self.name} ({self.image})")
        try:
            self._run_setup()
        except Exception:
            self.stop()
            raise

    def _run_argv(self) -> list[str]:
        settings = self.sandbox.settings
        uid = os.getuid()
        gid = os.getgid()
        argv = [
            "run",
            "-d",
            "--rm",
            "--name",
            self.name,
            "--label",
            f"forgel.project={self.project_id}",
            "--label",
            "forgel.kind=sandbox",
            "--network",
            settings.sandbox_network,
            "--cpus",
            settings.sandbox_cpus,
            "--memory",
            settings.sandbox_memory,
            "--pids-limit",
            str(settings.sandbox_pids),
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            f"{uid}:{gid}",
            "-e",
            "HOME=/tmp",
            "-e",
            "TMPDIR=/tmp",
        ]
        for key, value in self.env:
            argv.extend(["-e", f"{key}={value}"])
        argv.extend(
            [
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=256m",
                "-v",
                f"{self.mount}:{WORKDIR}:rw",
            ]
        )
        for source, destination in self.extra_mounts:
            argv.extend(["-v", f"{source}:{destination}:ro"])
        argv.extend(["-w", WORKDIR])
        if settings.sandbox_read_only:
            argv.extend(["--read-only"])
        argv.extend(["--entrypoint", "sleep", self.image, "infinity"])
        return argv

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        try:
            self.sandbox._run(["stop", "-t", "3", self.name], timeout=30)
        except (SandboxError, subprocess.TimeoutExpired):
            try:
                self.sandbox._run(["rm", "-f", self.name], timeout=30)
            except (SandboxError, subprocess.TimeoutExpired):
                self.log(f"[sandbox] {self.project_id}: could not remove {self.name}")

    # -------------------------------------------------------------- commands

    def _run_setup(self) -> None:
        for command in self.setup:
            try:
                argv = command_argv(command)
            except Exception as exc:  # noqa: BLE001 - reported as a sandbox error
                raise SandboxError(f"invalid setup command {command!r}: {exc}") from exc
            code, output = self._exec(argv, timeout=900)
            if code != 0:
                raise SandboxError(
                    f"setup command exited {code}: {command}\n{_cap(output)}"
                )

    def run(
        self, command: Sequence[str], timeout: float = 120.0
    ) -> tuple[int, str]:
        if self._dead:
            raise SandboxError(
                "the sandbox session ended after a timed-out command"
            )
        if not self._running:
            raise SandboxError("the sandbox session is not running")
        try:
            return self._exec(list(command), timeout)
        except subprocess.TimeoutExpired as exc:
            partial = merge_output(exc.stdout, exc.stderr)
            self._dead = True
            self.stop()
            return 124, _cap(
                f"timed out after {timeout:g}s; the sandbox was stopped\n"
                f"{partial}"
            )

    def _exec(self, command: list[str], timeout: float) -> tuple[int, str]:
        result = self.sandbox._run(
            ["exec", self.name, *command], timeout=timeout
        )
        output = merge_output(result.stdout, result.stderr)
        return result.returncode, _cap(output)


def docker_runner(settings: Settings) -> DockerSandbox | None:
    """Return the docker sandbox when it is configured, otherwise ``None``."""

    if settings.sandbox == "docker":
        return DockerSandbox(settings)
    return None
