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
| Created | 2026-11-23T12:28:35+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit found the README's install documentation out of step with the installer release it is meant to describe, and nothing in the suite stops a stale install-script URL from coming back. The reader is told to fetch an installer ref that no longer matches the script that carries the login-shell PATH block, and the update and uninstall commands are documented separately, so any one of them can drift without the suite noticing. The task must leave the three documented commands pinned to the intended release installer and add a documentation guard that fails when any of them, or an older install-script path, reappears.

**Outcome:** README.md documents exactly one install-script URL, from the intended release tag v0.1.1, shared by the install, update and uninstall commands; no `/v0.1.0/install.sh` string remains anywhere in the file; and `tests/test_readme_install.py` carries assertions for all three commands so that changing any one of them, or reintroducing the stale path, makes the suite fail. The full test suite still passes without network access, and the fact that the v0.1.1 tag is not yet published is recorded as a known gap rather than fixed by creating or moving a tag or by falling back to v0.1.0.

## Product Intent

The product offers exactly one one-command install path: fetch install.sh and pipe it into a shell. That script owns the login-shell detection, the single marked PATH block in the profile the login shell reads, and the fresh-shell verification that makes a new terminal find `forgel-code`. Documentation that points at an older installer advertises behaviour the old script does not have, so the documented command must name the installer release that implements it, and a suite guard must keep it that way.

## User Experience

A new user copies one command from the README, runs it, and gets the installer that writes the marked PATH block into the profile their login shell reads and then verifies in a fresh login shell that `forgel-code` resolves. The update section repeats that same command, and the uninstall section runs the same script with `--uninstall`, so all three documented actions operate on the same installer. Nobody is sent to an older installer that lacks the PATH handling the prose promises.

## Roadmap

—

## Goals

- README.md's install, update and uninstall commands all use the intended release installer at v0.1.1.
- No stale `/v0.1.0/install.sh` path remains in README.md.
- A documentation guard asserts all three commands and the absence of the stale path, and demonstrably fails when either is violated.
- The suite passes offline and no release tag is created, moved or promised.

## Non-Goals

- Creating, moving or promising any release tag; the runtime release train owns tags and versions
- Falling back to the newest published tag (v0.1.0) because v0.1.1 is unpublished
- Changing install.sh behaviour, its default `FORGEL_CODE_TAG`, or the install command in its header comment
- Changing the engine, the client code, packaging or the build backend
- Requiring any network access, HTTP status assertion or live URL fetch as part of the test suite
- Asserting that `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh` returns HTTP 200 before the release train publishes the tag
- Adding documentation beyond the install, update and uninstall commands this task corrects

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: the client is installed as `forgel-code`, a Python client with a Pareto 20/80 scope that imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-002: the client is a thin UI over the engine's parameterized commands; model access, sandbox, QA, review and release approval stay in the engine. | User, 2026-11-16 18:31 |
| — | D-006: work proceeds engine commands first, then the client repository and console move, then removal of the replaced chat mode. | User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: R1: README.md's install section leads with exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh`.
- **FR-2**: R2: README.md's update section shows exactly that same command, character for character.
- **FR-3**: R3: README.md's uninstall section shows exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh -s -- --uninstall`.
- **FR-4**: R4: README.md contains no occurrence of the string `v0.1.0/install.sh`.
- **FR-5**: R5 (amended): when the behaviour the README describes exists only on the default branch because the intended tag is not yet published, the README keeps the intended release tag v0.1.1 and the unpublished tag is recorded as a known gap in the task report; substituting an earlier published tag such as v0.1.0 is forbidden.
- **FR-6**: R6: `tests/test_readme_install.py` pins the intended release tag in one constant and asserts R1, R2 and R3 as full expected command strings, so that changing a URL, a flag or the `| sh` form in any of the three sections makes the module fail.
- **FR-7**: R7: `tests/test_readme_install.py` asserts R4, so a reintroduced stale install-script path fails the module.
- **FR-8**: R8: `tests/test_readme_install.py` performs no network I/O: it reads files only, so the guard passes and fails identically offline.
- **FR-9**: R9 (amended): the suite never asserts an HTTP status for the v0.1.1 installer URL; the post-release publication of that tag is verified by the release train and its audit, not by this test module or by a command check in this task.
- **FR-10**: R10: the pre-existing documentation guards in `tests/test_readme_install.py` (single install-script URL, no alternative main install path, no editable install, Tests section, prerequisites) keep their current strength and keep passing.
- **FR-11**: R11: the full suite, `python -m unittest discover -s tests`, passes with no environment variable or marker excluding a test.
- **FR-12**: R12: the task report records the observed HTTP status of `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh` at commit time and states that a 404 is the expected, recorded known gap until the release train publishes the tag.

