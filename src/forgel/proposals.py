"""Post-release change proposals.

After the user's goal is met, Forgel does not keep polishing. It proposes
changes by SemVer class: PATCH fixes by default, MINOR improvements only when
configured, MAJOR changes only on explicit human initiative.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import write_text
from .project_config import ProjectConfig, ReleaseConfig

VALID_KINDS = {"patch", "minor", "major"}


class ProposalError(RuntimeError):
    """Raised when a proposal is not allowed by the release policy."""


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "proposal"


def _policy(config: ProjectConfig | None) -> ReleaseConfig:
    return config.release if config is not None else ReleaseConfig()


def create_proposal(
    workspace: Path,
    kind: str,
    title: str,
    evidence: str = "",
    risk: str = "",
    auto_apply: bool = False,
) -> Path:
    if kind not in VALID_KINDS:
        raise ProposalError(f"Unknown proposal class: {kind}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    path = (
        workspace
        / "docs"
        / "program"
        / "proposals"
        / f"{timestamp}_{kind}_{_slug(title)}.md"
    )
    write_text(
        path,
        f"""# Proposal: {title}

- Class: `{kind}`
- Status: `pending`
- Created: {datetime.now(timezone.utc).isoformat(timespec="seconds")}
- Auto-apply: `{str(auto_apply).lower()}`

## Evidence

{evidence or "—"}

## Risk

{risk or "—"}

## Decision

Awaiting user approval. On approval, this proposal becomes a change set and
starts a new iteration with its own acceptance criteria and budget.
""",
    )
    return path


def propose_project(
    workspace: Path,
    config: ProjectConfig | None,
    kind: str,
    title: str,
    evidence: str = "",
    risk: str = "",
) -> Path:
    policy = _policy(config)
    if kind not in VALID_KINDS:
        raise ProposalError(f"Unknown proposal class: {kind}")
    if kind == "minor" and not policy.propose_minor:
        raise ProposalError(
            "MINOR proposals are disabled; set [release] propose_minor = true"
        )
    auto_apply = kind == "patch" and policy.auto_patch
    return create_proposal(
        workspace,
        kind=kind,
        title=title,
        evidence=evidence,
        risk=risk,
        auto_apply=auto_apply,
    )


def list_proposals(workspace: Path) -> list[Path]:
    directory = workspace / "docs" / "program" / "proposals"
    if not directory.exists():
        return []
    return sorted(directory.glob("*.md"))


def summarize_proposals(workspace: Path) -> list[dict[str, str]]:
    """Return title, class, status and file name for each proposal."""

    summaries: list[dict[str, str]] = []
    for path in list_proposals(workspace):
        text = path.read_text(encoding="utf-8")
        title = path.stem
        kind = ""
        status = ""
        for line in text.splitlines():
            if line.startswith("# Proposal: "):
                title = line[len("# Proposal: ") :]
            elif line.startswith("- Class: "):
                kind = line.split(":", 1)[1].strip().strip("`")
            elif line.startswith("- Status: "):
                status = line.split(":", 1)[1].strip().strip("`")
        summaries.append(
            {
                "title": title,
                "kind": kind,
                "status": status,
                "file": path.name,
            }
        )
    return summaries
