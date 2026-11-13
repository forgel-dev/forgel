"""Reconcile external changes with the Forgel process.

Forgel never regenerates and never overwrites external work. ``sync`` detects
changes since the generated baseline, records them, and asks for a decision.
``reconcile`` records the decision and starts a new ledger generation from a
chosen stage.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import read_json, write_text
from .layout import ProjectLayout
from .ledger import Ledger
from .state import validate_stage

IGNORED_PARTS = {"__pycache__", "node_modules", ".git", ".forgel"}
IGNORED_PATHS = {
    "docs/program/artifact-manifest.json",
    "docs/program/external-changes.md",
    "docs/program/reconciliation.md",
}
REQUIRED_PATHS = {
    "api/app.py",
    "web/index.html",
    "e2e/check.py",
    "Dockerfile",
    "docker/docker-compose.qa.yml",
    "qa/runner.mjs",
    "qa/package.json",
    "qa/scenarios/hello_web.mjs",
}
KNOWN_PREFIXES = {"api", "web", "e2e", "qa", "docker", "infra"}
KNOWN_ROOT_FILES = {
    "Dockerfile",
    ".dockerignore",
    ".gitignore",
    "program.yaml",
    "FORGEL.md",
    "AGENTS.md",
}
VALID_DECISIONS = {"accept", "fix", "rollback", "ignore"}


class SyncError(RuntimeError):
    """Raised when a project cannot be reconciled."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _layout(workspace: Path) -> ProjectLayout:
    return ProjectLayout.detect(workspace)


def _docs(workspace: Path) -> Path:
    return _layout(workspace).artifact("docs/program")


def _ref(workspace: Path, path: Path) -> str:
    return str(path.relative_to(_layout(workspace).root))


def _required_paths(workspace: Path) -> set[str]:
    layout = _layout(workspace)
    if not layout.is_container:
        return set(REQUIRED_PATHS)
    control = layout.control.relative_to(layout.root).as_posix()
    return {
        f"{control}/program.yaml",
        f"{control}/forgel.toml",
        f"{control}/FORGEL.md",
        f"{control}/AGENTS.md",
        layout.repo_ref("api", "app.py"),
        layout.repo_ref("web", "index.html"),
        layout.repo_ref("e2e", "check.py"),
        layout.repo_ref("infra", "Dockerfile"),
        layout.repo_ref("infra", "docker-compose.qa.yml"),
        layout.repo_ref("e2e", "qa/runner.mjs"),
        layout.repo_ref("e2e", "qa/package.json"),
        layout.repo_ref("e2e", "qa/scenarios/hello_web.mjs"),
    }


def _docs_prefix(workspace: Path) -> str:
    return _docs(workspace).relative_to(_layout(workspace).root).as_posix()


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )


def _filter_paths(paths: set[str]) -> set[str]:
    return {path for path in paths if path and path not in IGNORED_PATHS}


def _manifest_files(workspace: Path) -> set[str]:
    path = workspace / "docs" / "program" / "artifact-manifest.json"
    if not path.exists():
        return set()
    return set(read_json(path).get("files", {}))


def _detect_git(workspace: Path) -> dict[str, Any]:
    status = _git(workspace, "status", "--porcelain")
    tag = _git(workspace, "rev-parse", "--verify", "forgel-baseline")
    baseline = ""
    if tag.returncode == 0 and tag.stdout.strip():
        baseline = tag.stdout.strip()
    else:
        root = _git(workspace, "rev-list", "--max-parents=0", "HEAD")
        if root.returncode == 0 and root.stdout.strip():
            baseline = root.stdout.strip().splitlines()[0]

    files: set[str] = set()
    for line in status.stdout.splitlines():
        if len(line) <= 3:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            files.update({old.strip('"'), new.strip('"')})
        else:
            files.add(path)

    diffstat = ""
    commits = ""
    if baseline:
        diffstat = _git(workspace, "diff", "--stat", baseline).stdout.strip()
        names = _git(workspace, "diff", "--name-status", baseline)
        for line in names.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                files.add(parts[-1].strip())
                if len(parts) >= 3:
                    files.add(parts[-2].strip())
        commits = _git(
            workspace, "log", "--oneline", f"{baseline}..HEAD"
        ).stdout.strip()

    files = _filter_paths(files)
    return {
        "kind": "git",
        "baseline": baseline,
        "files": sorted(files),
        "count": len(files),
        "status": status.stdout.strip(),
        "diffstat": diffstat,
        "commits": commits,
        "note": "",
    }


