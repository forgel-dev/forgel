"""Reconcile external changes with the Forgel process.

Forgel never regenerates and never overwrites external work. ``sync`` detects
changes since the generated baseline, records them, and starts a new ledger
generation from a chosen stage.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import read_json, write_text
from .ledger import Ledger
from .state import validate_stage

IGNORED_PARTS = {"__pycache__", "node_modules", ".git", ".forgel"}
IGNORED_PATHS = {
    "docs/program/artifact-manifest.json",
    "docs/program/external-changes.md",
}


class SyncError(RuntimeError):
    """Raised when a project cannot be reconciled."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def detect_external_changes(workspace: Path) -> dict[str, Any]:
    if (workspace / ".git").exists():
        return _detect_git(workspace)
    return _detect_manifest(workspace)


def _write_report(workspace: Path, report: dict[str, Any]) -> Path:
    lines = [
        "# External Changes",
        "",
        f"- Detected: {report['detected_at']}",
        f"- Kind: `{report['kind']}`",
        f"- Baseline: `{report['baseline'] or 'n/a'}`",
        f"- Files changed: {report['count']}",
        f"- Re-run from: `{report['from_stage']}`",
        f"- Generation: {report['generation']}",
        f"- Started: {'yes' if report['started'] else 'no'}",
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

    path = workspace / "docs" / "program" / "external-changes.md"
    write_text(path, "\n".join(lines).rstrip() + "\n")
    return path


def sync_project(
    workspace: Path,
    ledger: Ledger,
    project_id: str,
    from_stage: str = "review",
    force: bool = False,
) -> dict[str, Any]:
    """Detect external changes and start a new generation when needed."""

    validate_stage(from_stage)
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
    }

    if changes["count"] == 0 and not force:
        _write_report(workspace, report)
        return report

    generation = ledger.start_generation(project_id, from_stage)
    report["generation"] = generation
    report["started"] = True
    path = _write_report(workspace, report)
    ledger.append_event(
        project_id,
        "sync",
        status="completed",
        artifact_refs=[str(path.relative_to(workspace))],
        payload={
            "files_changed": changes["count"],
            "from_stage": from_stage,
            "kind": changes["kind"],
        },
        generation=generation,
    )
    return report