## Technical Requirements

- All committed artifacts are English (project rule).
- Do not weaken an existing test to make the change pass; strengthen the product or the test's premise instead (repository rule).
- A published tag is immutable; agents do not assign, promise or rewrite release versions or tags (FORGEL.md, AGENTS.md ## Release Rules).
- No new runtime or test dependency: the suite runs on the standard library (README `## Tests`).
- No network access in unit tests; the suite must pass offline.
- Keep the change to one logical documentation fix plus its guard; leave unrelated README prose stable.
- Commit in English, imperative mood, with `git commit -s`, and without tool attribution lines.

## User Stories

- As a new user, I want the README's install command to fetch the installer that writes the PATH block and verifies it, so that a new terminal finds `forgel-code`.
- As a maintainer, I want the install, update and uninstall commands guarded by a test, so that a stale installer URL cannot be committed unnoticed.
- As a release auditor, I want the unpublished-tag gap recorded rather than patched, so that no agent creates or moves a release tag.

## Tests

- A1: `python -m unittest discover -s tests -p test_readme_install.py`
- A2: `python -m unittest discover -s tests -p test_readme_install.py`
- A3: `python -m unittest discover -s tests -p test_readme_install.py`
- A4: `sh -c ! grep -F 'v0.1.0/install.sh' README.md`
- A5: `sh -c set -eu; d=$(mktemp -d); mkdir "$d/tests"; cp tests/test_readme_install.py "$d/tests/"; sed 's#code/v0\.1\.1/install\.sh#code/v0.1.0/install.sh#g' README.md > "$d/README.md"; grep -F 'v0.1.0/install.sh' "$d/README.md" >/dev/null; if python -m unittest discover -s "$d/tests" -p 'test_readme_install.py' >"$d/out" 2>&1; then echo 'guard did not fail on a stale README' >&2; cat "$d/out" >&2; exit 1; fi; grep -q 'stale install script' "$d/out"; echo ok`
- A6: `sh -c ! grep -nE 'urllib|http\.client|requests|socket|curl' tests/test_readme_install.py`
- A7: `sh -c curl -fsS -o /dev/null -w '%{http_code}' https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | grep -qx 200`
- A8: `python -m unittest discover -s tests`
- A9: review
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: A1: README.md's install section leads with `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh`, and the guard module passes on the committed file.
- **AC-2**: A2: README.md's update section shows exactly the same command as the install section, and the guard module asserts it.
- **AC-3**: A3: README.md's uninstall section shows exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh -s -- --uninstall`, and the guard module asserts it.
- **AC-4**: A4: `grep -F 'v0.1.0/install.sh' README.md` finds nothing.
- **AC-5**: A5: The guard bites — on a temporary copy of README.md in which `code/v0.1.1/install.sh` is replaced by `code/v0.1.0/install.sh`, the guard module fails for both the install and the uninstall command.
- **AC-6**: A6: `tests/test_readme_install.py` contains no network client import or fetch, so it needs no network.
- **AC-7**: A7: The URL form the README uses is real: the same host answers 200 for the published `main` ref of `install.sh`.
- **AC-8**: A8: The full suite, `python -m unittest discover -s tests`, passes.
- **AC-9**: A9: The task report records the status of the v0.1.1 installer URL at commit time and that its publication is a known gap owned by the release train.

## Scope Boundaries

- README.md: the install command, the update command and the uninstall command all name the release installer at the intended tag v0.1.1
- README.md: no occurrence of the stale install-script path `/v0.1.0/install.sh`
- README.md: the prose around those commands stays consistent with a single install-script URL shared by install, update and uninstall
- tests/test_readme_install.py: explicit assertions that the install command, the update command and the uninstall command each equal the release installer form
- tests/test_readme_install.py: an assertion that the stale v0.1.0 install-script path is absent
- Recording, in the task report, that the v0.1.1 tag is not yet published and that the documented URL therefore answers 404 until the release train publishes it
- Creating, moving or promising any release tag; the runtime release train owns tags and versions
- Falling back to the newest published tag (v0.1.0) because v0.1.1 is unpublished
- Changing install.sh behaviour, its default `FORGEL_CODE_TAG`, or the install command in its header comment
- Changing the engine, the client code, packaging or the build backend
- Requiring any network access, HTTP status assertion or live URL fetch as part of the test suite
- Asserting that `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh` returns HTTP 200 before the release train publishes the tag
- Adding documentation beyond the install, update and uninstall commands this task corrects

## Risks

- The v0.1.1 tag is not published, so the documented URL answers 404 today; anyone who copies the command before the release train publishes the tag gets an error. This is recorded as a known gap, not fixed here, because tags belong to the release train.
- install.sh itself still defaults `FORGEL_CODE_TAG` to `v0.1.0` and its header comment shows the `v0.1.0` URL; once v0.1.1 is published, the documented command fetches a script that would install the v0.1.0 source. That inconsistency is outside this task's scope and needs a follow-up audit item.
- A guard that only greps for one stale string can pass while a differently worded stale path survives; the negative control is what proves the guard bites on the install and uninstall commands.
- The negative control copies README.md and the guard module into a temporary directory; if the module later depends on another repository file, that copy approach breaks and must be updated with it.
- The `main` ref used by A7 can legitimately change, so that check proves the URL form, not the file's content; it must never be read as proof that v0.1.1 exists.

## Open Questions

- None.

## Affected Files

- README.md
- tests/test_readme_install.py

## Assumptions

- The intended release tag is v0.1.1: it is what the README's install, update and uninstall commands and its pinned-revision test line already name, and what the guard module's `INSTALL_TAG` pins.
- A pinned tag URL is preferred over a versionless `latest` URL, because the existing guard compares the tag exactly and a versionless URL would weaken that comparison.
- The guard module may be extended in place; its existing helper functions are reusable and need no rewrite.
- The pre-existing README strings already carry v0.1.1 in the install, update and uninstall commands as read at specification time; the deliverable therefore centres on the guard plus any residual stale string, and the coder verifies rather than assumes the README state.
- The v0.1.1 tag's publication is a separate event owned by the release train; this task neither waits for it nor blocks on it.

## Related Documents

- AGENTS.md
- FORGEL.md
- CHANGELOG.md
- releases/0.1.0/release.md

## Revision History

- v1: initial specification.
- v2: removed the unsatisfiable network requirement for HTTP 200 on the unpublished v0.1.1 installer URL and removed the fallback to the newest published tag; the unreleased tag is now recorded as a known gap (R5, R9, R12, A9), matching the Risks section and FORGEL.md ## Releases.

## External Dependencies

- **GitHub raw content host (raw.githubusercontent.com)** — mode `unknown`; interface: `GET https://raw.githubusercontent.com/forgel-dev/code/<ref>/install.sh` returns 200 with the script body for a published ref (`main`, `v0.1.0`) and 404 for an unpublished ref (`v0.1.1`). The README only embeds this URL as text; the implementation must not fetch it in tests.; docs: https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files; evidence: —