def _current_hashes(workspace: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        name = relative.as_posix()
        if name in IGNORED_PATHS:
            continue
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _detect_manifest(workspace: Path) -> dict[str, Any]:
    manifest_path = workspace / "docs" / "program" / "artifact-manifest.json"
    if not manifest_path.exists():
        return {
            "kind": "manifest",
            "baseline": "",
            "files": [],
            "count": 0,
            "status": "",
            "diffstat": "",
            "commits": "",
            "note": "No artifact manifest found; external changes cannot be detected.",
        }

    manifest = read_json(manifest_path)
    previous = manifest.get("files", {})
    current = _current_hashes(workspace)
    changed = set(previous) ^ set(current)
    changed.update(
        name for name, digest in current.items() if previous.get(name) != digest
    )
    files = sorted(changed)
    return {
        "kind": "manifest",
        "baseline": "artifact-manifest",
        "files": files,
        "count": len(files),
        "status": "",
        "diffstat": "",
        "commits": "",
        "note": "",
    }


def _detect_container(layout: ProjectLayout) -> dict[str, Any]:
    files: set[str] = set()
    diffstat: list[str] = []
    commits: list[str] = []
    statuses: list[str] = []
    for target in layout.git_roots():
        info = _detect_git(target)
        prefix = target.relative_to(layout.root).as_posix()
        files.update(f"{prefix}/{name}" for name in info["files"])
        if info["diffstat"]:
            diffstat.append(f"## {prefix}\n{info['diffstat']}")
        if info["commits"]:
            commits.append(f"## {prefix}\n{info['commits']}")
        if info["status"]:
            statuses.append(f"## {prefix}\n{info['status']}")
    return {
        "kind": "git",
        "baseline": "multi-repo",
        "files": sorted(files),
        "count": len(files),
        "status": "\n".join(statuses),
        "diffstat": "\n\n".join(diffstat),
        "commits": "\n\n".join(commits),
        "note": "",
    }


def detect_external_changes(workspace: Path) -> dict[str, Any]:
    layout = _layout(workspace)
    if layout.is_container:
        if layout.git_roots():
            return _detect_container(layout)
        return _detect_manifest(layout.control)
    if (workspace / ".git").exists():
        return _detect_git(workspace)
    return _detect_manifest(workspace)


def analyze_changes(workspace: Path, changes: dict[str, Any]) -> dict[str, list[str]]:
    """Classify changed files against explicit constraints and the generated baseline."""

    layout = _layout(workspace)
    manifest = _manifest_files(layout.control)
    required = _required_paths(workspace)
    docs_prefix = _docs_prefix(workspace)
    changed = set(changes.get("files", []))
    violations: list[str] = []
    requirements: list[str] = []
    documented: list[str] = []
    undocumented: list[str] = []
    deletions: list[str] = []

    def is_requirements_path(path: str) -> bool:
        return path.startswith(docs_prefix + "/") and (
            path.endswith("requirements.json")
            or "/features/" in path
            or path.endswith("change-sets.json")
        )

    def is_documented(path: str) -> bool:
        if path in manifest or path in required:
            return True
        if layout.is_container:
            return path.startswith("repos/") or path.startswith(
                layout.control.relative_to(layout.root).as_posix() + "/"
            )
        return (
            path.split("/", 1)[0] in KNOWN_PREFIXES
            or path in KNOWN_ROOT_FILES
        )

    for path in sorted(changed):
        if not (layout.root / path).exists():
            deletions.append(path)
            if path in required:
                violations.append(f"Required file missing: `{path}`")
            continue

        if is_requirements_path(path):
            requirements.append(path)
        elif is_documented(path):
            documented.append(path)
        else:
            undocumented.append(path)

    for required_path in sorted(required):
        if not (layout.root / required_path).exists() and required_path not in deletions:
            violations.append(f"Required file missing: `{required_path}`")

    return {
        "violations": violations,
        "requirements": requirements,
        "documented": documented,
        "undocumented": undocumented,
        "deletions": deletions,
    }


def _write_external_report(workspace: Path, report: dict[str, Any]) -> Path:
    lines = [
        "# External Changes",
        "",
        f"- Detected: {report['detected_at']}",
        f"- Kind: `{report['kind']}`",
        f"- Baseline: `{report['baseline'] or 'n/a'}`",
        f"- Files changed: {report['count']}",
        f"- Re-run from: `{report['from_stage']}`",
        f"- Generation: {report['generation']}",
        "",
        "## Note",
        "",
        "Forgel reconciles external changes; it does not regenerate or overwrite them.",
    ]
    if report.get("note"):
        lines += ["", report["note"]]
    if report["files"]:
        lines += ["", "## Files", "", *[f"- `{name}`" for name in report["files"]]]
    if report["commits"]:
        lines += ["", "## Commits Since Baseline", "", "```", report["commits"], "```"]
    if report["diffstat"]:
        lines += ["", "## Diffstat", "", "```", report["diffstat"], "```"]
    if report["status"]:
        lines += ["", "## Working Tree Status", "", "```", report["status"], "```"]

    path = _docs(workspace) / "external-changes.md"
    write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def _write_reconciliation(
    workspace: Path,
    changes: dict[str, Any],
    analysis: dict[str, list[str]],
    generation: int,
) -> Path:
    def bullets(items: list[str], template: str) -> str:
        return "\n".join(template.format(item=item) for item in items) or "_None._"

    text = f"""# Reconciliation

- Status: pending
- Detected: {_utcnow()}
- Detected at generation: {generation}
- External files: {changes['count']}
- Decision: —

## Findings

No requirements document exists for these changes. Validation is limited to
explicit constraints and the generated file manifest; an intentional change can
still look like a violation.

### Violations

{bullets(analysis['violations'], '- {item}')}

### Requirements Changed Externally

{bullets(analysis['requirements'], '- `{item}`')}

### Documented Modifications

{bullets(analysis['documented'], '- `{item}`')}

### Undocumented Changes

{bullets(analysis['undocumented'], '- `{item}`')}

### Deletions

{bullets(analysis['deletions'], '- `{item}`')}

## Decision Required

Choose one:

- `accept` — accept and document the change in the feature spec.
- `fix` — keep it as a defect; the pipeline will require a fix before continuing.
- `rollback` — restore the changed files from the generated baseline.
- `ignore` — record the change and continue without documenting it.

Run:

```
forgel reconcile <project-id> --decision accept|fix|rollback|ignore [--notes "..."]
```
"""
    path = _docs(workspace) / "reconciliation.md"
    write_text(path, text)
    return path


def _feature_spec(workspace: Path) -> Path | None:
    features = sorted((_docs(workspace) / "features").glob("*.md"))
    return features[-1] if features else None


def _append_revision(spec: Path, notes: str, files: list[str]) -> None:
    description = notes or "External change accepted"
    if files:
        description += ": " + ", ".join(f"`{name}`" for name in files)
    description = description.replace("|", "\\|")
    row = f"| 1.1.0 | {datetime.now(timezone.utc).date()} | Forgel reconcile | {description} |"
    lines = spec.read_text(encoding="utf-8").rstrip().splitlines()
    insert_at = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].startswith("|"):
            insert_at = index + 1
            break
    lines.insert(insert_at, row)
    write_text(spec, "\n".join(lines) + "\n")


