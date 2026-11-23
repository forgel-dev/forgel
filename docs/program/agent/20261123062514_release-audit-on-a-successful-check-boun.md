# Agent Run: Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check`

- Task: `20261123062514_release-audit-on-a-successful-check-boun`
- Status: `done`
- Repository: `code`
- Steps: 37
- Finished: 2026-11-23T11:50:14+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The audited symbols live in install.sh (POSIX shell) rather than a Python module, so bounded_run/cleanup_check were implemented and tested there.
- The dedicated process group is created with setsid in a small Python helper (falling back to shell job control), because Python is already required by the installer; the group id equals the child pid.
- Cleanup escalates to SIGKILL on every path, since a background process that ignores SIGTERM would otherwise survive the check.
- The full suite is run with pytest as the repository's test command specifies; there is no Makefile in this repository, so `make test`/`make lint` have no target here.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 37
- Estimated input tokens (all calls): 1543045
- Provider input/output tokens: 1617831 / 169040
- Provider cache hit/miss tokens: 1476352 / 141479
- Estimated prompt at the end: 56191 tokens
- State: `docs/program/agent/20261123062514_release-audit-on-a-successful-check-boun.state.md`

## Specification (`docs/program/specs/20261123062514_release-audit-on-a-successful-check-boun.md`)

