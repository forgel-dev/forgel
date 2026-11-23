# Task Spec: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo |
| Project | — |
| Task | `20261123062514_release-audit-readme-md-still-documents-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T15:33:53+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The project's public documentation and the automated check that protects it have drifted from the release contract. The documented install, update and uninstall instructions point at a mutable in-development location rather than a published release, so a reader who copies them gets an unreproducible snapshot that is not the release the page describes and that silently ships unverified changes. The guard that should keep the documented release line trustworthy was inverted: it now forbids naming any release at all, so it would fight the next legitimate release update instead of catching the stale one it exists to catch. The release record must also agree with what the documentation actually says.

**Outcome:** The documentation page's install, update and uninstall instructions name the current published release; the guard accepts that release-identifying form and fails only for a superseded release or for no release at all; the release record matches the documented instructions; and no unrelated pending change is included in or attributed to the delivered result.

## Product Intent

A reader of the public documentation installs and removes exactly the published release the page describes, reproducibly and verifiably, and the automated guard keeps the page pinned to the current release across future releases.

## User Experience

A new user opens the documentation page, copies the install line, and gets the published release described on that page. Copying the update or uninstall line behaves consistently with that same release. Nothing about the page changes silently between releases; a stale page is caught by the project's own checks before it reaches a reader.

## Roadmap

—

## Goals

- Make the documentation page point at the current published release for install, update and uninstall.
- Restore the guard so it protects the release-identifying documentation form and rejects superceded releases.
- Make the release record agree with the documentation.

## Non-Goals

- Changing the installer's behavior
- Publishing, moving or retagging any release
- Choosing or changing any release version
- Changing the packaging, the client behavior or the command line
- Adding new documentation pages or new user-facing features
- Rewriting unrelated parts of the documentation page

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | A published release is immutable: a change after a release is a new version, never a rewrite of the released version; the release process computes and publishes the next version, and agents do not assign, promise or rewrite release versions. | Project FORGEL.md and AGENTS.md, Release Rules / Releases |
| — | A task delivers only the change selected for that task; unrelated changes are never staged, committed or attributed, and every uncommitted product file gets one decision at completion. | FORGEL.md / AGENTS.md native rules (D-097, D-105) |
| — | A specification states behavior, never an implementation file list. | FORGEL.md / AGENTS.md (D-104) |
| — | Never weaken a test to make it pass; fix the product or the test's premise. | Repository code AGENTS.md |
| — | All committed project artifacts are English. | Project AGENTS.md (D-025) |

## Functional Requirements

- **FR-1**: The documented install instruction names the current published release, either by that release's version-pinned location or by a versionless latest location that resolves to the current published release.
- **FR-2**: The documented install instruction does not take its source from an in-development or otherwise mutable location that is not a published release.
- **FR-3**: The documented uninstall instruction uses the same release-identifying form as the documented install instruction.
- **FR-4**: The documented update instruction, where the page provides one, uses the same release-identifying form as the documented install instruction.
- **FR-5**: The guard asserts that the documented install and uninstall instructions use the released installer rather than an in-development location.
- **FR-6**: The guard accepts the release-identifying form that names the current published release.
- **FR-7**: The guard fails when a documented instruction names a release superseded by the current published release, and when it names no release at all.
- **FR-8**: The release record agrees with the release-identifying form and instructions the documentation actually shows.
- **FR-9**: The release record states no release identifier or instruction form that contradicts the documentation.
- **FR-10**: The delivered result is confined to the documentation page, the guard and the release record; any unrelated pending change in the project is not included in it or attributed to it.

## User Stories

- As a new user, I want the documented install instruction to give me the published release the page describes, so that I install something reproducible and verified.
- As a new user, I want the documented uninstall instruction to match the release I installed, so that removal is predictable.
- As a maintainer, I want the guard to fail when the page goes stale, so that a release update cannot be forgotten and an older release cannot linger.
- As a release auditor, I want the release record to state what the page actually shows, so that the record is trustworthy.

## Acceptance Criteria

- **AC-1**: The documented install instruction identifies the current published release rather than an in-development location.
- **AC-2**: The documented uninstall instruction carries the same release identifier as the documented install instruction.
- **AC-3**: Any documented update instruction carries the same release identifier as the documented install instruction.
- **AC-4**: The guard passes against the updated documentation.
- **AC-5**: The guard fails against a documentation variant that names a superseded release, and against a variant that names no release.
- **AC-6**: The release record and the documentation agree on the release identifier and instruction form.
- **AC-7**: The delivered result contains only the documentation page, the guard and the release record, while unrelated pending changes remain undelivered and unattributed.

## Scope Boundaries

- The documentation page's install instruction
- The documentation page's update instruction, when present
- The documentation page's uninstall instruction
- The automated guard that asserts the documented install, update and uninstall instructions name a published release
- The release record's statement of the documented release-identifying form and instructions
- Changing the installer's behavior
- Publishing, moving or retagging any release
- Choosing or changing any release version
- Changing the packaging, the client behavior or the command line
- Adding new documentation pages or new user-facing features
- Rewriting unrelated parts of the documentation page

## Risks

- The guard could derive the current release from a source that also drifts, passing while the page is stale; it must be compared against the release the project currently publishes.
- The release record may live outside this project, in which case the reconciliation half of the task cannot be completed here and must be escalated to the planner.
- If the documentation adopts a versionless latest form, superseded-release detection cannot be a version comparison and needs a different signal that still fails for a stale page.
- A versionless latest form trades reproducibility for automatic currency; if a reader must be able to reproduce the exact release afterwards, only the version-pinned form satisfies that, and the choice is a product decision not yet recorded.
- Unrelated pending changes present when the task starts could be swept into the delivered result, contradicting the recorded rule against delivering everything in progress.

## Open Questions

- Should the documented instructions use a version-pinned release location or a versionless latest location? Both identify a published release and the page must pick one; only the version-pinned form lets a reader reproduce the exact release afterwards.

## Assumptions

- The documentation may identify the release either as a version-pinned location or as a versionless latest location, since both identify a published release; the guard therefore accepts the adopted form and rejects only superseded releases and non-release locations.
- The current published release is the one the existing release record already describes; this task reconciles the documentation to it rather than choosing a version.
- The release record is a project artifact; if it lives outside this project, the planner must say so.
- The guard can tell a superseded release from the current one only if the current release identifier is discoverable in the project, so the guard derives it from existing release information instead of inventing a new version.

## Related Documents

- README.md
- install.sh
- CHANGELOG.md
- releases/0.1.0/release.md
- releases/0.1.0/plan.md

## Revision History

- v3: removed implementation-level wording (version control and delivery mechanics) from problem, outcome, requirements, acceptance, constraints, goals, user stories, risks and assumptions; verification commands kept only in checks.
- v2: rewritten for the reported defect — release-identifying documentation restored, guard turned back to protect the release form and reject only superseded releases, release record reconciled with the documentation, change confined to the documentation and its guard.
