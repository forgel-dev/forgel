"""Deterministic M0 orchestrator.

The pipeline is intentionally small: brief → requirements → recipe → program
manifest → repo plans → change set → spec → spec review → code → review → QA →
acceptance → audit → done. Each stage writes a durable artifact and is recorded
in the ledger before the next stage starts.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approvals import latest_approval
from .artifacts import copy_template, read_json, write_json, write_text
from .complexity import evaluate, measure_patch, write_report
from .config import Settings
from .intake import build_requirements
from .jurisdiction import resolve_pack
from .ledger import Ledger
from .project_config import (
    SimplicityConfig,
    load_project_config,
    render_project_config,
)
from .registry import load_registry, select_recipe
from .state import next_stage, stages_from

FEATURE_ID = "20261113000000_hello_web"
FEATURE_REL = f"docs/program/features/{FEATURE_ID}.md"


class StageError(RuntimeError):
    """A stage failed and the pipeline cannot continue."""


class ApprovalRequired(Exception):
    """The pipeline is parked until a human records a decision.

    This is control flow, not a failure: the stage is not marked failed and the
    checkpoint stays at ``approval`` so the next run resumes there.
    """

    def __init__(
        self, project_id: str, generation: int, scope: str, decision: str
    ) -> None:
        super().__init__(
            f"{scope} approval required for {project_id} "
            f"(generation {generation}, decision: {decision})"
        )
        self.project_id = project_id
        self.generation = generation
        self.scope = scope
        self.decision = decision


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Orchestrator:
    def __init__(self, settings: Settings, ledger: Ledger) -> None:
        self.settings = settings
        self.ledger = ledger

    # ------------------------------------------------------------------ run

    def run(self, project_id: str) -> dict[str, Any]:
        project = self.ledger.get_project(project_id)
        if project is None:
            raise StageError(f"Unknown project: {project_id}")

        reconciliation = self._docs(project) / "reconciliation.md"
        if reconciliation.exists() and "- Status: pending" in reconciliation.read_text(
            encoding="utf-8"
        ):
            raise StageError(
                "Pending reconciliation; run `forgel reconcile <id> "
                "--decision accept|fix|rollback|ignore` first."
            )

        state = self.ledger.checkpoint_state(project_id)
        if state is None:
            start = "intake"
            generation = self.ledger.current_generation(project_id)
        else:
            start, generation = state

        for stage in stages_from(start):
            if self.ledger.has_completed(project_id, stage, generation):
                self.ledger.set_checkpoint(project_id, next_stage(stage), generation)
                continue

            print(f"[{stage}] running")
            try:
                refs = getattr(self, f"stage_{stage}")(project)
            except ApprovalRequired as exc:
                print(f"[{stage}] awaiting {exc.scope} approval ({exc.decision})")
                result = self.ledger.get_project(project_id)
                assert result is not None
                result = dict(result)
                result["approval_required"] = {
                    "scope": exc.scope,
                    "decision": exc.decision,
                    "generation": exc.generation,
                }
                return result
            except Exception as exc:
                self.ledger.append_event(
                    project_id,
                    stage,
                    status="failed",
                    payload={"error": str(exc)},
                    generation=generation,
                )
                print(f"[{stage}] FAILED: {exc}")
                raise
            self.ledger.append_event(
                project_id,
                stage,
                status="completed",
                artifact_refs=refs,
                generation=generation,
            )
            self.ledger.set_checkpoint(project_id, next_stage(stage), generation)
            print(f"[{stage}] completed")

        updated = self.ledger.get_project(project_id)
        assert updated is not None
        return updated

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _workspace(project: dict[str, Any]) -> Path:
        return Path(project["workspace"])

    def _docs(self, project: dict[str, Any]) -> Path:
        return self._workspace(project) / "docs" / "program"

    def _ref(self, project: dict[str, Any], path: Path) -> str:
        return str(path.relative_to(self._workspace(project)))

    # --------------------------------------------------------------- stages

    def stage_intake(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        requirements = build_requirements(project)
        path = write_json(self._docs(project) / "requirements.json", requirements)
        config_path = workspace / "forgel.toml"
        if not config_path.exists():
            write_text(
                config_path, render_project_config(project["name"])
            )
        return [self._ref(project, path), self._ref(project, config_path)]

    def stage_jurisdiction(self, project: dict[str, Any]) -> list[str]:
        docs = self._docs(project)
        requirements = read_json(docs / "requirements.json")
        config = load_project_config(self._workspace(project))
        pack_id = (
            config.jurisdiction.pack
            if config is not None
            else str(requirements.get("jurisdiction", "ru"))
        )
        region = str(requirements.get("region", ""))
        pack, fallback = resolve_pack(
            self.settings.jurisdiction_path, pack_id, region
        )

        # The layer informs; it does not block. A draft pack is usable and
        # strictly better than an ignored jurisdiction. Responsibility for
        # compliance stays with the human who approves production.
        profile = {
            "id": pack.id,
            "version": pack.version,
            "status": pack.status,
            "region": pack.region,
            "effective_from": pack.effective_from,
            "reviewed_by": pack.reviewed_by,
            "review_due": pack.review_due,
            "legal_review_status": pack.legal_review_status,
            "production_allowed": pack.production_allowed,
            "acknowledgement_required": pack.acknowledgement_required,
            "requires_human_review": pack.requires_human_review,
            "fallback": fallback,
            "requested_id": pack_id,
            "data_residency": pack.data_residency,
            "categories": list(pack.categories),
            "mandatory_requirements": list(pack.mandatory_requirements),
            "prohibitions": list(pack.prohibitions),
            "required_evidence": list(pack.required_evidence),
            "notes": pack.notes,
        }
        profile_path = write_json(docs / "jurisdiction" / "profile.json", profile)

        categories = "\n".join(f"- {item}" for item in pack.categories) or "- none"
        mandatory = (
            "\n".join(
                f"- `{item.get('id', '?')}` {item.get('title', '')}"
                for item in pack.mandatory_requirements
            )
            or "None recorded in this pack."
        )
        prohibitions = (
            "\n".join(f"- {item}" for item in pack.prohibitions)
            or "None recorded in this pack."
        )
        evidence = (
            "\n".join(f"- {item}" for item in pack.required_evidence)
            or "None recorded in this pack."
        )
        allowed_label = "yes"
        ack_label = "yes" if pack.acknowledgement_required else "no"
        review_label = pack.legal_review_status
        fallback_note = (
            f"\n> No pack named `{pack_id}` was found; the generic draft pack was used.\n"
            if fallback
            else ""
        )

        requirements_path = docs / "jurisdiction" / "requirements.md"
        write_text(
            requirements_path,
            f"""# Jurisdiction Requirements: {pack.id}