def _accept_changes(workspace: Path, changes: dict[str, Any], notes: str) -> None:
    spec = _feature_spec(workspace)
    if spec is None:
        raise SyncError("No feature spec found to document the change")
    files = changes["files"]
    section = [
        "",
        f"## External Change: {_utcnow()}",
        "",
        f"- Files: {', '.join(f'`{name}`' for name in files) or 'none'}",
        f"- Notes: {notes or '—'}",
        "- Decision: accepted and documented.",
        "",
    ]
    text = spec.read_text(encoding="utf-8")
    marker = "## Revision History"
    if marker in text:
        before, after = text.split(marker, 1)
        text = before.rstrip() + "\n" + "\n".join(section) + marker + after
    else:
        text = text.rstrip() + "\n" + "\n".join(section)
    write_text(spec, text.rstrip() + "\n")
    _append_revision(spec, notes, files)


def _mark_fix(path: Path, analysis: dict[str, list[str]], notes: str) -> None:
    section = [
        "",
        "## Fix Request",
        "",
        f"- Notes: {notes or '—'}",
        "- Violations:",
        *[f"  - {item}" for item in analysis["violations"]],
        "- Undocumented changes:",
        *[f"  - `{item}`" for item in analysis["undocumented"]],
        "",
    ]
    text = path.read_text(encoding="utf-8").rstrip()
    write_text(path, text + "\n" + "\n".join(section) + "\n")


