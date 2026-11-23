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
| Created | 2026-11-23T15:03:53+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

README.md still documents the install and uninstall commands against the superseded release installer at `.../v0.1.0/install.sh`. A reader who copies those commands installs a stale release, so a new terminal may not have the current `forgel-code`, and nothing in the test suite notices when the documented commands drift away from the release installer again. The previous specification of this task also demanded agent-side git writes and a `curl` reachability probe, which the agent runtime does not permit.

**Outcome:** README.md documents the install and uninstall commands against the current release installer (a versionless latest URL, or the released version recorded in CHANGELOG.md, never a superseded tag), a repository test guards those documented commands against regressing to a superseded or non-installer source, the full test suite passes, and the change set is committed by the runtime completion step from the paths named in the agent's done report (README.md, tests/test_readme_install.py, tests/test_cli.py), leaving unrelated worktree changes uncommitted.

## Product Intent

A user who copies the documented install command gets the current released `forgel-code` on PATH, and the documentation cannot silently fall behind a release again.

## User Experience

A new user finds the install line in README.md, pastes it into a fresh terminal, and afterwards runs `forgel-code` successfully, because the line points at the current release installer rather than an old tag.

## Roadmap

—

## Goals

- The documented install and uninstall commands point at the current release installer.
- Documentation drift on those commands is caught by a repository test instead of by a user.
- The change lands as a single small change set that the runtime completion step commits without agent git writes or network access.

## Non-Goals

- Changing install.sh behaviour or its arguments.
- Publishing, tagging or rewriting any release; versions come from the release train and its release report.
- Fetching the documented URL over the network to prove reachability.
- Reworking unrelated README sections, the client code or the engine contract.
- Running git write commands or any network client from the agent.
- Adding a new CI configuration or a new test runner.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a Python client installed as `forgel-code`, so the documented install command installs the `forgel-code` package. | User decision log, D-004 (2026-11-16 18:34) |
| — | The client repository is public and lives in the same organization as the engine, so the documented install URL points at a publicly resolvable release location. | User decision log, D-005 (2026-11-16 21:14) |

## Functional Requirements

- **FR-1**: R1: README.md contains no install command that references a superseded release path; in particular the string `v0.1.0/install.sh` does not appear in README.md.
- **FR-2**: R2: The documented install command in README.md invokes the release installer script (`install.sh`) from the release location and is presented as a copy-pasteable, complete shell command.
- **FR-3**: R3: The documented uninstall command in README.md invokes the same release installer script from the release location and is presented as a copy-pasteable, complete shell command.
- **FR-4**: R4: The installer location used in README.md is either a versionless latest-release URL or a URL whose version equals the newest released version recorded in CHANGELOG.md; the agent does not introduce, promise or invent a version.
- **FR-5**: R5: A guard test in `tests/` reads README.md, extracts the documented install and uninstall commands, and fails when either command does not reference the release installer script or references a superseded release path.
- **FR-6**: R6: The guard test fails for the pre-change README.md (a README documenting `v0.1.0/install.sh` does not satisfy it) and passes for the corrected README.md.
- **FR-7**: R7: The guard test performs no network access, spawns no external binary and makes no git call, so it runs under the repository's normal test command.
- **FR-8**: R8: The full repository test suite passes after the change.
- **FR-9**: R9: The change set is exactly README.md, tests/test_readme_install.py and tests/test_cli.py; these three paths are listed in the agent's done report and the runtime completion step commits exactly the listed paths, leaving every other worktree modification uncommitted.
- **FR-10**: R10: The agent inspects the worktree with read-only git commands only (`git status`, `git diff`, `git show`, `git log`) and never runs `git add`, `git commit`, `git reset` or `git checkout`.
- **FR-11**: R11: No reachability or network proof of the documented URL is part of the task; the URL correctness is judged by the documented form and by the guard test, not by a live request.

## Technical Requirements

- The agent's git access is read-only; the runtime completion step performs the commit for the paths named in the done report.
- The agent has no network client available; no `curl`, `wget` or HTTP fetch is part of the change or its verification.
- A published tag is immutable; the task never rewrites a release and never assigns a version.
- Never commit the whole working tree; the change set is the three named paths only.
- Artifacts are written in English.
- The repository test framework is pytest; the guard test uses it and nothing else.
- The specification states behaviour, not an implementation file list; the developer chooses the guard test's internal structure inside `tests/`.

## User Stories

- As a new user, I want the README install line to point at the current release installer, so that a fresh terminal ends up with a working `forgel-code` on PATH.
- As a maintainer, I want a test that fails when the documented install or uninstall command regresses to an old release, so that the docs cannot silently fall behind a release.

## Tests

