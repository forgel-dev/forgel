"""Adopt existing repositories into a container project.

Brownfield adoption never regenerates code. The project gets a control
repository with `forgel.toml`, `program.yaml`, context files and adoption
notes, while the cloned repository keeps its own history and receives a
`forgel-baseline` tag.

A project groups repositories whose code depends on each other. Adding an
independent repository is allowed and does not break anything; Forgel simply
maintains it separately inside the same project.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import ensure_dir, write_json, write_text
from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger
from .program_manifest import (
    add_entry,
    entries,
    set_entries,
    slugify_repo_id,
    unique_repo_id,
    validate_dependencies,
    write_program,
)
from .project_config import ConfigError, load_project_config, render_project_config
from .projects import NAME_RE, ProjectError, create_project
from .providers import AuthReport, ProviderError, Remote, get_provider

ADOPTED_CONTEXT = """# FORGEL.md

Native project instructions for {name}.

This project was adopted from `{url}`. Forgel does not regenerate the
repository; external changes are reconciled and recorded.

## Project

- Name: {name}
- Mode: brownfield
- Repositories: {repos}

## Rules

- Read `forgel.toml` for QA, jurisdiction, model and budget settings.
- Read `program.yaml` for repositories and dependency edges.
- Link only repositories whose code depends on each other.
- Run `forgel sync` after editing outside Forgel.
"""

ADOPTED_AGENTS = """# AGENTS.md

Canonical instructions for agents working on {name}.

## Read First

1. `FORGEL.md` — native project instructions.
2. `forgel.toml` — QA, jurisdiction, model and budget settings.
3. `program.yaml` — repositories and dependency edges.

## Rules

- The code already exists; do not regenerate or overwrite it.
- External edits are first-class; run `forgel sync` before continuing.
- Add a QA scenario for every automatically checkable change.
- Do not add tool attribution lines to commits or pull requests.
"""

GITIGNORE = """__pycache__/
*.py[cod]
node_modules/
.env
.env.*
!.env.example
.DS_Store
.forgel/
"""


class AdoptError(RuntimeError):
    """A repository cannot be adopted into a project."""


@dataclass(frozen=True)
class AdoptResult:
    project_id: str
    repo_id: str
    provider: str
    url: str
    slug: str
    auth: AuthReport
    mode: str


@dataclass(frozen=True)
class RepoAddResult:
    project_id: str
    entry: dict[str, Any]
    auth: AuthReport


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(target),
        capture_output=True,
        text=True,
        check=False,
    )


def _project_name(slug: str) -> str:
    base = slug.rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9 _-]+", "-", base).strip(" -")
    name = re.sub(r"\s+", " ", name)[:64].strip()
    if not name or not name[0].isalnum():
        name = f"project {name}".strip()[:64]
    return name if NAME_RE.fullmatch(name) else "project"


def _clone_temp(
    settings: Settings, url: str
) -> tuple[Path, Path, Remote, AuthReport]:
    provider = get_provider(url)
    try:
        remote = provider.parse(url)
    except ProviderError as exc:
        raise AdoptError(str(exc)) from exc
    ensure_dir(settings.home / "tmp")
    temporary = Path(
        tempfile.mkdtemp(prefix="adopt-", dir=settings.home / "tmp")
    )
    destination = temporary / "repo"
    try:
        provider.clone(remote, destination, settings.home)
    except ProviderError as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        raise AdoptError(str(exc)) from exc
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return temporary, destination, remote, provider.auth(settings.home)


def _move_clone(destination: Path, target: Path) -> None:
    if target.exists() and any(target.iterdir()):
        raise AdoptError(f"repository path is not empty: {target}")
    ensure_dir(target.parent)
    shutil.move(str(destination), str(target))


def _tag_baseline(repository: Path) -> None:
    head = _git(repository, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        raise AdoptError(
            "the repository has no commits yet; commit something before adopting"
        )
    _git(repository, "tag", "-f", "forgel-baseline")


def _control_commit(control: Path, message: str) -> None:
    if not (control / ".git").exists():
        _git(control, "init", "-q")
    _git(control, "add", "-A")
    _git(
        control,
        "-c",
        "user.name=Forgel",
        "-c",
        "user.email=forgel@localhost",
        "commit",
        "-q",
        "-m",
        message,
    )
    _git(control, "tag", "-f", "forgel-baseline")


def _recipe(project: dict[str, Any], layout: ProjectLayout) -> str:
    if project.get("recipe_id"):
        return str(project["recipe_id"])
    try:
        config = load_project_config(layout.control)
    except ConfigError:
        config = None
    return config.recipe if config is not None and config.recipe else ""


def _write_brownfield_files(
    layout: ProjectLayout,
    name: str,
    brief: str,
) -> None:
    repos = entries(layout)
    if not (layout.control / "forgel.toml").exists():
        write_text(
            layout.control / "forgel.toml",
            render_project_config(name),
        )
    write_program(layout, name, _recipe({"recipe_id": ""}, layout))
    repo_ids = ", ".join(entry["id"] for entry in repos)
    for filename, template in (
        ("FORGEL.md", ADOPTED_CONTEXT),
        ("AGENTS.md", ADOPTED_AGENTS),
    ):
        path = layout.control / filename
        if not path.exists():
            url = next(
                (entry["url"] for entry in repos if entry.get("url")), "—"
            )
            write_text(path, template.format(name=name, url=url, repos=repo_ids))
    if not (layout.control / ".gitignore").exists():
        write_text(layout.control / ".gitignore", GITIGNORE)

    write_json(
        layout.artifact("docs/program/requirements.json"),
        {
            "project": name,
            "brief": brief,
            "mode": "brownfield",
            "repos": [entry["id"] for entry in repos],
            "requires": [],
            "excludes": [],
            "region": "unspecified",
            "jurisdiction": "unspecified",
            "entity": "unspecified",
            "payments": False,
            "constraints": [],
        },
    )
    _write_adoption_note(layout, name)
    _write_state(layout, name)


def _write_adoption_note(layout: ProjectLayout, name: str) -> None:
    repos = entries(layout)
    rows = "\n".join(
        f"| {entry['id']} | {entry['provider']} | {entry['url'] or '—'} | "
        f"{', '.join(entry['depends_on']) or '—'} |"
        for entry in repos
    )
    write_text(
        layout.artifact("docs/program/adoption.md"),
        f"""# Adoption