def _target_for(
    layout: ProjectLayout, path: str
) -> tuple[Path, str]:
    if not layout.is_container:
        return layout.root, path
    control = layout.control.relative_to(layout.root).as_posix()
    if path == control:
        return layout.control, ""
    if path.startswith(control + "/"):
        return layout.control, path[len(control) + 1 :]
    parts = path.split("/")
    if len(parts) >= 3 and parts[0] == "repos":
        return layout.repo_path(parts[1]), "/".join(parts[2:])
    return layout.root, path


def _rollback(workspace: Path, changes: dict[str, Any]) -> None:
    layout = _layout(workspace)
    trash = layout.root / ".forgel" / "trash" / _utcnow().replace(":", "-")
    restored = False

    for path in changes["files"]:
        target, relative = _target_for(layout, path)
        if not relative or not (target / ".git").exists():
            continue
        baseline = _git(target, "rev-parse", "--verify", "forgel-baseline")
        if baseline.returncode != 0 or not baseline.stdout.strip():
            continue
        base = baseline.stdout.strip()
        restored = True
        in_baseline = _git(target, "cat-file", "-e", f"{base}:{relative}")
        if in_baseline.returncode == 0:
            _git(target, "restore", "--source", base, "--", relative)
        elif (layout.root / path).exists():
            destination = trash / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            (layout.root / path).replace(destination)

    if not restored:
        raise SyncError("Rollback requires a git baseline (tag forgel-baseline)")

    for required in sorted(_required_paths(workspace)):
        if (layout.root / required).exists():
            continue
        target, relative = _target_for(layout, required)
        if not relative or not (target / ".git").exists():
            continue
        base = _git(target, "rev-parse", "--verify", "forgel-baseline")
        if base.returncode != 0 or not base.stdout.strip():
            continue
        _git(
            target, "restore", "--source", base.stdout.strip(), "--", relative
        )


def _update_reconciliation(
    path: Path,
    status: str,
    decision: str,
    generation: int,
    notes: str,
) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("- Status: pending", f"- Status: {status}", 1)
    text = text.replace("- Status: fix_required", f"- Status: {status}", 1)
    text = text.replace("- Decision: —", f"- Decision: `{decision}`", 1)
    text = text.rstrip() + f"""

## Decision

- Decision: `{decision}`
- Generation: {generation}
- Notes: {notes or "—"}
"""
    write_text(path, text)


def _reconciliation_status(path: Path) -> str:
    if not path.exists():
        return "none"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Status:"):
            return line.split(":", 1)[1].strip()
    return "none"


