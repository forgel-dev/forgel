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

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import git_ops
from .artifacts import ensure_dir, write_json, write_text
from .config import Settings
from .layout import ProjectLayout
from .ledger import Ledger, new_project_id
from .program_manifest import (
    add_entry,
    entries,
    set_entries,
    slugify_repo_id,
    unique_repo_id,
    update_metadata,
    validate_dependencies,
    write_program,
)
from .project_config import (
    ConfigError,
    GitConfig,
    load_project_config,
    render_project_config,
)
from .projects import NAME_RE, ProjectError, create_project
from .providers import AuthReport, ProviderError, Remote, get_provider
from .providers.github_api import GithubAPI, GithubAPIError
from .providers.github_auth import (
    DEFAULT_API_BASE,
    AuthToken,
    GithubAuth,
    GithubAuthError,
)

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




CONTROL_PATHS = (
    "forgel.toml",
    "program.yaml",
    "FORGEL.md",
    "AGENTS.md",
    ".gitignore",
    "docs/program",
)


def _commit_control(layout: ProjectLayout, message: str) -> None:
    """Version control artifacts, without touching the user's other work."""

    if not layout.is_linked:
        _control_commit(layout.control, message)
        return
    if layout.control.resolve() != layout.root.resolve():
        _control_commit(layout.control, message)
        return
    paths = [
        item for item in CONTROL_PATHS if (layout.root / item).exists()
    ]
    _assert_no_local_environment(layout.root, paths)
    try:
        git_ops.commit_paths(layout.root, paths, message)
    except git_ops.GitOperationError:
        return


LOCAL_ENVIRONMENT_MARKERS = (
    "BEGIN OPENSSH PRIVATE KEY",
    "BEGIN RSA PRIVATE KEY",
    "FORGEL_MODEL_API_KEY=",
    "FORGEL_GITHUB_TOKEN=",
    "FORGEL_GITHUB_APP_PRIVATE_KEY=",
)


def _assert_no_local_environment(root: Path, paths: list[str]) -> None:
    """Refuse to commit machine-specific paths or credentials."""

    markers = (
        str(Path.home()),
        str(root.resolve()),
    ) + LOCAL_ENVIRONMENT_MARKERS
    leaks: list[str] = []
    for item in paths:
        target = root / item
        if target.is_file():
            files = [target]
        elif target.is_dir():
            files = [path for path in target.rglob("*") if path.is_file()]
        else:
            continue
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if any(marker and marker in text for marker in markers):
                leaks.append(str(path.relative_to(root)))
    if leaks:
        raise AdoptError(
            "refusing to commit local environment data in: "
            + ", ".join(sorted(leaks))
        )


def _default_base_branch(
    layout: ProjectLayout, repos: list[dict[str, Any]]
) -> str:
    for entry in repos:
        repository = layout.repo_path(entry["id"])
        if not (repository / ".git").exists():
            continue
        result = _git(repository, "rev-parse", "--abbrev-ref", "HEAD")
        branch = result.stdout.strip()
        if result.returncode == 0 and branch and branch != "HEAD":
            return branch
    return "main"


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
            render_project_config(
                name,
                git_base_branch=_default_base_branch(layout, repos),
            ),
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
                (entry["url"] for entry in repos if entry.get("url")),
                "a local folder",
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
        f"| {entry['id']} | {entry['provider']} | {entry['url'] or 'local folder'} | "
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
- URL: {entry['url'] or 'local folder'}
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
    path = layout.artifact(relative)
    try:
        return str(path.relative_to(layout.root))
    except ValueError:
        return str(path)


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




def _local_directory(value: str) -> Path | None:
    """A local folder passed to adoption, or ``None`` for a remote URL."""

    raw = value.strip()
    if not raw or "://" in raw or raw.startswith("git@"):
        return None
    path = Path(raw).expanduser()
    return path.resolve() if path.is_dir() else None