- Pack: `{pack.ref}`
- Status: `{pack.status}`
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}**
- Human acknowledgement required: **{ack_label}**
- Data residency: `{pack.data_residency}`
{fallback_note}

## Categories

{categories}

## Mandatory Requirements

{mandatory}

## Prohibitions

{prohibitions}

## Required Evidence

{evidence}

## Compliance Disclaimer

Forgel is a software development tool, not a law firm. This pack is draft guidance,
may be incomplete or out of date, and is not legal advice. Forgel does not warrant
that the generated product complies with the laws of any jurisdiction. The user is
responsible for reviewing these requirements and for regulatory compliance. Approving
a production deploy confirms that responsibility.

See `docs/program/jurisdiction/disclaimer.md`.
""",
        )

        data_flow_path = docs / "jurisdiction" / "data-flow.md"
        write_text(
            data_flow_path,
            f"""# Data Flow and Residency: {pack.id}

- Pack status: `{pack.status}`
- Data residency: `{pack.data_residency}`
- Model endpoint constraints: `to-be-confirmed`

The architecture stage must record where each data class is stored and processed,
including model endpoints, before this pack can be reviewed.
""",
        )

        compliance_rows = (
            "\n".join(
                f"| `{item.get('id', '?')}` | {item.get('verification', '—')} | "
                f"{item.get('evidence', '—')} | pending |"
                for item in pack.mandatory_requirements
            )
            or "| — | — | — | pending human review |"
        )
        compliance_path = docs / "jurisdiction" / "compliance.md"
        write_text(
            compliance_path,
            f"""# Compliance Evidence: {pack.id}

- Pack: `{pack.ref}`
- Status: `{pack.status}`
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}** (acknowledgement required: **{ack_label}**)

| Requirement | Verification | Evidence | Status |
|---|---|---|---|
{compliance_rows}

> Evidence is recorded only for reviewed mandatory requirements. A draft pack has none.
""",
        )

        disclaimer_path = docs / "jurisdiction" / "disclaimer.md"
        write_text(
            disclaimer_path,
            """# Compliance Disclaimer

Forgel is a software development tool, not a law firm. Jurisdiction packs are draft
guidance, may be incomplete or out of date, and are not legal advice. Forgel does not
warrant that any generated product complies with the laws of any jurisdiction.

The user is responsible for reviewing the jurisdiction requirements and for
regulatory compliance. Approving a production deploy confirms that responsibility.
""",
        )

        legal_review_path = docs / "jurisdiction" / "legal-review.md"
        if pack.acknowledgement_required:
            review_body = (
                "- Status: **not reviewed**\n"
                "- Reviewed by: —\n"
                "- Review due: —\n"
                "- Production: **allowed**, subject to the disclaimer and human acknowledgement.\n"
            )
        else:
            review_body = (
                "- Status: **reviewed by a named reviewer**\n"
                f"- Reviewed by: {pack.reviewed_by}\n"
                f"- Review due: {pack.review_due}\n"
                "- Production: allowed after the project's human sign-off. This is still not a legal guarantee.\n"
            )
        write_text(
            legal_review_path,
            f"""# Legal Review: {pack.id}

