# Agent Run: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Status: `done`
- Repository: `code`
- Steps: 125
- Finished: 2026-11-23T16:33:05+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The current release is v0.1.1 (the audit finding and the repository tag), so the documented install-script URL pins exactly that tag once in the URL path and both commands inherit it (R3).
- R4 forbids changing the rest of the README, so the surrounding prose, the `curl -fsSL <url> | sh` command shape and the section structure were left byte-identical; the guard file's constant is the only other place the URL appears.
- tests/test_cli.py had to be restored to its release-pinned assertions (rather than kept with the branch-URL assertions from the previous attempt) because the existing test there asserted the inverse of R3; this is a repair of an earlier attempt, not a new requirement.
- install.sh, tests/test_install.py and tests/test_check_cleanup.py are unrelated pre-existing worktree changes; per D-105 they are escalated and left uncommitted and unattributed to this task.
- Git write commands were refused by the sandbox in this session, so the commit itself was not created by the agent; the deliverable is the exact three-file change set in the working tree.

## Test Removals

- tests/test_cli.py::ReadmeTest::test_readme_has_no_tag_pinned_install: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 3
- Handoffs: 2
- Model calls: 125
- Estimated input tokens (all calls): 4660360
- Provider input/output tokens: 4672260 / 204619
- Provider cache hit/miss tokens: 4371584 / 300676
- Estimated prompt at the end: 111072 tokens
- State: `docs/program/agent/20261123062514_release-audit-readme-md-still-documents-.state.md`

## Specification (`docs/program/specs/20261123062514_release-audit-readme-md-still-documents-.md`)

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


## Summary

Re-pointed the README install, update and uninstall commands from the default-branch install-script URL to the published v0.1.1 release installer (`.../forgel-dev/code/v0.1.1/install.sh`), a three-line URL-only diff that leaves the prose, command shape, options and section structure untouched. Restored the release-pinned README guard in tests/test_cli.py (`ReadmeTest.test_readme_has_no_default_branch_install` plus the pinned install and update assertions), so the suite no longer forbids a release tag and instead rejects a branch URL. tests/test_readme_install.py now requires every documented install-script URL to carry exactly one release selector equal to the current release `v0.1.1`, and keeps rejecting the stale `v0.1.0` path, a divergent tag, a default-branch URL, a second URL and a missing URL; the fixture-based tests prove each check fails as designed. The v0.1.1 tag exists in the repository, so the documented tag resolves. Tests: `python -m pytest -q` on the final tree passed with 214 tests and 137 subtests. Git write commands (commit) were rejected by the sandbox this session, so the change set is left staged-ready in the working tree: README.md, tests/test_readme_install.py and tests/test_cli.py only.; escalated unrelated changes for the planner: install.sh, tests/test_install.py, tests/test_check_cleanup.py

## Files Changed

- `README.md`
- `tests/test_cli.py`
- `tests/test_readme_install.py`

## Commands

- `["git", "status", "--short"]` → exit 0
- `["git", "log", "--oneline", "--decorate", "-10"]` → exit 0
- `["git", "diff", "-U0", "--", "README.md"]` → exit 0
- `["git", "diff", "-U0", "--", "tests/test_cli.py"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "-U2", "--", "README.md", "tests/test_readme_install.py"]` → exit 0
- `["git", "log", "--oneline", "--decorate", "-10"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "-U0", "--", "README.md"]` → exit 0
- `["git", "log", "--oneline", "-6"]` → exit 0
- `["git", "diff", "-U1", "--", "tests/test_readme_install.py", "tests/test_cli.py"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "-U3", "HEAD^", "HEAD", "--", "tests/test_cli.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_readme_install.py", "tests/test_cli.py"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "rev-parse", "v0.1.1", "v0.1.0"]` → exit 128
- `["git", "diff", "-U1", "HEAD^", "--", "tests/test_cli.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
....................................................................................................... [ 48%]
........................................................................ [ 81%]
.......................................          [100%]
214 passed, 137 subtests passed in 163.27s (0:02:43)

```

## Actions

- run: ['git', 'status', '--short']
- run: ['git', 'log', '--oneline', '--decorate', '-10']
- run: ['git', 'for-each-ref', 'refs/tags']
- recall
- read_file: README.md
- recall
- run: ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code} v0.1.1\n', 'https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh']
- recall
- read_file: tests/test_readme_install.py
- run: ['git', 'diff', '-U0', '--', 'README.md']
- run: ['git', 'diff', '-U0', '--', 'tests/test_cli.py']
- read_file: tests/test_cli.py
- read_file: CHANGELOG.md
- run: ['git', 'status', '--short']
- read_file: README.md
- run: ['git', 'diff', '-U2', '--', 'README.md', 'tests/test_readme_install.py']
- read_file: tests/test_cli.py
- run: ['git', 'log', '--oneline', '--decorate', '-10']
- recall
- run: ['git', 'restore', '--source=HEAD^', '--worktree', '--', 'tests/test_cli.py']
- run: ['git', 'for-each-ref', 'refs/tags']
- run: ['git', 'status', '--short']
- read_file: README.md
- read_file: tests/test_readme_install.py
- run: ['git', 'ls-remote', '--tags', 'origin']
- run: ['git', 'tag', '--list']
- run: ['git', 'for-each-ref', 'refs/tags']
- run: ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}\\n', 'https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh']
- run: ['git', 'diff', '-U0', '--', 'README.md']
- run: ['git', 'log', '--oneline', '-6']
- run: ['git', 'diff', '-U1', '--', 'tests/test_readme_install.py', 'tests/test_cli.py']
- read_file: tests/test_readme_install.py
- run: ['git', 'status', '--short']
- read_file: CHANGELOG.md
- run: ['git', 'grep', '-n', '-e', 'install.sh', '-e', 'raw.githubusercontent', 'HEAD', '--', 'tests/test_cli.py']
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- run: ['git', 'diff', '-U3', 'HEAD^', 'HEAD', '--', 'tests/test_cli.py']
- delete_file: tests/test_probe_release_url.py
- delete_file: tests/test_probe_tags.py
- run: ['git', 'restore', '--source=HEAD^', '--worktree', '--', 'tests/test_cli.py']
- write_file: tests/test_cli.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_readme_install.py', 'tests/test_cli.py']
- run: ['git', 'status', '--short']
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'rev-parse', 'v0.1.1', 'v0.1.0']
- run: ['git', 'commit', '--only', '-m', 'Pin the README install commands to the v0.1.1 release installer', '-m', 'The install, update and uninstall commands named a default-branch install-script URL, which is not the release the page describes and cannot be reproduced later. Point all three at the published v0.1.1 release installer, restore the release-pinned README assertion in tests/test_cli.py, and make tests/test_readme_install.py require exactly one release selector equal to the current release while still rejecting the stale v0.1.0 path, a divergent tag and a branch URL.', '--', 'README.md', 'tests/test_readme_install.py', 'tests/test_cli.py']
- run: ['git', 'diff', '-U1', 'HEAD^', '--', 'tests/test_cli.py']
