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
| Created | 2026-11-23T13:29:47+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit reports that the documented installation command in README.md still points at a pinned release installer path, so a user who copies it installs an obsolete script, and nothing in the suite fails when a documented command drifts to an old or divergent install-script URL. The previous specification of this task also left the completion step undecidable: it declared the agent's git read-only and left the commit to the runtime, while the worktree already carries unrelated modifications, so the runtime could not tell which paths belonged to the task, the repository stayed uncommitted, and the acceptance item 'the task repository is committed' with its exact three-path commit could never pass.

**Outcome:** README.md's install, update and uninstall commands all name one and the same canonical release-installer URL that is not pinned to a release tag; tests/test_readme_install.py guards that rule and fails the suite when a documented command carries a stale tag, a divergent tag or another branch; and the change is finished by the agent itself with a path-limited commit that lists exactly README.md, tests/test_readme_install.py and tests/test_cli.py, leaving install.sh, tests/test_install.py, tests/test_check_cleanup.py and CHANGELOG.md uncommitted in the worktree.

## Product Intent

Forgel Code is a thin console client distributed as a separate public repository in the Forgel organization (D-001, D-005) and installed as `forgel-code` (D-004). A user installs it with one command from the public repository, so the documented command must fetch the installer the project actually maintains, and the documentation must not freeze at a release the project has superseded.

## User Experience

A user opens the README, copies the single install command, the update command or the uninstall command, and each of them runs the same current installer. A later edit that reintroduces an old release path or a divergent install-script URL makes the test suite fail before that edit reaches a release.

## Roadmap

—

## Goals

- Every install-script command the README documents uses one canonical, tag-free release-installer URL.
- The suite fails when a documented install-script command regresses to a stale tag, a divergent tag or another branch.
- The task is committed by the agent with a path-limited commit that lists exactly README.md, tests/test_readme_install.py and tests/test_cli.py, so the completion step never has to guess the change set again.

## Non-Goals

- Changing the PATH behaviour of install.sh: it is a separate change whose files are already modified in the worktree.
- Publishing a release, creating or moving a tag, or assigning a version number.
- Editing CHANGELOG.md: the release train owns the changelog and the file already carries unrelated modifications.
- Changing the client's commands, output format or engine calls.
- Rewriting the Windows fallback or any other README section beyond the install-script URLs.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-001: The interactive client moves to a separate public repository in the same organization as the engine. | User decision log, 2026-11-16 21:14 |
| — | D-004: The client's working name is Forgel Code; it is a Python client installed as `forgel-code`. | User decision log, 2026-11-16 18:34 |
| — | D-005: The second repository is public and lives in the same organization as the first (`forgel-dev`). | User decision log, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: R1: The `## Install` section's first runnable command is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh`.
- **FR-2**: R2: The `### Update` command block shows the same one-line installer command.
- **FR-3**: R3: The `### Uninstall` command block shows exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh -s -- --uninstall`.
- **FR-4**: R4: No install-script path in README.md is pinned to a release tag: the text contains no match of `/v<digit><non-space, non-slash characters>/install.sh`, in particular no `v0.1.0/install.sh` and no `v0.1.1/install.sh`.
- **FR-5**: R5: README.md contains at least two install-script URLs and exactly one distinct one, `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`.
- **FR-6**: R6: In the `## Install` section no other installation path appears before the one-line installer: no `pip install`, `pip3 install`, `python -m venv`, `python3 -m venv`, `pipx` or `--user` token appears above it.
- **FR-7**: R7: Outside the Windows fallback line and the single `[test]`-extra `pip install` line in the `## Tests` section, README.md names no other main installation path (`pipx`, `python -m venv`, `python3 -m venv`, `pip install`, `--user`) and no editable install (`-e` as a word of its own, `--editable`).
- **FR-8**: R8: tests/test_readme_install.py contains a guard that reads README.md and fails with an AssertionError when R1 to R7 are violated; the guard needs no network, no environment variable and no particular working directory, and is not skipped.
- **FR-9**: R9: The guard proves its teeth: the same assertions are run on mutated input where an install-script URL carries a stale tag, where it points at a divergent release tag and where it uses another branch, and the AssertionError is required. No existing test is weakened, removed or skipped to make this change pass.
- **FR-10**: R10: The agent finishes the task itself and performs the commit. It stages and commits exactly README.md, tests/test_readme_install.py and tests/test_cli.py with a path-limited stage and commit — `git add -- README.md tests/test_readme_install.py tests/test_cli.py` followed by `git commit -- README.md tests/test_readme_install.py tests/test_cli.py`, or the single equivalent `git commit --only -- README.md tests/test_readme_install.py tests/test_cli.py`. It never uses `git add -A`, `git add .`, `git commit -a`, `git stash`, `git checkout --`, `git restore` or `git reset`, and it never adds install.sh, tests/test_install.py, tests/test_check_cleanup.py, CHANGELOG.md or any other modified file to the commit.
- **FR-11**: R11: After the commit the agent verifies with `git show --name-only --format= HEAD` that the commit lists exactly README.md, tests/test_cli.py and tests/test_readme_install.py, and reports the commit hash and the files that remain modified in the worktree. The commit message is English, states that the README install, update and uninstall commands now use the canonical release installer, and carries no tool attribution or session reference.

