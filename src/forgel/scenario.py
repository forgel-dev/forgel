"""A permanent scenario sandbox.

Real scenarios need the real runtime and a real model, but no public effect:
no GitHub repository, no push, no release on a real remote. The sandbox gives
each scenario its own home and workspace, a local clone of a fixture
repository with no remote, local repository creation instead of a provider,
and no GitHub credentials. Everything a scenario writes stays in a temporary
tree; the caller can keep it for inspection or let it be removed.

The runner drives the same CommandRouter the console and Telegram use. It
executes the agent's actions against the sandbox, so a scenario observes the
real intake, planning, task and release behaviour rather than a canned
transcript.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from . import adopt, chat as chat_module, git_ops, planner as planner_module, tasks
from .adopt import (
    AdoptError,
    RepoAddResult,
    RepoCreateResult,
    _init_local_repository,
    _update_entry,
    validate_dependencies,
)
from .chat import CommandRouter
from .config import Settings
from .daemon import run_once
from .layout import ProjectLayout
from .ledger import Ledger
from .model import ModelClient, build_model_client
from .program_manifest import add_entry, set_entries, slugify_repo_id, write_program
from .projects import create_project
from .providers.base import AuthReport


class ScenarioError(RuntimeError):
    """The sandbox cannot be prepared or the scenario cannot run."""


@dataclass
class Sandbox:
    root: Path
    settings: Settings
    ledger: Ledger
    project_id: str
    project: dict[str, Any]
    layout: ProjectLayout
    keep: bool = False

    def run(
        self,
        messages: Sequence[str],
        client: ModelClient | None = None,
        execute: bool = False,
        max_cycles: int = 20,
        log: Callable[[str], None] = print,
    ) -> list[str]:
        """Send messages through the real router; optionally run the daemon."""

        model = client or build_model_client(self.settings.home, log=log)
        if model is None:
            raise ScenarioError(
                "no model is configured; pass a client or set a model key"
            )
        from .agent import ProjectAgent

        agent = ProjectAgent(self.settings, self.ledger, model)
        router = CommandRouter(
            self.settings,
            self.ledger,
            daemon_enabled=False,
            agent=agent,
        )
        replies: list[str] = []
        with _sandbox_repositories(), _without_github_env():
            for message in messages:
                log(f"[scenario] user: {message}")
                reply = router.handle(0, message, "sandbox")
                replies.append(reply.text)
                log(f"[scenario] reply: {reply.text}")
            if execute:
                for _ in range(max_cycles):
                    processed = run_once(
                        self.settings,
                        self.ledger,
                        log=log,
                        client=model,
                    )
                    if not processed:
                        break
        return replies

    def close(self) -> None:
        if not self.keep:
            shutil.rmtree(self.root, ignore_errors=True)


def create_sandbox(
    fixture: Path,
    snapshot: str = "",
    root: Path | None = None,
    keep: bool = False,
) -> Sandbox:
    """Build an isolated home and a clone of the fixture with no remote."""

    fixture = Path(fixture).expanduser().resolve()
    if not (fixture / ".git").exists():
        raise ScenarioError(f"fixture is not a git repository: {fixture}")
    base = (
        Path(root).expanduser().resolve()
        if root is not None
        else Path(tempfile.mkdtemp(prefix="forgel-scenario-"))
    )
    base.mkdir(parents=True, exist_ok=True)
    home = base / "home"
    home.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_env(home)
    ledger = Ledger(settings.db_path)
    project_id = create_project(
        settings,
        ledger,
        "Scenario sandbox",
        "Isolated scenario workspace.",
        mode="brownfield",
    )
    project = ledger.get_project(project_id)
    assert project is not None
    layout = ProjectLayout.detect(project["workspace"])
    repo = layout.repo_path("main")
    repo.parent.mkdir(parents=True, exist_ok=True)
    _git(base, "clone", "--no-tags", "--no-hardlinks", str(fixture), str(repo))
    if snapshot:
        _git(repo, "checkout", "-q", snapshot)
    _git(repo, "remote", "remove", "origin")
    set_entries(
        layout,
        [
            {
                "id": "main",
                "role": "application",
                "provider": "local",
                "url": "",
                "depends_on": [],
            }
        ],
    )
    write_program(layout, str(project["name"]), "")
    ledger.set_session(0, project_id)
    return Sandbox(
        root=base,
        settings=settings,
        ledger=ledger,
        project_id=project_id,
        project=project,
        layout=layout,
        keep=keep,
    )


def _git(cwd: Path, *args: str, check: bool = True) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise ScenarioError(
            f"git {' '.join(args)}: {result.stderr or result.stdout}"
        )


def _local_path(
    layout: ProjectLayout, repo_id: str, path: str
) -> Path:
    if layout.is_linked and str(path or "").strip():
        return Path(path).expanduser().resolve()
    return layout.repo_path(repo_id)


def _register_local(
    layout: ProjectLayout,
    project: Mapping[str, Any],
    repo_id: str,
    local: Path,
    role: str,
    depends_on: Sequence[str],
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": repo_id,
        "role": role or "application",
        "provider": "local",
        "url": "",
        "depends_on": [str(item) for item in depends_on if str(item).strip()],
    }
    if layout.is_linked:
        entry["path"] = str(local)
    add_entry(layout, entry)
    write_program(
        layout, str(project["name"]), str(project.get("recipe") or "")
    )
    tasks.commit_control(layout, f"Create sandbox repository {repo_id}")
    return entry


def sandbox_create_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str,
    org: str = "",
    private: bool = True,
    depends_on: list[str] | None = None,
    role: str = "application",
    description: str = "",
    path: str = "",
    api: Any | None = None,
    auth: Any | None = None,
) -> RepoCreateResult:
    """A local repository instead of a provider repository."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    selected = slugify_repo_id(repo_id)
    if not selected:
        raise AdoptError("repository id must not be empty")
    known = {str(entry["id"]) for entry in _entries(layout)}
    if selected in known:
        raise AdoptError(f"repository id already exists: {selected}")
    dependencies = [
        str(item).strip()
        for item in (depends_on or [])
        if str(item).strip()
    ]
    try:
        validate_dependencies(known, dependencies)
    except ValueError as exc:
        raise AdoptError(str(exc)) from exc
    local = _local_path(layout, selected, path)
    if local.exists() and any(local.iterdir()):
        raise AdoptError(f"local repository already exists: {local}")
    _init_local_repository(local, selected, description)
    entry = _register_local(
        layout, project, selected, local, role, dependencies
    )
    return RepoCreateResult(
        project_id=str(project["id"]),
        entry=entry,
        url="",
        created=True,
    )


