# Task Spec: Release audit: --uninstall omits ~/.bashrc, although the previous installer wrote the marked bl

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: --uninstall omits ~/.bashrc, although the previous installer wrote the marked bl |
| Project | — |
| Task | `20261122034544_release-audit-uninstall-omits-bashrc-alt` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T03:56:46+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The installer writes a marked PATH block for bash into ~/.bashrc (when ~/.bashrc existed or when no ~/.bash_profile existed), but `install.sh --uninstall` does not consider ~/.bashrc among the files it cleans. After an upgrade followed by an uninstall, the stale marked block stays behind in ~/.bashrc, so the removed installation's PATH entry survives the uninstall and contradicts the uninstall result.

**Outcome:** `install.sh --uninstall` removes the installer's marked block from every shell startup file the installer can write it to, including ~/.bashrc, leaves all other content of those files byte-for-byte unchanged, is safe to run repeatedly, and the repository test suite covers the bash/~/.bashrc case and still passes.

## Product Intent

—

## User Experience

—

## Goals

- `install.sh --uninstall` removes the installer's marked PATH block from ~/.bashrc as well as from the other startup files it already handles.
- Upgrade followed by uninstall leaves no stale forgel-code block in any shell startup file the installer may have written.
- The regression is covered by automated tests and the existing suite still passes.

## Non-Goals

- Changing which shell startup files the installer writes to, or changing the marker text/format
- Adding new installer features, flags or output formats beyond what the uninstall path already provides
- Editing README.md, CHANGELOG.md, pyproject.toml, releases/ or any Python module under forgel_code/
- Rewriting or reformatting install.sh beyond the defect
- Cleaning startup files of shells the installer never writes to
- Removing a real user's files or invoking the uninstaller against a real home directory during tests

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code; it is installed as `forgel-code` and imports nothing from the engine. | User decision log, accepted proposal 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: The uninstall path of install.sh must treat ~/.bashrc as a file that can contain the installer's marked block, in addition to the files it already handles.
- **FR-2**: The set of files the uninstall path cleans must be a superset of the set of files the install path can write the marked block to for bash, i.e. both the ~/.bash_profile branch and the ~/.bashrc branch.
- **FR-3**: Uninstall must remove the block delimited by the installer's existing begin/end marker lines, and must leave every other line of the file unchanged in content and order.
- **FR-4**: Uninstall must not fail, and must not modify a file, when a candidate startup file is missing, unreadable or contains no marked block.
- **FR-5**: Running uninstall twice must produce the same result as running it once: the second run finds no marked block and leaves the files unchanged.
- **FR-6**: The fix must not change the install path's behaviour: a fresh install still writes exactly one marked block into the same file it selected before.
- **FR-7**: tests/test_install.py must contain a regression test whose name contains `bashrc`; it sets up a temporary HOME with a ~/.bashrc containing the marked block written by the install path (no ~/.bash_profile present, or ~/.bashrc present), runs the uninstall, and asserts the block is gone and unrelated lines survive.
- **FR-8**: tests/test_install.py must contain an idempotence test whose name contains `idempotent`; it runs uninstall twice against the same temporary HOME and asserts the file is unchanged between the two runs and free of markers.
- **FR-9**: All tests must operate on a temporary HOME (or equivalent environment override already used by the suite) and must never read or write the invoking user's real startup files.
- **FR-10**: install.sh must remain syntactically valid POSIX sh compatible with the interpreter it already declares.

## Technical Requirements

- Keep install.sh in the shell dialect it already uses; do not introduce new runtime dependencies such as python, perl or GNU-only flags unless already used by the script.
- Only the uninstall file set and the related tests change; the install path, marker text and CLI surface stay as they are.
- Tests stay hermetic: temporary HOME under the test's temporary directory, restored afterwards; no network access.
- Do not weaken or delete an existing test to make the suite pass; fix the product or the test's premise.
- Follow the repository rule to work autonomously and record assumptions in the change report; commits in English, imperative mood, no tool attribution lines.

## User Stories

- As a user who upgraded forgel-code and then ran `install.sh --uninstall`, I want the old PATH block removed from ~/.bashrc so that no stale installation path lingers in a new terminal.
- As a maintainer, I want the uninstall file set to match the install file set so that any file the installer writes is also cleaned by the uninstaller.
- As a developer, I want a regression test for the ~/.bashrc case so that the file-set drift cannot come back silently.

## Tests