{review_body}
""",
        )

        return [
            self._ref(project, profile_path),
            self._ref(project, requirements_path),
            self._ref(project, data_flow_path),
            self._ref(project, compliance_path),
            self._ref(project, disclaimer_path),
            self._ref(project, legal_review_path),
        ]

    def stage_recipe(self, project: dict[str, Any]) -> list[str]:
        requirements = read_json(self._docs(project) / "requirements.json")
        recipes = load_registry(self.settings.registry_path)
        recipe = select_recipe(recipes, requirements)

        project["recipe_id"] = recipe.ref
        self.ledger.set_recipe(project["id"], recipe.ref)

        config_path = self._workspace(project) / "forgel.toml"
        if config_path.exists():
            config_text = config_path.read_text(encoding="utf-8")
            config_text = re.sub(
                r'(?m)^recipe = ".*"$',
                f'recipe = "{recipe.ref}"',
                config_text,
                count=1,
            )
            write_text(config_path, config_text)
        else:
            write_text(
                config_path,
                render_project_config(project["name"], recipe.ref),
            )

        adr = self._docs(project) / "adr" / "0001-recipe.md"
        write_text(
            adr,
            f"""# ADR 0001: Recipe Selection

- Chosen recipe: `{recipe.ref}`
- Status: `{recipe.status}`
- Template: `{recipe.template}`
- Composes: {", ".join(f"`{item}`" for item in recipe.composes) or "none"}

## Why

The deterministic matcher selected this recipe from the registry. The LLM was not
asked to invent a composition, and no plugin outside the recipe was used.
""",
        )
        return [self._ref(project, adr)]

    def stage_architecture(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        recipe_ref = project.get("recipe_id") or "unknown"
        profile = read_json(self._docs(project) / "jurisdiction" / "profile.json")
        pack_ref = f"{profile['id']}@{profile['version']}"
        allowed_label = "yes" if profile.get("production_allowed") else "no"
        ack_label = "yes" if profile.get("acknowledgement_required") else "no"
        review_label = profile.get("legal_review_status", "unknown")

        lines = [
            "# program.yaml",
            f"project: {project['name']}",
            f"recipe: {recipe_ref}",
            "repos:",
        ]
        repos = (
            ("api", "backend", "./api"),
            ("web", "frontend", "./web"),
            ("infra", "infrastructure", "./infra"),
            ("e2e", "acceptance", "./e2e"),
        )
        for repo_id, role, path in repos:
            lines.extend(
                [f"  - id: {repo_id}", f"    role: {role}", f"    path: {path}"]
            )
            if repo_id == "api":
                lines.extend(["    contracts:", "      publishes: [openapi.yaml]"])
            if repo_id == "web":
                lines.extend(["    contracts:", "      consumes: [api/openapi.yaml]"])
        program_path = write_text(workspace / "program.yaml", "\n".join(lines) + "\n")

        master = self._docs(project) / "master-plan.md"
        write_text(
            master,
            f"""# Master Plan: {project['name']}

## Goal

{project['brief']}

## Repositories

| Repo | Role | Path |
|---|---|---|
| api | backend | ./api |
| web | frontend | ./web |
| infra | infrastructure | ./infra |
| e2e | acceptance | ./e2e |

## Contracts

- `api` publishes OpenAPI 3.1.
- `web` consumes the generated client.

## Jurisdiction

- Pack: `{pack_ref}`
- Status: `{profile['status']}`
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}** (acknowledgement required: **{ack_label}**)
- See `docs/program/jurisdiction/requirements.md`.

## Dependency Graph

- `web` depends on `api`.
- `e2e` depends on `api` and `web`.
- `infra` is independent.

## Open Questions

- None for the M0 skeleton.
""",
        )
        return [self._ref(project, program_path), self._ref(project, master)]

    def stage_repo_plan(self, project: dict[str, Any]) -> list[str]:
        plans = {
            "api": "Backend. Serves `/health` and the static frontend for M0.",
            "web": "Frontend. A static `index.html`; there is no build step in M0.",
            "infra": "Infrastructure. The local provider only; no cloud resources in M0.",
            "e2e": "Acceptance. Starts the API and asserts `/health` and `/`.",
        }
        refs: list[str] = []
        for repo_id, description in plans.items():
            path = self._docs(project) / "repos" / f"{repo_id}.md"
            write_text(
                path,
                f"""# Repo: {repo_id}

{description}

## Contracts

- See `program.yaml`.

## M0 Boundary

- This repository is generated from the `hello-web` template.
- It has no third-party runtime dependencies.
""",
            )
            refs.append(self._ref(project, path))
        return refs

    def stage_feature_plan(self, project: dict[str, Any]) -> list[str]:
        feature = self._workspace(project) / FEATURE_REL
        change_sets = {
            "change_sets": [
                {
                    "id": "cs-0001",
                    "name": "hello-web",
                    "repos": ["api", "web", "infra", "e2e"],
                    "feature": FEATURE_REL,
                }
            ]
        }
        path = write_json(
            self._docs(project) / "change-sets.json", change_sets
        )
        return [self._ref(project, feature), self._ref(project, path)]

    def stage_spec(self, project: dict[str, Any]) -> list[str]:
        feature = self._workspace(project) / FEATURE_REL
        profile = read_json(self._docs(project) / "jurisdiction" / "profile.json")
        pack_ref = f"{profile['id']}@{profile['version']}"
        allowed_label = "yes" if profile.get("production_allowed") else "no"
        ack_label = "yes" if profile.get("acknowledgement_required") else "no"
        review_label = profile.get("legal_review_status", "unknown")
        mandatory_lines = (
            "\n".join(
                f"- `{item.get('id', '?')}`: "
                f"{item.get('requirement', item.get('title', ''))}"
                for item in profile.get("mandatory_requirements", [])
            )
            or "- None recorded in this pack."
        )
        write_text(
            feature,
            f"""# Feature: Hello Web

