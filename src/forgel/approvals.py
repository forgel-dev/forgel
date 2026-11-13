"""Human approval gates.

Approvals are generation-scoped: approving generation 1 never approves work
produced in generation 2. Every decision is written to the ledger and appended
to ``docs/program/approvals.md`` so the committed history carries the audit
trail. The production gate additionally requires an explicit compliance
acknowledgement; the human who approves carries that responsibility.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import write_json, write_text
from .layout import ProjectLayout
from .ledger import Ledger

SCOPES: tuple[str, ...] = ("staging", "production")
DECISIONS: tuple[str, ...] = ("approved", "rejected")


class ApprovalError(RuntimeError):
    """Raised when an approval is not valid."""


def _short_sha(target: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(target),
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def release_sha(workspace: Path) -> str:
    """Return the short SHA of the current release candidate, if there is one."""

    layout = ProjectLayout.detect(workspace)
    if not layout.is_container:
        return _short_sha(layout.root) if (layout.root / ".git").exists() else ""
    digest, _repos = release_state(workspace)
    return digest


def release_state(workspace: Path) -> tuple[str, dict[str, str]]:
    """Return a release id and the per-repository SHAs it covers.

    A container has one git repository per code repo plus the control repo, so
    no single SHA can name the release. The digest binds the approval to every
    repository state; the mapping is written to
    ``docs/program/releases/g<generation>.json``.
    """

    layout = ProjectLayout.detect(workspace)
    if not layout.is_container:
        sha = _short_sha(layout.root) if (layout.root / ".git").exists() else ""
        return sha, ({"main": sha} if sha else {})
    repos: dict[str, str] = {}
    for target in layout.git_targets():
        if not (target / ".git").exists():
            continue
        sha = _short_sha(target)
        if not sha:
            continue
        name = (
            "program"
            if target == layout.control
            else f"repos/{target.name}"
        )
        repos[name] = sha
    if not repos:
        return "", {}
    digest = hashlib.sha256(
        "\n".join(f"{name}:{sha}" for name, sha in sorted(repos.items())).encode()
    ).hexdigest()[:12]
    return digest, repos


def latest_approval(
    ledger: Ledger,
    project_id: str,
    scope: str,
    generation: int | None = None,
) -> dict[str, Any] | None:
    return ledger.latest_approval(project_id, scope, generation)


def is_approved(
    ledger: Ledger, project_id: str, scope: str, generation: int | None = None
) -> bool:
    approval = latest_approval(ledger, project_id, scope, generation)
    return approval is not None and approval["decision"] == "approved"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ") or "—"


def _append_artifact(workspace: Path, record: dict[str, Any]) -> Path:
    layout = ProjectLayout.detect(workspace)
    path = layout.artifact("docs/program/approvals.md")
    header = """# Approvals

Human decisions recorded by the approval gate. The ledger is the runtime
source; this file is the committed audit trail. Approvals are scoped to one
generation. For container projects the release is a digest; the per-repository
SHAs are in `docs/program/releases/g<generation>.json`.

| Time | Scope | Generation | Decision | Actor | Compliance | Release | Notes |
|---|---|---|---|---|---|---|---|
"""
    text = path.read_text(encoding="utf-8") if path.exists() else header
    if not text.endswith("\n"):
        text += "\n"
    compliance = "yes" if record["compliance_ack"] else "no"
    row = (
        f"| {record['created_at']} | {record['scope']} | {record['generation']} "
        f"| {record['decision']} | {_cell(record['actor'])} | {compliance} "
        f"| {_cell(record['release_sha'])} | {_cell(record['notes'])} |"
    )
    write_text(path, text + row + "\n")
    return path


def record_approval(
    ledger: Ledger,
    project_id: str,
    scope: str,
    actor: str,
    decision: str = "approved",
    compliance_ack: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    """Record a human decision for the current generation."""

    project = ledger.get_project(project_id)
    if project is None:
        raise ApprovalError(f"unknown project {project_id}")
    if scope not in SCOPES:
        raise ApprovalError(f"unknown approval scope {scope!r}")
    if decision not in DECISIONS:
        raise ApprovalError(f"unknown decision {decision!r}")
    if scope == "production" and decision == "approved" and not compliance_ack:
        raise ApprovalError(
            "production approval requires the compliance acknowledgement"
        )

    generation = ledger.current_generation(project_id)
    state = ledger.checkpoint_state(project_id)
    stage = state[0] if state is not None else None
    if scope == "staging" and stage != "approval":
        raise ApprovalError(
            "staging decisions are only valid while the release is at the "
            "approval gate"
        )
    if scope == "production" and stage != "done":
        raise ApprovalError(
            "production decisions require a completed release"
        )
    if scope == "production" and decision == "approved":
        if not is_approved(ledger, project_id, "staging", generation):
            raise ApprovalError("staging must be approved before production")

    latest = latest_approval(ledger, project_id, scope, generation)
    if latest is not None and latest["decision"] == decision:
        return latest

    workspace = Path(project["workspace"])
    layout = ProjectLayout.detect(workspace)
    release_id, repos = release_state(workspace)
    artifact_refs = [
        str(layout.artifact("docs/program/approvals.md").relative_to(layout.root))
    ]
    if layout.is_container and repos:
        manifest = layout.artifact(
            f"docs/program/releases/g{generation}.json"
        )
        write_json(
            manifest,
            {
                "generation": generation,
                "digest": release_id,
                "repos": repos,
                "recorded_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
            },
        )
        artifact_refs.append(str(manifest.relative_to(layout.root)))

    record = ledger.add_approval(
        project_id=project_id,
        generation=generation,
        scope=scope,
        decision=decision,
        actor=actor,
        compliance_ack=compliance_ack,
        notes=notes,
        release_sha=release_id,
    )
    _append_artifact(workspace, record)
    ledger.append_event(
        project_id,
        "approval",
        status=decision,
        idempotency_key=(
            f"{project_id}:g{generation}:approval:{scope}:{decision}"
        ),
        artifact_refs=artifact_refs,
        payload={
            "scope": scope,
            "actor": actor,
            "compliance_ack": compliance_ack,
            "notes": notes,
            "release_sha": record["release_sha"],
            "release_repos": repos,
        },
        generation=generation,
    )
    return record


def awaits_approval(ledger: Ledger, project_id: str) -> bool:
    """True when the project is parked at the staging approval gate."""

    state = ledger.checkpoint_state(project_id)
    if state is None or state[0] != "approval":
        return False
    return not is_approved(ledger, project_id, "staging", state[1])