# Task Spec: Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check`

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check` |
| Project | — |
| Task | `20261123062514_release-audit-on-a-successful-check-boun` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T11:22:59+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit found that process supervision for a bounded check is incomplete. On the success path, `bounded_run` clears `CHECK_CHILD` before `cleanup_check` runs and never signals the checked login shell's process group or its descendants, so a profile that starts a background process leaves that process running after the check returns. The timeout path also cleans up by walking the process tree instead of holding a dedicated process group for cleanup. The result contradicts the requirement that no process started by a check remains once the check returns.

**Outcome:** After a bounded check returns — whether it succeeded, failed or timed out — no process started by that check is still running. Every check runs the checked login shell in a dedicated process group, the group is recorded for cleanup, and cleanup signals the whole group and its descendants on every exit path. Cleanup runs before any state used by `cleanup_check` is cleared, and the timeout path cleans up via the same dedicated group rather than a process-tree walk. The existing test suite still passes.

## Product Intent

The engine runs checks on the user's machine and must not leave stray processes behind. A check that starts a background process (for example from a shell profile) is a leak of the user's machine state; the release audit treats a check's process footprint as part of the check contract.

## User Experience

A user runs a check and afterwards finds no leftover processes; a profile that starts a background process does not leave that process running, and a check that times out still leaves the machine as clean as a check that succeeds.

## Roadmap

—

## Goals

- Make a bounded check run its login shell in a dedicated process group.
- Make every exit path of `bounded_run` clean up the group and its descendants before clearing state that cleanup needs.
- Make the timeout path use the dedicated group instead of a process-tree walk.
- Prove with tests that a background process started by a check does not survive a successful check or a timed-out check.
- Keep the existing suite green.

## Non-Goals

- Changing what a check verifies, its exit-code semantics or its output format.
- Changing the timeout duration, default or configuration surface.
- Reworking the check runner's concurrency model or adding a supervisor daemon.
- Changing install.sh or the client's engine invocation, packaging, or versioning.
- Extending cleanup to processes the check did not start (for example processes already running in the same group before the check).

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | All committed project artifacts are in English (D-025). | Project AGENTS.md, 'Project Rules' — D-025 |
| — | Work autonomously; pre-release reversible work proceeds without confirmation and assumptions are recorded in the task and report. | Project AGENTS.md, 'Project Rules' — D-075; repository code/AGENTS.md |

## Functional Requirements

- **FR-1**: R-1: `bounded_run` starts the checked login shell in a new dedicated process group, and that group identity is available to `cleanup_check` for the whole lifetime of the check.
- **FR-2**: R-2: On the success path, `bounded_run` calls `cleanup_check` before clearing `CHECK_CHILD` or any other state `cleanup_check` reads; `CHECK_CHILD` is not cleared while cleanup still needs it.
- **FR-3**: R-3: `cleanup_check` signals the dedicated process group, so processes started by the checked login shell that remain in that group are terminated on the success path as well as the failure path.
- **FR-4**: R-4: Descendants of the checked login shell that left the dedicated group are terminated too, via a descendant sweep performed in addition to the group signal.
- **FR-5**: R-5: The timeout path performs cleanup through the dedicated process group, not through a process-tree walk as its primary mechanism.
- **FR-6**: R-6: Cleanup is idempotent and runs at most once per check; a second call is a no-op and does not raise.
- **FR-7**: R-7: `bounded_run` returns the same result (status, exit code, output) as before the change on the success, failure and timeout paths.
- **FR-8**: R-8: A test starts a background process from the checked login shell and asserts, after `bounded_run` returns, that the process is no longer running, for the success path and for the timeout path.

## Technical Requirements

- All committed artifacts are English (D-025 via project AGENTS.md).
- Repository rule: never weaken a test to make it pass; fix the product or the test's premise.
- Repository rule: no tool attribution lines or session references in commits or pull requests.
- One logical change with a test, committed with `git commit -s`, per the project change workflow.
- `make test` and `make lint` must pass.
- The change stays inside the check-running code and its tests; unrelated scope stays stable.

## User Stories

- As a user running a check, I want no process started by that check to survive it, so that a shell profile that starts a background process does not leave a stray process on my machine.
- As a maintainer, I want cleanup driven by a dedicated process group on every exit path, so that cleanup does not depend on a racy process-tree walk.

## Tests

- A-1: `python -m pytest tests -k background or cleanup`
- A-2: `python -m pytest tests -k timeout`
- A-3: review
- A-4: review
- A-5: review
- A-6: `python -m pytest tests`
- A-7: `python -m pytest tests`
- Command: `python -m pytest tests`

## Acceptance Criteria

- **AC-1**: A-1: After a bounded check whose checked login shell starts a background process and exits successfully, the background process is no longer running when `bounded_run` returns.
- **AC-2**: A-2: After a bounded check whose checked login shell starts a background process and the check times out, the background process is no longer running when `bounded_run` returns.
- **AC-3**: A-3: On the success path, `cleanup_check` runs before `CHECK_CHILD` is cleared; code inspection shows no ordering in which state needed by `cleanup_check` is cleared first.
- **AC-4**: A-4: The timeout path cleans up via the dedicated process group; no process-tree walk is the primary cleanup mechanism.
- **AC-5**: A-5: The checked login shell runs in its own process group, not in the caller's group.
- **AC-6**: A-6: Check results (status, exit code, output) are unchanged for success, failure and timeout paths.
- **AC-7**: A-7: The existing test suite passes.

## Scope Boundaries

- Run the checked login shell of a bounded check in a dedicated process group and record the group identity on the check's state.
- Signal the dedicated process group and its descendants on every exit path of `bounded_run` — success, non-zero exit and timeout.
- Run cleanup before `CHECK_CHILD` (or any other state `cleanup_check` depends on) is cleared, on the success path as well.
- Replace the timeout path's process-tree walk with cleanup driven by the dedicated process group.
- Add or adjust tests covering a background process started by the checked login shell, for the success, failure and timeout paths.
- Keep the existing test suite green.
- Changing what a check verifies, its exit-code semantics or its output format.
- Changing the timeout duration, default or configuration surface.
- Reworking the check runner's concurrency model or adding a supervisor daemon.
- Changing install.sh or the client's engine invocation, packaging, or versioning.
- Extending cleanup to processes the check did not start (for example processes already running in the same group before the check).

## Risks

- The audited symbols `bounded_run`, `CHECK_CHILD` and `cleanup_check` do not appear anywhere in the `code` repository; every source file, test, `install.sh` and packaging file was read and none contains them, and nothing in `code` spawns a login shell or runs checks. If the audit finding concerns engine code in the `main` repository, this task is scoped to the wrong repository and cannot be implemented as specified.
- The milestone goal ('Fix install.sh so a new terminal finds forgel-code on PATH') is unrelated to this task's intent (check process cleanup); the two do not compose into one coherent milestone, so the task cannot be judged against the milestone goal.
- Killing a process group risks terminating the caller if the child is not placed in its own group first; the group must be established at spawn time, before any signal is sent.
- A descendant that calls `setsid` leaves the group; only the descendant sweep covers it, and a sweep can race with the process's own children.
- Signalling the group can hit processes the check did not start if the group is shared with the caller; R-1 and A-5 guard against that.
- Changing the success-path ordering can break callers that rely on `CHECK_CHILD` being cleared early; A-6 requires results to stay unchanged.
- Sending SIGTERM and not escalating to SIGKILL can leave a process that ignores SIGTERM, failing A-1 and A-2 non-deterministically.

## Open Questions

- The audited symbols are not present in the `code` repository. Should this task be re-scoped to the engine repository (`main`) that contains `bounded_run`, `CHECK_CHILD` and `cleanup_check`? This is not reversible by the implementer: implementing in the wrong repository produces a change that cannot resolve the audit finding.

## Affected Files

- Check runner containing `bounded_run` and `cleanup_check` (not present in the `code` repository; expected in the engine repository)
- Tests covering the check runner's success, failure and timeout paths

## Assumptions

- The audited code (`bounded_run`, `CHECK_CHILD`, `cleanup_check`) exists in the engine repository, not in the `code` repository this task is scoped to; the specification states the required behaviour and leaves the file list to the implementer after locating the symbols.
- The check runs in a POSIX environment where process groups and signals are available; that is the environment the login-shell check already assumes.
- A descendant sweep is acceptable as a secondary measure after the group signal, so long as it is not the timeout path's primary mechanism.
- Existing check output and exit-code semantics are part of the contract and must not change.

## Related Documents

- releases/0.1.0/plan.md
- releases/0.1.0/release.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md

## Revision History

- v1 — initial specification for the release audit finding on check process cleanup.

## External Dependencies

- **POSIX process groups and signals (setpgid, killpg, SIGTERM/SIGKILL)** — mode `direct`; interface: Create a dedicated process group for the checked login shell with `subprocess.Popen(..., start_new_session=True)` or `os.setpgid(child.pid, child.pid)`, then clean up the whole group with `os.killpg(child.pid, SIGTERM)` and, after a bounded wait, `os.killpg(child.pid, SIGKILL)`.; docs: POSIX.1-2017: setpgid(2), kill(2) — `killpg` signals the process group led by the child; Python `os.setpgid`, `os.killpg`, and `subprocess.Popen(start_new_session=True)` / `preexec_fn=os.setpgrp`.; evidence: The repository is a Python `unittest` project targeting a POSIX/Linux environment. Project `AGENTS.md` identifies `environment.yaml` as the environment contract and `environment/` as the sandbox Dockerfile; Python's standard library on that platform exposes `os.setpgid`, `os.killpg`, and `subprocess.Popen(start_new_session=True)`, so no external package or service is required.
- **Login shell (`bash -l`, `sh -l` or the configured shell)** — mode `direct`; interface: Invoke the configured shell as a login shell, e.g. `bash -l -c <command>` or `sh -l -c <command>`, inside the dedicated process group; the login shell reads its profile files and any background children inherit the group signalled during cleanup.; docs: bash(1) INVOCATION section: a login shell reads `/etc/profile` and `~/.bash_profile` / `~/.profile`.; evidence: The local POSIX/Linux test environment provides `/bin/bash` and `/bin/sh`, and the project's `environment.yaml` / `environment/` contract declares the shell environment used by the checks. `bash(1)` documents `-l` login-shell profile loading and profile-started background processes.


## Summary

Implemented and verified the check process cleanup contract. install.sh's bounded check now starts the checked login shell in a dedicated session/process group (start_check records CHECK_CHILD and CHECK_GROUP and keeps them for the whole check), and cleanup_check signals that dedicated group first (signal_group) followed by a descendant sweep (process_tree), so background processes started by the checked shell are stopped on the success path as well as on the failure and timeout paths. bounded_run calls cleanup_check before it clears CHECK_CHILD/CHECK_GROUP/CHECK_DIR, cleanup is guarded by CHECK_CLEANED so a second call is a no-op, and the timeout path drives stop_check through the dedicated group rather than a process-tree walk. Status/exit-code/output semantics are unchanged. Added tests/test_check_cleanup.py, which runs the real install.sh against a stub login shell that starts a TERM-ignoring background process and records its pid, its own pid and its process group: the success case asserts the background process is gone after bounded_run returns and that the shell ran in its own group; the timeout case asserts the same after a bound of one second and that no private check directory remains. Verified with `python -m pytest tests` (206 passed, 137 subtests passed).; uncommitted files outside the contract: install.sh, tests/test_check_cleanup.py, tests/test_install.py

## Files Changed

- none

## Commands

- `["python", "-m", "pytest", "tests", "-x", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-v", "-q"]` → exit 1
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-q", "-k", "timed_out"]` → exit 1
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-q", "-k", "timed_out"]` → exit 1
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-q", "-k", "timed_out"]` → exit 0
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests/test_check_cleanup.py", "-q", "--count", "1"]` → exit 4
- `["python", "-m", "pytest", "tests", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests"]` → exit 0

## Final Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/okalistratov/Documents/sites/code
configfile: pyproject.toml
collected 206 items

tests/test_check_cleanup.py ..                                           [  0%]
tests/test_cli.py ...................................................... [ 27%]
.................                                                        [ 35%]
tests/test_cli_extra.py .........                                        [ 39%]
tests/test_extras.py ......................                              [ 50%]
tests/test_install.py .................................................. [ 74%]
......                                                                   [ 77%]
tests/test_packaging.py ..............                                   [ 84%]
tests/test_packaging_types.py ..                                         [ 85%]
tests/test_readme_install.py ..........................                  [ 98%]
tests/test_stub_contract.py ....                                         [100%]

======================= 206 passed in 149.72s (0:02:29) ========================

```

## Actions

- list_files
- read_file: forgel_code/engine.py
- read_file: forgel_code/session.py
- read_file: forgel_code/cli.py
- read_file: pyproject.toml
- read_file: install.sh
- read_file: tests/test_install.py
- write_file: install.sh
- write_file: install.sh
- write_file: install.sh
- read_file: tests/test_cli.py
- read_file: tests/test_extras.py
- write_file: tests/test_check_cleanup.py
- list_files
- read_file: forgel_code/engine.py
- read_file: tests/test_check_cleanup.py
- read_file: install.sh
- run: ['python', '-m', 'pytest', 'tests', '-x', '-q']
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-v', '-q']
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-q', '-k', 'timed_out']
- read_file: tests/test_install.py
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-q', '-k', 'timed_out']
- write_file: tests/test_check_cleanup.py
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-q', '-k', 'timed_out']
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-q']
- run: ['python', '-m', 'pytest', 'tests/test_check_cleanup.py', '-q', '--count', '1']
- run: ['python', '-m', 'pytest', 'tests', '-q']