## Document Information

| Field | Value |
|---|---|
| Feature | Hello Web |
| Version | 0.1.0 |
| Status | Draft |
| Date | 2026-11-13 |
| Author | Forgel spec writer |

## Overview

A minimal web product generated by Forgel's M0 skeleton. It proves the pipeline
from a brief to a running staging artifact.

## Goals

- Serve an index page with the project name.
- Serve a `/health` endpoint.
- Pass an automated acceptance check.

## Non-Goals

- Authentication, payments and persistence.
- A real cloud provider.
- Mobile clients.

## Functional Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| FR-1 | The app serves `GET /health` with JSON `{{"status":"ok"}}`. | Must | |
| FR-2 | The app serves `GET /` with an HTML page containing the project name. | Must | |
| FR-3 | The app starts on a configurable port. | Must | `PORT` env or `--port`. |

## Non-Functional Requirements

- NFR-1: No third-party runtime dependencies.
- NFR-2: The acceptance check runs in under 10 seconds.
- NFR-3: The app binds to `127.0.0.1` by default.

## Affected Files

- `api/app.py`
- `web/index.html`
- `e2e/check.py`
- `Dockerfile`
- `docker/docker-compose.qa.yml`
- `qa/runner.mjs`
- `qa/scenarios/hello_web.mjs`

## Jurisdiction Requirements

- Pack: `{pack_ref}` ({profile['status']})
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}** (acknowledgement required: **{ack_label}**)

{mandatory_lines}

See `docs/program/jurisdiction/requirements.md` and
`docs/program/jurisdiction/disclaimer.md`.

## Acceptance Criteria

- [ ] AC-1: `GET /health` returns HTTP 200 and `status=ok`.
- [ ] AC-2: `GET /` returns HTTP 200 and contains `{project['name']}`.
- [ ] AC-3: The E2E check exits 0 and reports at least 4 passing checks.

## Open Questions

- None for M0.

## Related Resources