## Technical Requirements

- The guard uses only the Python standard library (unittest, pathlib, re) and runs under both runners README.md documents (`python -m unittest discover -s tests` and `python -m pytest -q`).
- The change keeps README.md's other documented content — install options, shell-profile table, command table, output, timeout and tests sections — as it is.
- All committed artifacts and the commit message are English; no tool attribution lines and no session references.
- The whole working tree is never committed: the commit is path-limited to the three named paths and the unrelated modifications stay uncommitted.
- The versionless default-branch URL is used rather than a pinned release path, so the documented command cannot freeze at an obsolete release; the task creates and moves no tag and assigns no version.
- The agent's git is writable for this task and the agent performs the commit; no other step decides or performs the commit.
- The check that fetches the documented URL needs outbound HTTPS to raw.githubusercontent.com.

## User Stories

- As a new user I want the README's single install command to fetch the current installer so that I do not end up on an obsolete release.
- As a maintainer I want the suite to fail when a documented install-script command drifts to a stale or divergent URL so that the release audit does not find it first.
- As the developer of this task I want an explicit completion contract so that my commit contains exactly this change and the unrelated worktree modifications stay out of it.

## Tests

- A1: `python -m unittest tests.test_readme_install -v`
- A2: `bash -c awk '/^### Update$/{f=1;next} /^#/{f=0} f' README.md | grep -Fx -e 'curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh'`
- A3: `bash -c awk '/^### Uninstall$/{f=1;next} /^#/{f=0} f' README.md | grep -Fx -e 'curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh -s -- --uninstall'`
- A4: `bash -c ! grep -nE '/v[0-9][^[:space:]/]*/install\.sh' README.md`
- A5: `bash -c test "$(grep -oE 'https?://[^[:space:]]*/install\.sh' README.md | sort -u | wc -l)" -eq 1`
- A6: `python -m unittest tests.test_readme_install -v`
- A7: `python -m unittest tests.test_readme_install -v`
- A8: `python -m unittest discover -s tests`
- A9: `bash -c test "$(git show --name-only --format= HEAD | sed '/^$/d' | sort | tr '\n' ' ')" = "README.md tests/test_cli.py tests/test_readme_install.py "`
- A10: `bash -c for p in install.sh tests/test_install.py tests/test_check_cleanup.py CHANGELOG.md; do git show --name-only --format= HEAD | grep -qxF "$p" && exit 1; done; for p in install.sh tests/test_install.py tests/test_check_cleanup.py; do test -n "$(git status --porcelain -- "$p")" || exit 1; done; exit 0`
- A11: review
- A12: review
- A13: `curl -fsSIL --max-time 20 -o /dev/null -w %{http_code} https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: A1: The first runnable command of the README `## Install` section is the canonical one-line installer.
- **AC-2**: A2: The README `### Update` block contains the canonical one-line installer.
- **AC-3**: A3: The README `### Uninstall` block contains exactly the canonical uninstall one-liner with `-s -- --uninstall`.
- **AC-4**: A4: README.md contains no install-script path pinned to a release tag.
- **AC-5**: A5: README.md documents exactly one distinct install-script URL.
- **AC-6**: A6: No alternative main installation path precedes the one-liner in the install section, and none appears elsewhere except the Windows fallback and the `[test]` extra line.
- **AC-7**: A7: The suite's README guard rejects a stale tag, a divergent tag and another branch, and those negative cases run in the same suite as the positive ones.
- **AC-8**: A8: The whole test suite passes with the command README.md documents.
- **AC-9**: A9: The task commit lists exactly README.md, tests/test_cli.py and tests/test_readme_install.py.
- **AC-10**: A10: The commit contains none of install.sh, tests/test_install.py, tests/test_check_cleanup.py and CHANGELOG.md, and those pre-existing modifications remain in the worktree.
- **AC-11**: A11: The commit message states the README install-command fix in English and carries no tool attribution or session reference.
- **AC-12**: A12: The agent's report states the commit hash and which files remain modified.
- **AC-13**: A13: The documented install-script URL serves install.sh from the repository's default branch.