def _ensure_source_repository(root: Path) -> Path:
    """Keep the source folder in place: git, an ignore entry, a first commit."""

    result = _git(root, "rev-parse", "--show-toplevel")
    if result.returncode == 0 and result.stdout.strip():
        root = Path(result.stdout.strip()).resolve()
    if not (root / ".git").exists():
        init = _git(root, "init", "-b", "main")
        if init.returncode != 0:
            raise AdoptError(
                "git init failed: " + (init.stderr or init.stdout).strip()
            )
    gitignore = root / ".gitignore"
    changed = False
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8")
        ignored = any(
            line.strip() in {".forgel/", ".forgel"}
            for line in text.splitlines()
        )
        if not ignored:
            if text and not text.endswith("\n"):
                text += "\n"
            gitignore.write_text(text + ".forgel/\n", encoding="utf-8")
            changed = True
    else:
        gitignore.write_text(".forgel/\n", encoding="utf-8")
        changed = True
    head = _git(root, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        _git(root, "add", "-A")
        staged = _git(root, "diff", "--cached", "--name-only").stdout.splitlines()
        suspicious = git_ops.secret_like(staged)
        if suspicious:
            raise AdoptError(
                "refusing to create the first commit: local environment files "
                "would be included: " + ", ".join(suspicious)
            )
        commit = _git(
            root,
            "-c", "user.name=Forgel",
            "-c", "user.email=forgel@localhost",
            "commit", "-q", "--allow-empty", "-m",
            "Initialize with Forgel",
        )
        if commit.returncode != 0:
            raise AdoptError(
                "git commit failed: "
                + (commit.stderr or commit.stdout).strip()
            )
    elif changed:
        _git(root, "add", "--", ".gitignore")
        _git(
            root,
            "-c", "user.name=Forgel",
            "-c", "user.email=forgel@localhost",
            "commit", "-q", "-m", "Adopt with Forgel", "--", ".gitignore",
        )
    return root


def _source_remote(root: Path) -> tuple[str, str]:
    origin = git_ops.origin_url(root)
    if not origin:
        return "", "local"
    try:
        remote = get_provider(origin).parse(origin)
    except (ProviderError, ValueError):
        return "", "local"
    return remote.url, remote.provider


def _remote_name(url: str) -> str:
    """Project name from the repository identity, never from the local path."""

    if not url:
        return ""
    try:
        remote = get_provider(url).parse(url)
    except (ProviderError, ValueError):
        return ""
    return _project_name(remote.slug)


def _maybe_create_remote(
    settings: Settings,
    root: Path,
    project_name: str,
    brief: str,
) -> tuple[str, str, AuthReport]:
    """Create an origin repository when the folder has none."""

    try:
        auth_client = GithubAuth(settings.home)
        token = auth_client.resolve("auto")
    except GithubAuthError as exc:
        return (
            "",
            "local",
            AuthReport(
                configured=False,
                detail=f"no origin remote and GitHub is not configured: {exc}",
            ),
        )
    client = GithubAPI(token.token, api_base=auth_client.api_base)
    org = os.environ.get("FORGEL_GITHUB_ORG", "").strip()
    if org:
        owner = org
    elif token.kind == "pat":
        owner = str(client.user().get("login", "")).strip()
    else:
        return (
            "",
            "local",
            AuthReport(
                configured=False,
                detail=(
                    "no origin remote and FORGEL_GITHUB_ORG is not set; "
                    "a GitHub App needs the organization"
                ),
            ),
        )
    if not owner:
        return (
            "",
            "local",
            AuthReport(
                configured=False,
                detail="no origin remote and the GitHub owner is unknown",
            ),
        )
    name = slugify_repo_id(project_name)
    try:
        full_name, url = _create_remote(
            client, name, owner, True, brief
        )
    except AdoptError as exc:
        return "", "local", AuthReport(configured=False, detail=str(exc))
    try:
        git_ops.ensure_remote(root, url)
        branch = git_ops.current_branch(root) or "main"
        git_ops.push(root, branch, token.token)
    except git_ops.GitOperationError as exc:
        return (
            url,
            "github",
            AuthReport(
                configured=True,
                detail=f"origin created at {full_name}; push failed: {exc}",
            ),
        )
    return (
        url,
        "github",
        AuthReport(
            configured=True,
            detail=f"origin created at {full_name}",
        ),
    )


def _adopt_linked(
    settings: Settings,
    ledger: Ledger,
    path: Path,
    brief: str,
    name: str,
) -> AdoptResult:
    """Adopt a local folder in place: no clone, no second copy of the code."""

    root = _ensure_source_repository(path)
    if (root / ".forgel" / "project.json").exists():
        raise AdoptError(
            "this folder is already a Forgel project; select it with "
            "`/use <id>` or adopt from a copy"
        )
    for existing in ledger.list_projects():
        if Path(existing["workspace"]).resolve() == root.resolve():
            raise AdoptError(
                f"this folder is already adopted as {existing['id']}; "
                f"select it with `/use {existing['id']}`"
            )
    url, provider = _source_remote(root)
    project_name = (
        name.strip() or _remote_name(url) or _project_name(root.name)
    )
    if not NAME_RE.fullmatch(project_name):
        raise AdoptError(
            "project name must be 1-64 characters of letters, digits, "
            "spaces, hyphens or underscores"
        )
    project_brief = brief.strip() or f"Adopted in place: {project_name}."
    if url:
        auth = AuthReport(
            configured=True,
            detail=f"using the existing origin {url}",
        )
    else:
        url, provider, auth = _maybe_create_remote(
            settings, root, project_name, project_brief
        )
        if not url:
            url = ""
            provider = "local"
    project_id = new_project_id(project_name)
    ensure_dir(root / ".forgel")
    entry = {
        "id": "main",
        "role": "application",
        "provider": provider,
        "url": url,
        "path": ".",
        "depends_on": [],
    }
    write_json(
        root / ".forgel" / "project.json",
        {
            "id": project_id,
            "name": project_name,
            "layout": "linked",
            "mode": "brownfield",
            "repos": [entry],
            "created_at": _now(),
        },
    )
    ledger.create_project(
        project_id, project_name, project_brief, str(root)
    )
    layout = ProjectLayout.detect(root)
    _write_brownfield_files(layout, project_name, project_brief)
    _commit_control(layout, f"Adopt {project_name}")
    _tag_baseline(root)
    _event(
        ledger,
        project_id,
        "adopt",
        [
            _artifact_ref(layout, "program.yaml"),
            _artifact_ref(layout, "docs/program/adoption.md"),
        ],
        {
            "repo": "main",
            "provider": provider,
            "url": url,
            "mode": "linked",
        },
    )
    return AdoptResult(
        project_id=project_id,
        repo_id="main",
        provider=provider,
        url=url,
        slug=root.name,
        auth=auth,
        mode="brownfield",
    )


def adopt_repository(
    settings: Settings,
    ledger: Ledger,
    url: str,
    brief: str = "",
    name: str = "",
) -> AdoptResult:
    local = _local_directory(url)
    if local is not None:
        return _adopt_linked(settings, ledger, local, brief, name)
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




def _add_linked_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    layout: ProjectLayout,
    url: str,
    repo_id: str,
    depends_on: list[str] | None,
    role: str,
) -> "RepoAddResult":
    local = _local_directory(url)
    if local is None:
        raise AdoptError(
            "linked projects add local folders; clone a remote repository "
            "yourself and add its path"
        )
    top = _git(local, "rev-parse", "--show-toplevel")
    if top.returncode != 0 or not top.stdout.strip():
        raise AdoptError(
            f"{local} has no git history; commit it before adding"
        )
    root = Path(top.stdout.strip()).resolve()
    head = _git(root, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        raise AdoptError(
            f"{root} has no commits; commit it before adding"
        )
    if root == layout.root.resolve():
        raise AdoptError(
            "the folder is already the project's main repository"
        )
    existing = entries(layout)
    known_ids = {entry["id"] for entry in existing}
    for entry in existing:
        if layout.repo_path(entry["id"]).resolve() == root:
            raise AdoptError(
                f"repository {entry['id']} already points at {root}"
            )
    origin, provider = _source_remote(root)
    if repo_id:
        selected_id = slugify_repo_id(repo_id)
        if selected_id in known_ids:
            raise AdoptError(
                f"repository id already exists: {selected_id}"
            )
    else:
        remote_name = _remote_name(origin)
        selected_id = unique_repo_id(layout, remote_name or root.name)
    dependencies = [
        item.strip() for item in (depends_on or []) if item.strip()
    ]
    if selected_id in dependencies:
        raise AdoptError("a repository cannot depend on itself")
    try:
        validate_dependencies(known_ids, dependencies)
    except ValueError as exc:
        raise AdoptError(str(exc)) from exc
    entry = {
        "id": selected_id,
        "role": role.strip() or "application",
        "provider": provider,
        "url": origin,
        "path": str(root),
        "depends_on": dependencies,
    }
    add_entry(layout, entry)
    _write_repo_doc(layout, entry)
    write_program(
        layout,
        str(project["name"]),
        str(project.get("recipe_id") or ""),
    )
    _commit_control(layout, f"Add repository {selected_id}")
    _tag_baseline(root)
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
            "provider": provider,
            "url": origin,
            "depends_on": dependencies,
            "path": str(root),
        },
    )
    return RepoAddResult(
        project_id=str(project["id"]),
        entry=entry,
        auth=AuthReport(
            configured=provider != "local",
            detail=(
                f"using {origin}"
                if provider != "local"
                else "linked folder has no origin remote"
            ),
        ),
    )


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
    if not layout.is_project:
        raise AdoptError(
            "this project uses the legacy flat layout; repositories can only "
            "be added to a project"
        )
    if layout.metadata().get("mode") != "brownfield":
        raise AdoptError(
            "adopting an existing repository into an existing project is "
            "supported for brownfield projects; use 'repo create' for a new "
            "repository or '/adopt' for a new project"
        )
    if layout.is_linked:
        return _add_linked_repository(
            settings,
            ledger,
            project,
            layout,
            url,
            repo_id,
            depends_on,
            role,
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


NEW_REPO_README = """# {name}

{description}

Managed by Forgel.
"""

NEW_REPO_FORGEL = """# FORGEL.md

Native project instructions for {name}. Forgel reads this file first, then
`AGENTS.md`.

## Rules

- This repository belongs to a Forgel project; changes go through the project
  workflow.
- Recorded assumptions and change reports live in the project control
  repository.
- Autonomy: finish reversible pre-release work without asking, record
  assumptions, and stop only for a material fork, an irreversible or
  production action, or missing access.
"""

NEW_REPO_AGENTS = """# AGENTS.md

Canonical instructions for agents working on {name}.

## Rules

- Work autonomously: pre-release work proceeds without confirmation. Record
  assumptions in the task and report. Ask only for a material fork, an
  irreversible or production action, or missing access. Finish the result,
  show the evidence, then rework on feedback.
- Never weaken a test to make it pass; fix the product or the test's premise.
- Do not add tool attribution lines to commits or pull requests.
"""


@dataclass(frozen=True)
class RepoCreateResult:
    project_id: str
    entry: dict[str, Any]
    url: str
    created: bool


def _github_client(
    settings: Settings,
    prefer: str,
    auth: AuthToken | None,
    api: Any | None,
) -> tuple[Any, AuthToken]:
    auth_client: GithubAuth | None = None
    if auth is None:
        auth_client = GithubAuth(settings.home)
        auth = auth_client.resolve(prefer)
    api_base = (
        auth_client.api_base
        if auth_client is not None
        else DEFAULT_API_BASE
    )
    client = api or GithubAPI(auth.token, api_base=api_base)
    return client, auth


def _git_config(layout: ProjectLayout) -> GitConfig:
    try:
        config = load_project_config(layout.control)
    except ConfigError:
        config = None
    return config.git if config is not None else GitConfig()


def _init_local_repository(
    local: Path, repo_id: str, description: str
) -> Path:
    if local.exists() and any(local.iterdir()):
        raise AdoptError(f"local repository already exists: {local}")
    ensure_dir(local)
    write_text(
        local / "README.md",
        NEW_REPO_README.format(
            name=repo_id, description=description or "Created by Forgel."
        ),
    )
    write_text(local / "FORGEL.md", NEW_REPO_FORGEL.format(name=repo_id))
    write_text(local / "AGENTS.md", NEW_REPO_AGENTS.format(name=repo_id))
    write_text(local / ".gitignore", GITIGNORE)
    result = subprocess.run(
        ["git", "init", "-q", "-b", "main"],
        cwd=local,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AdoptError(
            "git init failed: " + (result.stderr or result.stdout).strip()
        )
    try:
        git_ops.commit_all(local, f"Initialize {repo_id}")
    except git_ops.GitOperationError as exc:
        raise AdoptError(str(exc)) from exc
    return local


def _project_owner(layout: ProjectLayout) -> str:
    """The single GitHub owner already used by the project's repositories."""

    owners = {
        match.group(1)
        for entry in entries(layout)
        if (
            match := re.search(
                r"github\.com[/:]([^/]+)/", str(entry.get("url") or "")
            )
        )
    }
    return next(iter(owners)) if len(owners) == 1 else ""


def _resolve_owner(
    layout: ProjectLayout,
    client: Any,
    auth: AuthToken,
    configured: str,
    org: str,
) -> str:
    owner = (
        org
        or configured
        or os.environ.get("FORGEL_GITHUB_ORG", "")
        or _project_owner(layout)
    ).strip()
    if owner:
        return owner
    if auth.kind != "pat":
        raise AdoptError(
            "set [git] org or --org when using GitHub App credentials"
        )
    user = client.user()
    login = str(user.get("login", "")).strip()
    if not login:
        raise AdoptError(
            "cannot determine the GitHub owner; set [git] org or --org"
        )
    return login


def _create_remote(
    client: Any,
    name: str,
    owner: str,
    private: bool,
    description: str,
) -> tuple[str, str]:
    try:
        data = client.create_repo(
            owner, name, private=private, description=description
        )
    except GithubAPIError as exc:
        if exc.status == 422:
            raise AdoptError(
                f"GitHub repository {owner}/{name} already exists; use "
                f"/repo add https://github.com/{owner}/{name}.git to adopt it"
            ) from exc
        raise AdoptError(str(exc)) from exc
    full_name = str(data.get("full_name") or f"{owner}/{name}")
    url = str(
        data.get("clone_url") or f"https://github.com/{full_name}.git"
    )
    return full_name, url


def _push_repository(local: Path, token: AuthToken, branch: str) -> None:
    try:
        git_ops.push(local, branch, token.token)
    except git_ops.GitOperationError as exc:
        raise AdoptError(str(exc)) from exc


def _write_repo_doc(layout: ProjectLayout, entry: dict[str, Any]) -> None:
    path = layout.artifact(f"docs/program/repos/{entry['id']}.md")
    edges = ", ".join(entry.get("depends_on", [])) or "none"
    write_text(
        path,
        f"""# Repository: {entry['id']}

- Role: {entry.get('role', 'application')}
- Provider: {entry.get('provider', '')}
- URL: {entry.get('url') or '—'}
- Depends on: {edges}
""",
    )


def _update_entry(
    layout: ProjectLayout, entry: dict[str, Any]
) -> None:
    updated = [
        entry if item["id"] == entry["id"] else item
        for item in entries(layout)
    ]
    set_entries(layout, updated)


def create_repository(
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
    auth: AuthToken | None = None,
) -> RepoCreateResult:
    """Create a repository on GitHub and register it in the project."""

    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_project:
        raise AdoptError(
            "this project uses the legacy flat layout; repositories can only "
            "be created in a project"
        )
    selected_id = slugify_repo_id(repo_id)
    if not selected_id:
        raise AdoptError("repository id must not be empty")
    known = {entry["id"] for entry in entries(layout)}
    if selected_id in known:
        raise AdoptError(f"repository id already exists: {selected_id}")
    dependencies = [
        item.strip() for item in (depends_on or []) if item.strip()
    ]
    if selected_id in dependencies:
        raise AdoptError("a repository cannot depend on itself")
    try:
        validate_dependencies(known, dependencies)
    except ValueError as exc:
        raise AdoptError(str(exc)) from exc
    if layout.is_linked:
        if path.strip():
            local = Path(path).expanduser().resolve()
        else:
            local = (layout.root.parent / selected_id).resolve()
    else:
        local = layout.repo_path(selected_id)
    if local.exists() and any(local.iterdir()):
        raise AdoptError(f"local repository already exists: {local}")

    git_config = _git_config(layout)
    client, token = _github_client(
        settings, git_config.auth, auth, api
    )
    owner = _resolve_owner(layout, client, token, git_config.org, org)
    full_name, url = _create_remote(
        client, selected_id, owner, private, description
    )

    _init_local_repository(local, selected_id, description)
    try:
        git_ops.ensure_remote(local, url)
    except git_ops.GitOperationError as exc:
        raise AdoptError(str(exc)) from exc
    entry = {
        "id": selected_id,
        "role": role.strip() or "application",
        "provider": "github",
        "url": url,
        "depends_on": dependencies,
    }
    if layout.is_linked:
        entry["path"] = str(local)
    add_entry(layout, entry)
    _write_repo_doc(layout, entry)
    write_program(
        layout,
        str(project["name"]),
        str(project.get("recipe_id") or ""),
    )
    _commit_control(layout, f"Create repository {selected_id}")
    _push_repository(local, token, git_ops.current_branch(local) or "main")
    _event(
        ledger,
        str(project["id"]),
        "repo_create",
        [
            _artifact_ref(layout, "program.yaml"),
            _artifact_ref(layout, f"docs/program/repos/{selected_id}.md"),
        ],
        {
            "repo": selected_id,
            "provider": "github",
            "url": url,
            "full_name": full_name,
            "depends_on": dependencies,
        },
    )
    return RepoCreateResult(
        project_id=str(project["id"]),
        entry=entry,
        url=url,
        created=True,
    )


def publish_repository(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str,
    org: str = "",
    private: bool = True,
    description: str = "",
    api: Any | None = None,
    auth: AuthToken | None = None,
) -> RepoCreateResult:
    """Create the GitHub remote for an existing local repository and push it."""

    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_project:
        raise AdoptError(
            "this project uses the legacy flat layout; publishing requires a "
            "project"
        )
    entry = next(
        (item for item in entries(layout) if item["id"] == repo_id), None
    )
    if entry is None:
        raise AdoptError(f"unknown repository {repo_id!r}")
    if "github.com" in str(entry.get("url", "")):
        raise AdoptError(
            f"repository {repo_id} already has a GitHub remote: {entry['url']}"
        )
    local = layout.repo_path(repo_id)
    if not (local / ".git").exists():
        raise AdoptError(f"repository {repo_id} has no git history")

    git_config = _git_config(layout)
    client, token = _github_client(
        settings, git_config.auth, auth, api
    )
    owner = _resolve_owner(layout, client, token, git_config.org, org)
    remote_name = repo_id
    if layout.is_linked and repo_id == "main":
        remote_name = slugify_repo_id(str(project["name"]))
    full_name, url = _create_remote(
        client, remote_name, owner, private, description
    )
    git_ops.ensure_remote(local, url)
    _push_repository(local, token, git_ops.current_branch(local) or "main")
    entry = dict(entry)
    entry["provider"] = "github"
    entry["url"] = url
    _update_entry(layout, entry)
    _write_repo_doc(layout, entry)
    write_program(
        layout,
        str(project["name"]),
        str(project.get("recipe_id") or ""),
    )
    _commit_control(layout, f"Publish repository {repo_id}")
    _event(
        ledger,
        str(project["id"]),
        "repo_publish",
        [
            _artifact_ref(layout, "program.yaml"),
            _artifact_ref(layout, f"docs/program/repos/{repo_id}.md"),
        ],
        {
            "repo": repo_id,
            "url": url,
            "full_name": full_name,
        },
    )
    return RepoCreateResult(
        project_id=str(project["id"]),
        entry=entry,
        url=url,
        created=True,
    )




@dataclass(frozen=True)
class ControlExtractResult:
    project_id: str
    control: str
    moved: list[str]


def extract_control(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    path: str = "",
) -> ControlExtractResult:
    """Move a linked project's state into a separate repository."""

    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_linked:
        raise AdoptError(
            "control extraction is only available for linked projects"
        )
    if layout.control.resolve() != layout.root.resolve():
        raise AdoptError("the project state is already in a separate repository")
    target = (
        Path(path).expanduser().resolve()
        if path.strip()
        else (
            layout.root.parent
            / (slugify_repo_id(str(project["name"])) + "-program")
        ).resolve()
    )
    if target.exists() and any(target.iterdir()):
        raise AdoptError(f"target directory is not empty: {target}")
    ensure_dir(target)
    moved: list[str] = []
    for name in CONTROL_PATHS:
        if name == ".gitignore":
            continue
        source = layout.root / name
        if not source.exists():
            continue
        shutil.move(str(source), str(target / name))
        moved.append(name)
    try:
        git_ops.commit_paths(
            layout.root,
            moved,
            f"Move project state to {target.name}",
        )
    except git_ops.GitOperationError:
        pass
    update_metadata(layout, {"control": str(target)})
    layout = ProjectLayout.detect(layout.root)
    write_program(
        layout,
        str(project["name"]),
        str(project.get("recipe_id") or ""),
    )
    _control_commit(target, f"Extract project state for {project['name']}")
    try:
        _maybe_create_remote(
            settings,
            target,
            f"{project['name']} program",
            "Forgel project state",
        )
    except Exception:  # noqa: BLE001 - a local control repository is valid
        pass
    _event(
        ledger,
        str(project["id"]),
        "control_extract",
        [_artifact_ref(layout, "program.yaml")],
        {"control": str(target), "moved": moved},
    )
    return ControlExtractResult(
        project_id=str(project["id"]),
        control=str(target),
        moved=moved,
    )


def set_dependencies(
    settings: Settings,
    ledger: Ledger,
    project: dict[str, Any],
    repo_id: str,
    depends_on: list[str],
) -> dict[str, Any]:
    """Replace the dependency edges of a repository in an existing project."""

    layout = ProjectLayout.detect(project["workspace"])
    if not layout.is_project:
        raise AdoptError(
            "dependency edges can only be edited in a project"
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
    _commit_control(layout, f"Link repository {repo_id}")
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