def reconciliation_status(workspace: Path) -> str:
    """Return the recorded reconciliation status for a project workspace."""

    return _reconciliation_status(_docs(workspace) / "reconciliation.md")


def reconciliation_status_path(path: Path) -> str:
    """Return the status from an explicit reconciliation file."""

    return _reconciliation_status(path)


def sync_project(
    workspace: Path,
    ledger: Ledger,
    project_id: str,
    from_stage: str = "review",
    force: bool = False,
    decision: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Detect external changes, record them, and ask for a decision."""

    validate_stage(from_stage)
    if decision is not None and decision not in VALID_DECISIONS:
        raise SyncError(f"Unknown decision: {decision}")
    project = ledger.get_project(project_id)
    if project is None:
        raise SyncError(f"Unknown project: {project_id}")

    changes = detect_external_changes(workspace)
    current_generation = ledger.current_generation(project_id)
    report: dict[str, Any] = {
        "detected_at": _utcnow(),
        "kind": changes["kind"],
        "baseline": changes["baseline"],
        "files": changes["files"],
        "count": changes["count"],
        "status": changes["status"],
        "diffstat": changes["diffstat"],
        "commits": changes["commits"],
        "note": changes.get("note", ""),
        "from_stage": from_stage,
        "generation": current_generation,
        "started": False,
        "pending": False,
        "decision": decision,
    }
    _write_external_report(workspace, report)

    if changes["count"] == 0:
        if not force:
            return report
        generation = ledger.start_generation(project_id, from_stage)
        report["generation"] = generation
        report["started"] = True
        return report

    analysis = analyze_changes(workspace, changes)
    report["analysis"] = analysis
    reconciliation = _write_reconciliation(
        workspace, changes, analysis, current_generation
    )

    if decision is not None:
        result = reconcile_project(
            workspace,
            ledger,
            project_id,
            decision=decision,
            notes=notes,
            from_stage=from_stage,
        )
        result["external_changes"] = report
        return result

    report["pending"] = True
    report["reconciliation"] = _ref(workspace, reconciliation)
    return report


def reconcile_project(
    workspace: Path,
    ledger: Ledger,
    project_id: str,
    decision: str,
    notes: str = "",
    from_stage: str = "review",
) -> dict[str, Any]:
    """Apply a user's decision to a pending reconciliation."""

    validate_stage(from_stage)
    if decision not in VALID_DECISIONS:
        raise SyncError(f"Unknown decision: {decision}")
    project = ledger.get_project(project_id)
    if project is None:
        raise SyncError(f"Unknown project: {project_id}")

    reconciliation = _docs(workspace) / "reconciliation.md"
    status = _reconciliation_status(reconciliation)
    if status not in {"pending", "fix_required"}:
        raise SyncError(
            f"No pending reconciliation for {project_id} (status: {status})"
        )

    changes = detect_external_changes(workspace)
    analysis = analyze_changes(workspace, changes)

    if decision == "accept":
        _accept_changes(workspace, changes, notes)
        target_status = "accepted"
    elif decision == "fix":
        _mark_fix(reconciliation, analysis, notes)
        target_status = "fix_required"
    elif decision == "rollback":
        _rollback(workspace, changes)
        target_status = "rolled_back"
    else:
        target_status = "ignored"

    generation = ledger.start_generation(project_id, from_stage)
    _update_reconciliation(
        reconciliation, target_status, decision, generation, notes
    )
    ledger.append_event(
        project_id,
        "reconcile",
        status="completed",
        artifact_refs=[
            _ref(workspace, reconciliation),
            _ref(workspace, _docs(workspace) / "external-changes.md"),
        ],
        payload={
            "decision": decision,
            "files_changed": changes["count"],
            "from_stage": from_stage,
        },
        generation=generation,
    )
    return {
        "started": True,
        "pending": False,
        "decision": decision,
        "generation": generation,
        "from_stage": from_stage,
        "status": target_status,
        "files": changes["files"],
    }