- Project: `{name}`
- Mode: brownfield
- Recorded: {_now()}

## Repositories

| Id | Provider | URL | Depends on |
|---|---|---|---|
{rows}

## Why group repositories

A project groups repositories whose code depends on each other: for example a
frontend consumes a backend contract, or an E2E suite exercises both. The
dependency edges in `program.yaml` are what make the grouping meaningful.

An independent repository can be added to a project; nothing breaks, but Forgel
will maintain it separately. The grouping then adds no coupling.

Forgel does not regenerate adopted repositories. External edits are reconciled
and recorded.
""",
    )
    for entry in repos:
        write_text(
            layout.artifact(f"docs/program/repos/{entry['id']}.md"),
            f"""# Repo: {entry['id']}

- Provider: `{entry['provider']}`
- URL: {entry['url'] or '—'}
- Role: `{entry['role']}`
- Depends on: {', '.join(f'`{item}`' for item in entry['depends_on']) or 'none'}
""",
        )


def _write_state(layout: ProjectLayout, name: str) -> None:
    repos = entries(layout)
    edges = [
        f"- `{entry['id']}` depends on "
        + ", ".join(f"`{item}`" for item in entry["depends_on"])
        for entry in repos
        if entry["depends_on"]
    ] or ["- No dependency edges recorded."]
    write_text(
        layout.artifact("docs/program/state.md"),
        f"""# Project State

- Project: `{name}`
- Mode: brownfield
- Status: adopted
- Repositories: {', '.join(f'`{entry["id"]}`' for entry in repos)}

## Dependency Edges