## Scope Boundaries

- The install, update and uninstall commands documented in README.md and the rule that all documented install-script URLs are one canonical, tag-free URL.
- The README guard in tests/test_readme_install.py: it must fail, not skip, when a documented install-script URL carries a release tag or comes from another branch.
- The self-executed completion contract: the agent stages and commits exactly README.md, tests/test_readme_install.py and tests/test_cli.py and verifies the commit.
- Changing the PATH behaviour of install.sh: it is a separate change whose files are already modified in the worktree.
- Publishing a release, creating or moving a tag, or assigning a version number.
- Editing CHANGELOG.md: the release train owns the changelog and the file already carries unrelated modifications.
- Changing the client's commands, output format or engine calls.
- Rewriting the Windows fallback or any other README section beyond the install-script URLs.

## Risks

- The README read while writing this specification already names the canonical default-branch URL and the guard module already exists. If the committed tree already satisfies R1 to R9 the agent has no diff, and A9 and A10 cannot pass; the agent must report that state instead of manufacturing a change or padding the commit with unrelated files.
- The fixed change set names tests/test_cli.py. If this work produces no diff there, a path-limited commit lists only two paths and A9 fails. The agent reports that discrepancy and never adds install.sh, tests/test_install.py, tests/test_check_cleanup.py or CHANGELOG.md to make the commit look bigger.
- install.sh still defaults `FORGEL_CODE_TAG` to `v0.1.0` and its own header comment shows a `.../v0.1.0/install.sh` command, so the canonical README URL installs the v0.1.0 archive until the installer's default changes. That file belongs to another task's dirty change set and is out of scope here, but the audit finding is only partly closed by the documentation.
- A path-limited `git commit -- <paths>` produces no commit when none of the three paths has a staged change; the agent must resolve that by doing the real work, not by widening the path list.
- The URL reachability check needs outbound HTTPS; in an offline environment it fails for environmental reasons, not because of the documentation.
- It is tempting to run `git add -A` or `git commit -a`; that pulls install.sh, the installer tests and the changelog into the commit and the reviewer rejects the task.

## Open Questions

- None.

## Assumptions

- The intent allows either the current release installer or a versionless latest URL; the versionless default-branch URL is chosen because the repository's guard already treats a tag-pinned install-script path as a regression.
- The change set is the three paths the accepted completion contract names; tests/test_cli.py is part of it because it carries the client-side command-table assertion that mirrors the README, and it stays green without a weakened test.
- install.sh, tests/test_install.py, tests/test_check_cleanup.py and CHANGELOG.md are other work in the same worktree and belong to no commit of this task.
- Python 3.9 or newer, a POSIX shell and git are available in the task environment, and the suite runs without an engine on PATH.
- The repository's default branch is `main` and install.sh sits at its root, so the canonical URL resolves to this repository's installer.

## Related Documents

- CHANGELOG.md
- AGENTS.md
- FORGEL.md
- releases/0.1.0/release.md

## Revision History

- v1: Initial specification of the README install-command fix and its guard test; it declared the agent's git read-only and left the commit to the runtime.
- v2: R10 and R11 rewritten for the concrete defect the planner reported. The agent now performs the path-limited stage and commit of exactly README.md, tests/test_readme_install.py and tests/test_cli.py itself, verifies the commit with `git show --name-only --format= HEAD`, and reports the hash and the remaining modified files. The statements that the agent's git is read-only and that the runtime performs the commit are dropped; the rule that the whole working tree is never committed stays. R1 to R9 and all acceptance criteria are unchanged.

## External Dependencies

- **git** — mode `unknown`; interface: Path-limited staging and commit, and `git show --name-only --format= HEAD` for verification; docs: https://git-scm.com/docs/git-commit; evidence: —
- **curl** — mode `unknown`; interface: The documented one-liner fetches the installer script over HTTPS and pipes it to a shell; docs: https://curl.se/docs/; evidence: —
- **GitHub raw file host (raw.githubusercontent.com)** — mode `unknown`; interface: Serves install.sh from the forgel-dev/code default branch at the path the README documents; docs: https://docs.github.com/; evidence: —
- **pytest** — mode `unknown`; interface: Second documented runner of the suite; declares the `test` extra in pyproject.toml; docs: https://docs.pytest.org/; evidence: —