- A1: README.md no longer contains the superseded `v0.1.0/install.sh` path: `python -c import pathlib,sys; t=pathlib.Path('README.md').read_text(encoding='utf-8'); sys.exit(0 if 'v0.1.0/install.sh' not in t and 'v0.1.0' not in t else 1)`
- A4: the new README guard test passes against the corrected README.md: `python -m pytest tests/test_readme_install.py -q`
- A6: the full repository test suite passes: `python -m pytest -q`
- A2: the documented install command references the release installer and any version matches the newest CHANGELOG release: review
- A3: the documented uninstall command references the release installer on the same terms as A2: review
- A5: the guard test fails against a README documenting a superseded install path: review
- A7: the guard test makes no network call, spawns no external binary and calls no git: review
- A8: the done report lists exactly README.md, tests/test_readme_install.py and tests/test_cli.py and leaves unrelated worktree changes uncommitted: review
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: A1: README.md no longer contains `v0.1.0/install.sh`.
- **AC-2**: A2: The documented install command in README.md references the release installer and, when versioned, that version matches the newest release recorded in CHANGELOG.md.
- **AC-3**: A3: The documented uninstall command in README.md references the release installer on the same terms as A2.
- **AC-4**: A4: The new guard test passes against the corrected README.md.
- **AC-5**: A5: The new guard test fails when run against a README.md that documents a superseded install path.
- **AC-6**: A6: The full test suite passes.
- **AC-7**: A7: The guard test needs no network, no external binary and no git.
- **AC-8**: A8: The agent's done report lists exactly README.md, tests/test_readme_install.py and tests/test_cli.py as the change set, and unrelated worktree modifications are left uncommitted for the runtime completion decision.

## Scope Boundaries

- Correct the documented install command in README.md to the current release installer.
- Correct the documented uninstall command in README.md to the current release installer.
- Add a README guard test in the repository test suite that asserts both documented commands use the release installer.
- Keep the change set limited to README.md, tests/test_readme_install.py and tests/test_cli.py.
- Report the exact changed paths in the agent's done report so the runtime completion step commits exactly those paths.
- Changing install.sh behaviour or its arguments.
- Publishing, tagging or rewriting any release; versions come from the release train and its release report.
- Fetching the documented URL over the network to prove reachability.
- Reworking unrelated README sections, the client code or the engine contract.
- Running git write commands or any network client from the agent.
- Adding a new CI configuration or a new test runner.

## Risks

- The tree contains only `releases/0.1.0`, so a versioned URL chosen by the agent could name a release that does not exist; preferring a versionless latest URL removes this risk.
- If the release location does not serve a versionless installer URL, the guard test must compare against CHANGELOG.md instead of a literal, or the README will go stale again on the next release.
- If the release installer does not support uninstall, restricting the guard to the install command leaves the uninstall documentation uncorrected and A3 cannot be met.
- The guard test can become brittle if it parses prose loosely; it must target the fenced command block and must be shown to fail on the old README (A5).
- Adding `tests/test_cli.py` to the change set without a genuine modification reintroduces the rejected scope problem; that path is declared only when it is actually changed.
- Whoever reads this task may be tempted to reintroduce an agent-side commit or a `curl` probe; both are barred by R10, R11 and the constraints.

## Open Questions

- Does the release installer script provide an uninstall invocation on the same URL? If it does not, the guard test must be limited to the install command and A3 restated, which is a product-visible change to this task's intent.

## Assumptions

- The release installer is published as a script named `install.sh` at a release URL, and the same script serves both install and uninstall, which is why the task asks the guard to cover both commands.
- A versionless latest-release URL form is preferable because it cannot go stale; if the release location does not offer one, the newest version recorded in CHANGELOG.md is used instead.
- The README commands currently live in fenced code blocks whose text the guard test can extract with a small parser or a regular expression over the fenced block.
- CHANGELOG.md is the in-repository source for the newest released version, since the `releases/` directory contains only 0.1.0.
- The guard test may update `tests/test_cli.py` only if a shared helper or a CLI-documentation assertion already lives there; otherwise that file is untouched and still listed in the declared change set only if modified.

## Related Documents

- README.md
- install.sh
- CHANGELOG.md
- tests/test_readme_install.py
- tests/test_cli.py
- releases/0.1.0/release.md
- FORGEL.md
- AGENTS.md
- code/FORGEL.md
- code/AGENTS.md

## Revision History

- v1: initial specification requiring an agent-side `git commit --only` and a `curl` reachability check.
- v2: rewritten after rejection — the commit is performed by the runtime completion step for the paths listed in the agent's done report (README.md, tests/test_readme_install.py, tests/test_cli.py), unrelated worktree changes stay uncommitted, and the agent-side git write and `curl` reachability steps are removed.

## External Dependencies

- **Release installer script published as a release asset (`install.sh`) under the project's release URL on the public code repository host** — mode `unknown`; interface: HTTPS GET of a shell script from a release path; the documented command pipes or executes that script. Only the URL form is used in this task, never a live request.; docs: releases/0.1.0/release.md (release report describing the published install command); no 0.1.1 release report present in the tree; evidence: —