def sandbox_add_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    url: str,
    repo_id: str = "",
    depends_on: list[str] | None = None,
    role: str = "application",
) -> RepoAddResult:
    """Add a local copy of a repository, never a provider clone."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    source = Path(str(url or "")).expanduser()
    selected = slugify_repo_id(repo_id or source.name)
    if not selected:
        raise AdoptError("repository id must not be empty")
    known = {str(entry["id"]) for entry in _entries(layout)}
    if selected in known:
        raise AdoptError(f"repository id already exists: {selected}")
    dependencies = [
        str(item).strip()
        for item in (depends_on or [])
        if str(item).strip()
    ]
    try:
        validate_dependencies(known, dependencies)
    except ValueError as exc:
        raise AdoptError(str(exc)) from exc
    local = _local_path(layout, selected, "")
    if local.exists() and any(local.iterdir()):
        raise AdoptError(f"local repository already exists: {local}")
    if (source / ".git").exists():
        _git(local.parent, "clone", "--no-tags", "--no-hardlinks", str(source), str(local))
        _git(local, "remote", "remove", "origin")
    else:
        _init_local_repository(local, selected, "Sandbox repository")
    entry = _register_local(
        layout, project, selected, local, role, dependencies
    )
    return RepoAddResult(
        project_id=str(project["id"]),
        entry=entry,
        auth=AuthReport(configured=False, detail="scenario sandbox"),
    )


def sandbox_publish_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str,
    org: str = "",
    private: bool = True,
    description: str = "",
    api: Any | None = None,
    auth: Any | None = None,
) -> RepoCreateResult:
    """Publish to a local bare remote, never to a provider."""

    layout = ProjectLayout.detect(str(project["workspace"]))
    entry = next(
        (
            dict(item)
            for item in _entries(layout)
            if str(item.get("id")) == repo_id
        ),
        None,
    )
    if entry is None:
        raise AdoptError(f"unknown repository {repo_id!r}")
    local = layout.repo_path(repo_id)
    if not (local / ".git").exists():
        raise AdoptError(f"repository {repo_id} has no git history")
    remote = (
        settings.home.parent / "remotes" / f"{repo_id}.git"
    ).resolve()
    remote.parent.mkdir(parents=True, exist_ok=True)
    if not remote.exists():
        _git(remote.parent, "init", "--bare", "-q", str(remote))
    branch = git_ops.current_branch(local)
    _git(local, "remote", "remove", "origin", check=False)
    _git(local, "remote", "add", "origin", str(remote))
    _git(local, "push", "--set-upstream", "origin", branch)
    entry["provider"] = "local"
    entry["url"] = str(remote)
    _update_entry(layout, entry)
    write_program(
        layout, str(project["name"]), str(project.get("recipe") or "")
    )
    tasks.commit_control(layout, f"Publish sandbox repository {repo_id}")
    return RepoCreateResult(
        project_id=str(project["id"]),
        entry=entry,
        url=str(remote),
        created=True,
    )


def _entries(layout: ProjectLayout) -> list[dict[str, Any]]:
    from .program_manifest import entries

    return entries(layout)


@contextmanager
def _sandbox_repositories() -> Iterator[None]:
    originals = {
        (chat_module, "create_repository"): chat_module.create_repository,
        (chat_module, "add_repository"): chat_module.add_repository,
        (chat_module, "publish_repository"): chat_module.publish_repository,
        (planner_module, "create_repository"): planner_module.create_repository,
        (planner_module, "add_repository"): planner_module.add_repository,
    }
    chat_module.create_repository = sandbox_create_repository
    chat_module.add_repository = sandbox_add_repository
    chat_module.publish_repository = sandbox_publish_repository
    planner_module.create_repository = sandbox_create_repository
    planner_module.add_repository = sandbox_add_repository
    try:
        yield
    finally:
        for (module, name), value in originals.items():
            setattr(module, name, value)


@contextmanager
def _without_github_env() -> Iterator[None]:
    keys = [
        key
        for key in os.environ
        if key.startswith("FORGEL_GITHUB_")
        or key in {"GITHUB_TOKEN", "GH_TOKEN"}
    ]
    saved = {key: os.environ.pop(key) for key in keys}
    try:
        yield
    finally:
        os.environ.update(saved)


def load_scenario(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScenarioError(f"cannot read scenario {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ScenarioError(f"scenario {path} must be an object")
    messages = data.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(item, str) and item.strip() for item in messages
    ):
        raise ScenarioError(f"scenario {path}: messages must be strings")
    return data