- `program.yaml`
- `forgel.toml`
- `docs/program/change-sets.json`

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-11-13 | Forgel spec writer | Initial specification |
""",
        )
        return [self._ref(project, feature)]

    def stage_spec_review(self, project: dict[str, Any]) -> list[str]:
        spec = (self._workspace(project) / FEATURE_REL).read_text(encoding="utf-8")
        required = (
            "## Overview",
            "## Goals",
            "## Non-Goals",
            "## Functional Requirements",
            "## Affected Files",
            "## Jurisdiction Requirements",
            "## Acceptance Criteria",
            "## Open Questions",
            "## Revision History",
        )
        missing = [heading for heading in required if heading not in spec]
        verdict = "PASS" if not missing else "FAIL"
        path = self._docs(project) / "spec-review.md"
        body = (
            "All required sections are present.\n"
            if not missing
            else "Missing sections:\n" + "\n".join(f"- {item}" for item in missing) + "\n"
        )
        write_text(path, f"# Spec Review\n\n**Verdict:** {verdict}\n\n{body}")
        if missing:
            raise StageError(f"Spec review failed: missing {missing}")
        return [self._ref(project, path)]

    def stage_dev(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        template = self.settings.templates_path / "hello-web"
        if not template.exists():
            raise StageError(f"Template not found: {template}")

        substitutions = {
            "__PROJECT_NAME__": project["name"],
            "__PROJECT_ID__": project["id"],
            "__RECIPE__": project.get("recipe_id") or "",
        }
        refs: list[str] = []
        for name in (
            "Dockerfile",
            ".dockerignore",
            ".gitignore",
            "FORGEL.md",
            "AGENTS.md",
        ):
            source = template / name
            text = source.read_text(encoding="utf-8")
            for key, value in substitutions.items():
                text = text.replace(key, value)
            write_text(workspace / name, text)
            refs.append(name)
        for directory in ("api", "web", "infra", "e2e", "docker", "qa"):
            copy_template(template / directory, workspace / directory, substitutions)
            refs.append(directory)

        self._write_artifact_manifest(workspace)
        self._init_baseline_git(workspace)
        refs.append("docs/program/artifact-manifest.json")
        return refs

    @staticmethod
    def _write_artifact_manifest(workspace: Path) -> None:
        files: dict[str, str] = {}
        for path in sorted(workspace.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(workspace)
            if any(
                part in {"__pycache__", "node_modules", ".git"}
                for part in relative.parts
            ):
                continue
            if relative.as_posix() == "docs/program/artifact-manifest.json":
                continue
            files[relative.as_posix()] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        write_json(
            workspace / "docs" / "program" / "artifact-manifest.json",
            {"generated_at": utcnow(), "files": files},
        )

    @staticmethod
    def _init_baseline_git(workspace: Path) -> None:
        if shutil.which("git") is None or (workspace / ".git").exists():
            return
        subprocess.run(
            ["git", "init", "-q"], cwd=str(workspace), check=False
        )
        subprocess.run(
            ["git", "add", "-A"], cwd=str(workspace), check=False
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Forgel",
                "-c",
                "user.email=forgel@localhost",
                "commit",
                "-q",
                "-m",
                "Generated baseline",
            ],
            cwd=str(workspace),
            check=False,
        )
        subprocess.run(
            ["git", "tag", "-f", "forgel-baseline"],
            cwd=str(workspace),
            check=False,
        )

    @staticmethod
    def _commit_release_candidate(workspace: Path, generation: int) -> None:
        """Commit the tree the human reviews, so the approval names a SHA.

        The baseline tag is not moved here: it marks the last closed
        generation, and ``sync`` still compares against it.
        """

        if shutil.which("git") is None or not (workspace / ".git").exists():
            return
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            check=False,
        )
        if not status.stdout.strip():
            return
        subprocess.run(
            ["git", "add", "-A"], cwd=str(workspace), check=False
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Forgel",
                "-c",
                "user.email=forgel@localhost",
                "commit",
                "-q",
                "-m",
                f"Forgel release candidate for generation {generation}",
            ],
            cwd=str(workspace),
            check=False,
        )

    @staticmethod
    def _commit_generated_state(workspace: Path, generation: int) -> None:
        if shutil.which("git") is None or not (workspace / ".git").exists():
            return
        subprocess.run(
            ["git", "add", "-A"], cwd=str(workspace), check=False
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Forgel",
                "-c",
                "user.email=forgel@localhost",
                "commit",
                "-q",
                "-m",
                f"Forgel generation {generation} complete",
            ],
            cwd=str(workspace),
            check=False,
        )
        subprocess.run(
            ["git", "tag", "-f", "forgel-baseline"],
            cwd=str(workspace),
            check=False,
        )

    def stage_review(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        reconciliation = self._docs(project) / "reconciliation.md"
        if reconciliation.exists() and "- Status: fix_required" in reconciliation.read_text(
            encoding="utf-8"
        ):
            raise StageError(
                "A reconciliation fix is required; see docs/program/reconciliation.md"
            )
        checks: list[tuple[str, bool]] = []

        config = load_project_config(workspace)
        simplicity = (
            config.simplicity if config is not None else SimplicityConfig()
        )
        metrics = measure_patch(workspace)
        violations = evaluate(metrics, simplicity)
        complexity_path = write_report(workspace, metrics, violations)

        for relative in (
            "api/app.py",
            "web/index.html",
            "e2e/check.py",
            "Dockerfile",
            "docker/docker-compose.qa.yml",
            "qa/runner.mjs",
            "qa/package.json",
            "qa/scenarios/hello_web.mjs",
            "FORGEL.md",
            "AGENTS.md",
            "forgel.toml",
        ):
            checks.append((f"exists: {relative}", (workspace / relative).exists()))

        compose = workspace / "docker" / "docker-compose.qa.yml"
        if compose.exists():
            checks.append(
                (
                    "compose declares services",
                    "services:" in compose.read_text(encoding="utf-8"),
                )
            )

        for relative in ("api/app.py", "e2e/check.py"):
            path = workspace / relative
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
                checks.append((f"compiles: {relative}", True))
            except (OSError, SyntaxError):
                checks.append((f"compiles: {relative}", False))

        unresolved: list[str] = []
        for path in workspace.rglob("*"):
            if not path.is_file() or path.suffix not in {
                ".py",
                ".html",
                ".md",
                ".yaml",
                ".json",
                ".js",
                ".mjs",
                ".toml",
            }:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "__PROJECT_NAME__" in text or "__PROJECT_ID__" in text:
                unresolved.append(str(path.relative_to(workspace)))
        checks.append(("no unresolved template placeholders", not unresolved))
        checks.append(("simplicity budget", not violations))

        failed = [name for name, passed in checks if not passed]
        verdict = "PASS" if not failed else "FAIL"
        path = self._docs(project) / "review.md"
        lines = [
            "# Code Review",
            "",
            f"**Verdict:** {verdict}",
            "",
            "| Check | Result |",
            "|---|---|",
        ]
        lines.extend(
            f"| {name} | {'PASS' if passed else 'FAIL'} |" for name, passed in checks
        )
        if unresolved:
            lines.extend(["", "Unresolved placeholders: " + ", ".join(unresolved)])
        if violations:
            lines.extend(
                ["", "## Simplicity Violations", ""]
                + [f"- {item}" for item in violations]
            )
        write_text(path, "\n".join(lines) + "\n")
        if failed:
            raise StageError(f"Review failed: {failed}")
        return [self._ref(project, path), self._ref(project, complexity_path)]

    def stage_qa(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        runtime = self.settings.qa_runtime
        config = load_project_config(workspace)
        if runtime == "auto" and config is not None:
            runtime = config.qa.runtime
        if runtime == "auto":
            runtime = "docker" if self._docker_available() else "local"

        if runtime == "docker":
            returncode, output, runtime_label = self._run_qa_docker(workspace)
        else:
            returncode, output = self._run_qa_local(workspace)
            runtime_label = "local"

        verdict = "PASS" if returncode == 0 else "FAIL"
        path = self._docs(project) / "qa-report.md"
        write_text(
            path,
            f"""# QA Report