- A simulated install into a bash home with the block in ~/.bashrc, followed by `--uninstall`, leaves no block or marker line: `python -m pytest -q tests/test_install.py -k bashrc`
- Unrelated lines in the cleaned startup file are preserved byte-for-byte: `python -m pytest -q tests/test_install.py -k bashrc`
- A second `--uninstall` run leaves every candidate startup file unchanged, and missing or block-free files do not fail the uninstall: `python -m pytest -q tests/test_install.py -k idempotent`
- The full existing test suite passes: `python -m pytest -q`
- install.sh remains syntactically valid in its shell dialect: `sh -n install.sh`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: After a simulated install for a bash home whose selected target is ~/.bashrc, running `install.sh --uninstall` leaves ~/.bashrc without the marked block and without any leftover marker line.
- **AC-2**: Unrelated lines in the cleaned startup file are preserved byte-for-byte (verified by comparing the file against a fixture with only the block removed).
- **AC-3**: A second `--uninstall` run leaves every candidate startup file unchanged.
- **AC-4**: A missing or block-free candidate startup file does not make uninstall fail (exit status remains the script's normal success status).
- **AC-5**: The regression test containing `bashrc` passes.
- **AC-6**: The idempotence test containing `idempotent` passes.
- **AC-7**: The full existing test suite passes.
- **AC-8**: install.sh passes a shell syntax check.

## Scope Boundaries

- install.sh: the file set and logic used by the uninstall path to find and strip the installer's marked block
- install.sh: keep the uninstall path aligned with the install path, so any file the installer may write to is also uninstalled from
- tests/test_install.py: a regression test for a bash home where the marked block lives in ~/.bashrc
- tests/test_install.py: a test that uninstall is idempotent and does not damage unrelated file content
- Changing which shell startup files the installer writes to, or changing the marker text/format
- Adding new installer features, flags or output formats beyond what the uninstall path already provides
- Editing README.md, CHANGELOG.md, pyproject.toml, releases/ or any Python module under forgel_code/
- Rewriting or reformatting install.sh beyond the defect
- Cleaning startup files of shells the installer never writes to
- Removing a real user's files or invoking the uninstaller against a real home directory during tests

## Risks

- If the test harness cannot redirect HOME for the script, a regression test may touch the developer's real ~/.bashrc; the test must use an explicit temporary HOME argument or environment override.
- If the install path selects ~/.bash_profile rather than ~/.bashrc in the test's HOME layout, the regression test will not reproduce the audit finding; the fixture must match the described bash branch (no ~/.bash_profile, or ~/.bashrc present).
- Byte-for-byte preservation is easy to break with a sed/temp-file rewrite that drops or reorders a trailing newline; the test must compare exact content.
- A GNU-only sed/mktemp flag would silently pass locally and fail on other platforms; keep flags POSIX-compatible.
- The milestone wants a new terminal to find forgel-code on PATH; this task only removes the stale block on uninstall and does not itself guarantee PATH resolution after install.

## Open Questions

- None.

## Affected Files

- install.sh
- tests/test_install.py

## Assumptions

- The defect is in the uninstall path's list of candidate startup files, not in the install path's selection logic; the install path already writes the bash block into ~/.bashrc in the described cases.
- The marked block uses the same begin/end marker lines the existing suite asserts on; the fix reuses them rather than introducing new markers.
- The existing test suite already provides a way to redirect HOME (or to invoke the script with an overridden home) for install.sh tests; the new tests reuse that mechanism.
- Cleaning any candidate file that does not exist or has no block is already the uninstall path's tolerant behaviour; the fix extends the candidate list, it does not add new error handling semantics.
- pytest is available in the development environment (the repository has a .pytest_cache directory); the suite is runnable with `python -m pytest`.
- No documentation change is needed because the task intent names only the uninstall behaviour and existing tests.

## Related Documents

- README.md
- CHANGELOG.md
- releases/0.1.0/release.md

## Revision History

- v1: initial specification for the release-audit finding that --uninstall omits ~/.bashrc

## External Dependencies

- **POSIX shell (sh) executing install.sh** — mode `direct`; interface: Run `install.sh` through the host POSIX shell; `tests/test_install.py` exercises the uninstall path with a temporary `HOME`.; docs: POSIX.1-2017 Shell Command Language (XCU), section 2; evidence: `install.sh` is the repository's shell installer entrypoint and `tests/test_install.py` is the installer/uninstaller test module named by the dependency contract; the environment contract (`environment.yaml`, described in `AGENTS.md`) declares the project's commands, and `/bin/sh` is the local executable.
- **pytest test runner** — mode `direct`; interface: `python -m pytest` runs `tests/test_install.py` and the full `tests/` suite.; docs: https://docs.pytest.org/en/stable/how-to/usage.html; evidence: The project environment contract (`environment.yaml`, listed in `AGENTS.md`) supplies the test commands, and `tests/test_install.py` is the installer test module; the dependency contract specifies `python -m pytest` as the runner.