{chr(10).join(edges)}
""",
    )


def _artifact_ref(layout: ProjectLayout, relative: str) -> str:
    return str(layout.artifact(relative).relative_to(layout.root))


def _event(
    ledger: Ledger,
    project_id: str,
    stage: str,
    refs: list[str],
    payload: dict[str, Any],
) -> None:
    generation = ledger.current_generation(project_id)
    suffix = str(payload.get("repo", ""))
    if stage == "repo_link":
        suffix += ":" + ",".join(payload.get("depends_on", []))
    ledger.append_event(
        project_id,
        stage,
        status="completed",
        idempotency_key=f"{project_id}:{stage}:{suffix}",
        artifact_refs=refs,
        payload=payload,
        generation=generation,
    )


def adopt_repository(
    settings: Settings,
    ledger: Ledger,
    url: str,
    brief: str = "",
    name: str = "",
) -> AdoptResult:
    temporary, clone, remote, auth = _clone_temp(settings, url)
    try:
        project_name = name.strip() or _project_name(remote.slug)
        if not NAME_RE.fullmatch(project_name):
            raise AdoptError(
                "project name must be 1-64 characters of letters, digits, "
                "spaces, hyphens or underscores"
            )
        project_brief = brief.strip() or f"Adopted from {remote.slug}."
        _tag_baseline(clone)
        try:
            project_id = create_project(
                settings,
                ledger,
                project_name,
                project_brief,
                mode="brownfield",
            )
        except ProjectError as exc:
            raise AdoptError(str(exc)) from exc
        layout = ProjectLayout.detect(
            settings.projects_dir / project_id
        )
        repo_id = "main"
        repository = layout.repo_path(repo_id)
        _move_clone(clone, repository)
        entry = {
            "id": repo_id,
            "role": "application",
            "provider": remote.provider,
            "url": remote.url,
            "depends_on": [],
        }
        set_entries(layout, [entry])
        _write_brownfield_files(layout, project_name, project_brief)
        _control_commit(
            layout.control, f"Adopt {remote.slug}"
        )
        _event(
            ledger,
            project_id,
            "adopt",
            [
                _artifact_ref(layout, "program.yaml"),
                _artifact_ref(layout, "docs/program/adoption.md"),
            ],
            {
                "repo": repo_id,
                "provider": remote.provider,
                "url": remote.url,
                "slug": remote.slug,
            },
        )
        return AdoptResult(
            project_id=project_id,
            repo_id=repo_id,
            provider=remote.provider,
            url=remote.url,
            slug=remote.slug,
            auth=auth,
            mode="brownfield",
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def add_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    url: str,
    repo_id: str = "",
    depends_on: list[str] | None = None,
    role: str = "application",
) -> RepoAddResult:
    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_container:
        raise AdoptError(
            "this project uses the legacy flat layout; repositories can only "
            "be added to a container project"
        )
    if layout.metadata().get("mode") != "brownfield":
        raise AdoptError(
            "adding repositories is supported for adopted (brownfield) "
            "projects; template projects already define their repositories"
        )
    temporary, clone, remote, auth = _clone_temp(settings, url)
    try:
        existing = entries(layout)
        known_ids = {entry["id"] for entry in existing}
        if repo_id:
            selected_id = slugify_repo_id(repo_id)
            if selected_id in known_ids:
                raise AdoptError(f"repository id already exists: {selected_id}")
        else:
            selected_id = unique_repo_id(
                layout, remote.slug.rsplit("/", 1)[-1]
            )
        if not selected_id:
            raise AdoptError("repository id must not be empty")
        dependencies = [item.strip() for item in (depends_on or []) if item.strip()]
        if selected_id in dependencies:
            raise AdoptError("a repository cannot depend on itself")
        try:
            validate_dependencies(known_ids, dependencies)
        except ValueError as exc:
            raise AdoptError(str(exc)) from exc

        _tag_baseline(clone)
        repository = layout.repo_path(selected_id)
        _move_clone(clone, repository)
        entry = {
            "id": selected_id,
            "role": role.strip() or "application",
            "provider": remote.provider,
            "url": remote.url,
            "depends_on": dependencies,
        }
        try:
            add_entry(layout, entry)
        except ValueError as exc:
            raise AdoptError(str(exc)) from exc
        _write_brownfield_files(
            layout,
            str(project["name"]),
            str(project["brief"]),
        )
        _control_commit(
            layout.control, f"Add repository {selected_id}"
        )
        _event(
            ledger,
            str(project["id"]),
            "repo_add",
            [
                _artifact_ref(layout, "program.yaml"),
                _artifact_ref(
                    layout, f"docs/program/repos/{selected_id}.md"
                ),
            ],
            {
                "repo": selected_id,
                "provider": remote.provider,
                "url": remote.url,
                "depends_on": dependencies,
            },
        )
        return RepoAddResult(
            project_id=str(project["id"]), entry=entry, auth=auth
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def set_dependencies(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str,
    depends_on: list[str],
) -> dict[str, Any]:
    """Replace the dependency edges of a repository in an existing project."""

    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_container:
        raise AdoptError(
            "dependency edges can only be edited in a container project"
        )
    current = entries(layout)
    known_ids = {entry["id"] for entry in current}
    if repo_id not in known_ids:
        raise AdoptError(f"unknown repository id: {repo_id}")
    dependencies = [item.strip() for item in depends_on if item.strip()]
    if repo_id in dependencies:
        raise AdoptError("a repository cannot depend on itself")
    try:
        validate_dependencies(known_ids, dependencies)
    except ValueError as exc:
        raise AdoptError(str(exc)) from exc

    updated: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for entry in current:
        if entry["id"] == repo_id:
            selected = {**entry, "depends_on": dependencies}
            updated.append(selected)
        else:
            updated.append(entry)
    assert selected is not None
    set_entries(layout, updated)
    write_program(layout, str(project["name"]), _recipe(project, layout))
    if layout.metadata().get("mode") == "brownfield":
        _write_adoption_note(layout, str(project["name"]))
        _write_state(layout, str(project["name"]))
    _control_commit(layout.control, f"Link repository {repo_id}")
    refs = [_artifact_ref(layout, "program.yaml")]
    if layout.metadata().get("mode") == "brownfield":
        refs.append(
            _artifact_ref(layout, f"docs/program/repos/{repo_id}.md")
        )
    _event(
        ledger,
        str(project["id"]),
        "repo_link",
        refs,
        {"repo": repo_id, "depends_on": dependencies},
    )
    return selected