**Verdict:** {verdict}

**Runtime:** {runtime_label}

**Exit code:** {returncode}

```
{output.strip()}
```
""",
        )
        if returncode != 0:
            raise StageError(f"QA failed with exit code {returncode}: {output}")
        return [self._ref(project, path)]

    def _run_qa_local(self, workspace: Path) -> tuple[int, str]:
        script = workspace / "e2e" / "check.py"
        if not script.exists():
            raise StageError(f"QA script not found: {script}")
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(workspace / "e2e"),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        output = completed.stdout
        if completed.stderr:
            output += "\n" + completed.stderr
        return completed.returncode, output

    def _run_qa_docker(self, workspace: Path) -> tuple[int, str, str]:
        compose = workspace / "docker" / "docker-compose.qa.yml"
        if not compose.exists():
            compose = workspace / "compose.yaml"
        if not compose.exists():
            raise StageError(f"QA compose file not found in {workspace}")

        port = self._free_port()
        env = {**os.environ, "APP_PORT": str(port)}
        base_url = f"http://127.0.0.1:{port}"
        output = f"$ docker compose -f {compose} up -d --build\n"
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose), "up", "-d", "--build"],
            cwd=str(workspace),
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        output += result.stdout + result.stderr
        returncode = result.returncode

        try:
            if returncode == 0:
                self._wait_for_url(base_url + "/health")
                returncode, runner_output = self._run_browser_runner(
                    workspace, base_url
                )
                output += runner_output
        except Exception as exc:  # noqa: BLE001 - surface the failure in the report
            output += f"\nQA runtime error: {exc}\n"
            returncode = 1
        finally:
            down = subprocess.run(
                ["docker", "compose", "-f", str(compose), "down", "-v"],
                cwd=str(workspace),
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            output += "\n$ docker compose down -v\n" + down.stdout + down.stderr

        return returncode, output, "docker + headless Chrome"

    def _run_browser_runner(
        self, workspace: Path, base_url: str
    ) -> tuple[int, str]:
        qa_dir = workspace / "qa"
        runner = qa_dir / "runner.mjs"
        if not runner.exists():
            raise StageError(f"Browser QA runner not found: {runner}")

        node = shutil.which("node")
        npm = shutil.which("npm")
        if node is None:
            raise StageError("node is required for the browser QA runner")

        output = ""
        if npm is not None and not (qa_dir / "node_modules" / "puppeteer-core").exists():
            install = subprocess.run(
                [npm, "install", "--no-package-lock", "--no-audit", "--no-fund"],
                cwd=str(qa_dir),
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            output += "$ npm install\n" + install.stdout + install.stderr
            if install.returncode != 0:
                return install.returncode, output

        completed = subprocess.run(
            [node, str(runner), "--base-url", base_url],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        output += (
            "\n$ node qa/runner.mjs --base-url ...\n"
            + completed.stdout
            + completed.stderr
        )
        return completed.returncode, output

    @staticmethod
    def _docker_available() -> bool:
        if shutil.which("docker") is None:
            return False
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _wait_for_url(url: str, timeout: float = 90.0) -> None:
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except Exception as exc:  # noqa: BLE001 - retry until the deadline
                last_error = exc
            time.sleep(0.5)
        raise StageError(f"Timed out waiting for {url}: {last_error}")

    def stage_acceptance(self, project: dict[str, Any]) -> list[str]:
        docs = self._docs(project)
        qa = (docs / "qa-report.md").read_text(encoding="utf-8")
        review = (docs / "review.md").read_text(encoding="utf-8")
        spec_review = (docs / "spec-review.md").read_text(encoding="utf-8")
        jurisdiction = read_json(docs / "jurisdiction" / "profile.json")
        production_allowed = bool(jurisdiction.get("production_allowed", True))
        acknowledgement_required = bool(
            jurisdiction.get("acknowledgement_required", True)
        )
        review_label = jurisdiction.get("legal_review_status", "unknown")

        reconciliation = docs / "reconciliation.md"
        reconciliation_status = "none"
        if reconciliation.exists():
            for line in reconciliation.read_text(encoding="utf-8").splitlines():
                if line.startswith("- Status:"):
                    reconciliation_status = line.split(":", 1)[1].strip()
                    break

        summary = re.search(r"SUMMARY: (\d+)/(\d+) checks passed", qa)
        passed_count = int(summary.group(1)) if summary else 0
        total_count = int(summary.group(2)) if summary else 0

        checks = {
            "AC-1: `/health` returns 200 and `status=ok`": (
                "**Verdict:** PASS" in qa and "PASS health status 200" in qa
            ),
            "AC-2: `/` returns 200 and contains the project name": (
                "**Verdict:** PASS" in qa and "PASS index mentions project" in qa
            ),
            "AC-3: E2E exits 0 with at least 4 checks": (
                "**Verdict:** PASS" in qa and total_count >= 4 and passed_count == total_count
            ),
            "Code review passed": "**Verdict:** PASS" in review,
            "Spec review passed": "**Verdict:** PASS" in spec_review,
            "Jurisdiction profile present": (docs / "jurisdiction" / "profile.json").exists(),
            "Jurisdiction disclaimer present": (
                docs / "jurisdiction" / "disclaimer.md"
            ).exists(),
            "Jurisdiction gate evaluated": (
                "production_allowed" in jurisdiction
                and "acknowledgement_required" in jurisdiction
            ),
            "Reconciliation resolved": reconciliation_status
            not in {"pending", "fix_required"},
        }
        failed = [name for name, passed in checks.items() if not passed]
        verdict = "PASS" if not failed else "FAIL"

        path = docs / "acceptance" / "0001_hello-web.md"
        lines = [
            "# Acceptance: Hello Web",
            "",
            f"**Verdict:** {verdict}",
            "",
            "| Criterion | Evidence | Result |",
            "|---|---|---|",
        ]
        evidence = {
            "AC-1: `/health` returns 200 and `status=ok`": "`qa-report.md`",
            "AC-2: `/` returns 200 and contains the project name": "`qa-report.md`",
            "AC-3: E2E exits 0 with at least 4 checks": "`qa-report.md`",
            "Code review passed": "`review.md`",
            "Spec review passed": "`spec-review.md`",
            "Jurisdiction profile present": "`docs/program/jurisdiction/profile.json`",
            "Jurisdiction disclaimer present": "`docs/program/jurisdiction/disclaimer.md`",
            "Jurisdiction gate evaluated": "`docs/program/jurisdiction/requirements.md`",
            "Reconciliation resolved": "`docs/program/reconciliation.md`",
        }
        lines.extend(
            f"| {name} | {evidence.get(name, '—')} | "
            f"{'PASS' if passed else 'FAIL'} |"
            for name, passed in checks.items()
        )
        if summary:
            lines.extend(
                [
                    "",
                    f"E2E summary: {passed_count}/{total_count} checks passed.",
                ]
            )
        lines.extend(
            [
                "",
                f"Production allowed: **{'yes' if production_allowed else 'no'}** "
                f"(human acknowledgement required: **{'yes' if acknowledgement_required else 'no'}**).",
                f"Legal review: `{review_label}`.",
                f"Reconciliation: `{reconciliation_status}`.",
                "Compliance responsibility remains with the human who approves production; "
                "see `docs/program/jurisdiction/disclaimer.md`.",
            ]
        )
        write_text(path, "\n".join(lines) + "\n")
        if failed:
            raise StageError(f"Acceptance failed: {failed}")
        return [self._ref(project, path)]

    def stage_audit(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        jurisdiction = read_json(self._docs(project) / "jurisdiction" / "profile.json")
        production_allowed = bool(jurisdiction.get("production_allowed", True))
        acknowledgement_required = bool(
            jurisdiction.get("acknowledgement_required", True)
        )
        allowed_label = "yes" if production_allowed else "no"
        ack_label = "yes" if acknowledgement_required else "no"
        review_label = jurisdiction.get("legal_review_status", "unknown")
        scope_line = (
            "staging; production requires the human acknowledgement of the compliance disclaimer."
        )
        required = (
            "program.yaml",
            "docs/program/requirements.json",
            "docs/program/master-plan.md",
            "docs/program/change-sets.json",
            "docs/program/artifact-manifest.json",
            FEATURE_REL,
            "docs/program/spec-review.md",
            "docs/program/review.md",
            "docs/program/complexity/report.md",
            "docs/program/qa-report.md",
            "docs/program/acceptance/0001_hello-web.md",
            "docs/program/jurisdiction/profile.json",
            "docs/program/jurisdiction/requirements.md",
            "docs/program/jurisdiction/data-flow.md",
            "docs/program/jurisdiction/compliance.md",
            "docs/program/jurisdiction/disclaimer.md",
            "docs/program/jurisdiction/legal-review.md",
            "api/app.py",
            "web/index.html",
            "e2e/check.py",
            "Dockerfile",
            ".dockerignore",
            ".gitignore",
            "docker/docker-compose.qa.yml",
            "qa/runner.mjs",
            "qa/package.json",
            "qa/scenarios/hello_web.mjs",
            "FORGEL.md",
            "AGENTS.md",
            "forgel.toml",
        )
        missing = [item for item in required if not (workspace / item).exists()]

        registry_sha = hashlib.sha256(
            self.settings.registry_path.read_bytes()
        ).hexdigest()
        lock = {
            "recipe": project.get("recipe_id"),
            "registry_sha256": registry_sha,
            "repos": {
                "api": "0.1.0",
                "web": "0.1.0",
                "infra": "0.1.0",
                "e2e": "0.1.0",
            },
            "jurisdiction": {
                "id": jurisdiction["id"],
                "version": jurisdiction["version"],
                "status": jurisdiction["status"],
                "legal_review_status": review_label,
                "production_allowed": production_allowed,
                "acknowledgement_required": acknowledgement_required,
            },
            "generated_at": utcnow(),
        }
        lock_path = write_json(workspace / "lock.json", lock)

        staging = {
            "status": "ready",
            "host": "127.0.0.1",
            "port": 8000,
            "url": "http://127.0.0.1:8000",
            "command": f"{sys.executable} api/app.py",
            "checked_at": utcnow(),
        }
        staging_path = write_json(workspace / "staging.json", staging)

        verdict = "PASS" if not missing else "FAIL"
        audit_path = self._docs(project) / "audit.md"
        body = (
            "All required artifacts are present.\n"
            if not missing
            else "Missing artifacts:\n" + "\n".join(f"- {item}" for item in missing) + "\n"
        )
        write_text(
            audit_path,
            f"""# Pre-release Audit

