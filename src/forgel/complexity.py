"""Deterministic complexity guardrail.

Measures the patch since the generated baseline and flags unbounded growth:
new lines, new configuration knobs, compatibility markers and added branches.
The semantic decision belongs to the Simplicity Arbiter; this is the pre-filter
that stops obvious accumulation before review.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .artifacts import write_json, write_text
from .project_config import SimplicityConfig


@dataclass(frozen=True)
class PatchMetrics:
    added_lines: int = 0
    removed_lines: int = 0
    files_changed: int = 0
    new_files: int = 0
    new_config_keys: int = 0
    compat_markers: int = 0
    branches_added: int = 0


def _git(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )


def measure_patch(workspace: Path) -> PatchMetrics:
    if not (workspace / ".git").exists():
        return PatchMetrics()
    baseline = _git(workspace, "rev-parse", "--verify", "forgel-baseline")
    if baseline.returncode != 0 or not baseline.stdout.strip():
        return PatchMetrics()
    base = baseline.stdout.strip()

    added = removed = files = 0
    for line in _git(workspace, "diff", "--numstat", base).stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "-" or parts[1] == "-":
            continue
        added += int(parts[0])
        removed += int(parts[1])
        files += 1

    names = _git(workspace, "diff", "--name-status", base)
    new_files = sum(
        1 for line in names.stdout.splitlines() if line.startswith("A\t")
    )

    added_text = [
        line[1:]
        for line in _git(workspace, "diff", "--unified=0", base).stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    compat_markers = sum(
        1
        for line in added_text
        if re.search(r"deprecated|legacy|compat|backward", line, re.I)
    )
    branches = sum(
        1
        for line in added_text
        if re.match(r"^\s*(if|elif|try:|except)\b", line)
    )

    config_added = [
        line[1:].strip()
        for line in _git(
            workspace, "diff", "--unified=0", base, "--", "forgel.toml"
        ).stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    new_config_keys = sum(
        1
        for line in config_added
        if re.match(r"^[a-z_][a-z0-9_]*\s*=", line) and not line.startswith("#")
    )

    return PatchMetrics(
        added_lines=added,
        removed_lines=removed,
        files_changed=files,
        new_files=new_files,
        new_config_keys=new_config_keys,
        compat_markers=compat_markers,
        branches_added=branches,
    )


def evaluate(metrics: PatchMetrics, config: SimplicityConfig) -> list[str]:
    if not config.enabled:
        return []
    violations: list[str] = []
    if metrics.added_lines > config.max_added_lines:
        violations.append(
            f"Added {metrics.added_lines} lines; the budget is "
            f"{config.max_added_lines}. Prefer a smaller change or a spec change."
        )
    if metrics.new_config_keys > config.max_new_config_keys:
        violations.append(
            f"Added {metrics.new_config_keys} config keys; the budget is "
            f"{config.max_new_config_keys}. A new knob needs a second consumer."
        )
    if metrics.compat_markers > config.max_compat_markers:
        violations.append(
            f"Added {metrics.compat_markers} compatibility markers; the budget is "
            f"{config.max_compat_markers}. Name the consumer or remove the shim."
        )
    return violations


def write_report(
    workspace: Path, metrics: PatchMetrics, violations: list[str]
) -> Path:
    path = workspace / "docs" / "program" / "complexity" / "report.md"
    verdict = "NEEDS_SIMPLIFICATION" if violations else "PASS"
    lines = [
        "# Complexity Report",
        "",
        f"- Verdict: `{verdict}`",
        f"- Added lines: {metrics.added_lines}",
        f"- Removed lines: {metrics.removed_lines}",
        f"- Files changed: {metrics.files_changed}",
        f"- New files: {metrics.new_files}",
        f"- New config keys: {metrics.new_config_keys}",
        f"- Compatibility markers: {metrics.compat_markers}",
        f"- Branches added: {metrics.branches_added}",
        "",
        "## Violations",
        "",
    ]
    lines.extend(f"- {item}" for item in violations)
    if not violations:
        lines.append("_None._")
    lines.extend(
        [
            "",
            "## Note",
            "",
            "This is a deterministic pre-filter. The Simplicity Arbiter reviews whether",
            "the added requirements, branches and compatibility shims are necessary;",
            "prefer changing the task framing over adding a branch.",
        ]
    )
    write_text(path, "\n".join(lines).rstrip() + "\n")
    write_json(
        workspace / "docs" / "program" / "complexity" / "metrics.json",
        asdict(metrics),
    )
    return path