**Verdict:** {verdict}

{body}
- Lockfile: `lock.json`
- Staging descriptor: `staging.json`
- Staging approval: **required** before the pipeline may close the iteration
- Jurisdiction: `{jurisdiction['id']}@{jurisdiction['version']}` ({jurisdiction['status']})
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}** (acknowledgement required: **{ack_label}**)
- Scope: {scope_line}
""",
        )
        if missing:
            raise StageError(f"Audit failed: missing {missing}")
        return [
            self._ref(project, lock_path),
            self._ref(project, staging_path),
            self._ref(project, audit_path),
        ]

    def stage_approval(self, project: dict[str, Any]) -> list[str]:
        """Park the pipeline until staging is approved for this generation."""

        workspace = self._workspace(project)
        generation = self.ledger.current_generation(project["id"])
        self._commit_release_candidate(workspace, generation)
        approval = latest_approval(self.ledger, project["id"], "staging", generation)
        if approval is None:
            raise ApprovalRequired(project["id"], generation, "staging", "pending")
        if approval["decision"] != "approved":
            raise ApprovalRequired(
                project["id"], generation, "staging", approval["decision"]
            )

        staging_path = workspace / "staging.json"
        staging = read_json(staging_path) if staging_path.exists() else {}
        staging.update(
            {
                "status": "approved",
                "approved_at": approval["created_at"],
                "approved_by": approval["actor"],
                "generation": generation,
            }
        )
        write_json(staging_path, staging)
        return [self._ref(project, staging_path), "docs/program/approvals.md"]

    def stage_done(self, project: dict[str, Any]) -> list[str]:
        workspace = self._workspace(project)
        staging_path = workspace / "staging.json"
        staging = read_json(staging_path) if staging_path.exists() else {}
        jurisdiction = read_json(self._docs(project) / "jurisdiction" / "profile.json")
        allowed_label = "yes" if jurisdiction.get("production_allowed") else "no"
        ack_label = "yes" if jurisdiction.get("acknowledgement_required") else "no"
        review_label = jurisdiction.get("legal_review_status", "unknown")
        generation = self.ledger.current_generation(project["id"])
        approval = latest_approval(self.ledger, project["id"], "staging", generation)
        approval_line = (
            f"{approval['decision']} by {approval['actor']} at {approval['created_at']}"
            if approval is not None
            else "not recorded"
        )
        path = self._docs(project) / "state.md"
        write_text(
            path,
            f"""# Project State

- Project: `{project['id']}`
- Name: `{project['name']}`
- Recipe: `{project.get('recipe_id')}`
- Jurisdiction: `{jurisdiction['id']}@{jurisdiction['version']}` ({jurisdiction['status']})
- Legal review: `{review_label}`
- Production allowed: **{allowed_label}** (acknowledgement required: **{ack_label}**)
- Staging approval: {approval_line}
- Status: done
- Staging: {staging.get('url', 'not available')}
- Staging command: `{staging.get('command', 'not available')}`
""",
        )
        iteration = (
            self._docs(project)
            / "iterations"
            / str(generation)
            / "close.md"
        )
        write_text(
            iteration,
            f"""# Iteration {generation} Close

- Goal: complete the current generation and pass all gates
- Status: done
- Acceptance: PASS
- Staging approval: {approval_line}
- Legal review: `{review_label}`
- Staging: {staging.get('url', 'not available')}
- Deferred: none recorded
""",
        )
        self._commit_generated_state(workspace, generation)
        return [self._ref(project, path), self._ref(project, iteration)]


def dump_json(data: Any) -> str:
    """Small helper used by the CLI and tests."""

    return json.dumps(data, indent=2, ensure_ascii=False)
