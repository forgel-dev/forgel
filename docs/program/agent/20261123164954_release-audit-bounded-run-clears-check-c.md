# Agent Run: Release audit: bounded_run clears CHECK_CHILD before calling cleanup_check, and install.sh deli

- Task: `20261123164954_release-audit-bounded-run-clears-check-c`
- Status: `done`
- Repository: `code`
- Steps: 13
- Finished: 2026-11-23T16:58:44+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The existing cleanup regression tests and the recorded timeout wording ('stopped after Ns') and private check prefix are the reference for the fix.
- Process-group control uses the Python interpreter the installer already requires; shells without it fall back to job control and a descendant sweep.
- Cleanup is released exactly once per check via a guard flag, so the EXIT trap after a signal trap is a no-op rather than a second signal.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 13
- Estimated input tokens (all calls): 335389
- Provider input/output tokens: 348070 / 7084
- Provider cache hit/miss tokens: 314624 / 33446
- Estimated prompt at the end: 33987 tokens
- State: not needed

## Specification (`docs/program/specs/20261123164954_release-audit-bounded-run-clears-check-c.md`)

# Task Spec: Release audit: bounded_run clears CHECK_CHILD before calling cleanup_check, and install.sh deli

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: bounded_run clears CHECK_CHILD before calling cleanup_check, and install.sh deli |
| Project | — |
| Task | `20261123164954_release-audit-bounded-run-clears-check-c` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T16:52:05+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The fresh-shell check in the installer can leak processes: the bounded check releases its record of the checked shell before the cleanup routine runs, so on the success path the cleanup has nothing to signal and only removes the private temporary directory, letting background processes started by the checked login shell survive the installation. The installer also keeps the checked shell out of a process group of its own while its own description claims otherwise, so even the timeout path has no group to stop. This contradicts the promise that nothing the check started outlives it on every exit path, and the regression test that would have caught it was absent.

**Outcome:** The checked login shell runs as the leader of a process group of its own, and that group (including background processes the shell started) is stopped on every exit path — success, timeout, internal failure and interruption — before the check's recorded state is released. The regression tests for the successful and the timed-out check pass, and the whole existing test suite still passes.

## Product Intent

A new terminal must find the client on PATH, and the installer must verify that in a real fresh login shell without leaving stray processes or temporary directories behind, so a user can install, re-run or cancel the installer safely.

## User Experience

A user runs the one-command installer; it reports success only when a freshly started login shell resolves the client launcher. If the user aborts the installer, or the checked shell starts something in the background, nothing the check started keeps running after the installer exits, and no leftover temporary check directory remains on the timed-out path. A shell that never answers fails the installation with a message naming the elapsed bound instead of blocking forever.

## Roadmap

—

## Goals

- The checked login shell runs in a dedicated process group.
- The dedicated group is stopped on the success path as well as on the timeout path, before the check's state is released.
- No process started by the checked login shell survives the installation on any exit path.
- The script's description of the check matches the implemented behavior.
- The cleanup regression tests and the full existing suite pass.

## Non-Goals

- Changing how the login shell and the profile file are detected
- Changing the content, markers or placement of the PATH block, or the uninstall cleanup of that block
- Changing the client command line, packaging or build backend
- Adding new environment variables or new user-facing options
- Changing the install, re-install or uninstall flow beyond what the cleanup fix requires
- Rewriting the installer as a whole

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-104: A specification states behavior, never an implementation file list; the developer and the reviewer judge the change as a whole. | FORGEL.md / AGENTS.md, D-104 |
| — | D-106: Documentation is text and is verified by review; never add or require an automated check that reads a documentation file. | FORGEL.md / AGENTS.md, D-106 |
| — | D-075: Work autonomously on reversible pre-release work and record assumptions in the task and report. | AGENTS.md, D-075 |

## Functional Requirements

- **FR-1**: The installer starts the checked login shell so that it leads a process group of its own, distinct from the installer's group.
- **FR-2**: In the checked login shell, the observed process group identifier equals the shell's own process identifier.
- **FR-3**: A successful check stops every process in that dedicated group, including background processes the checked login shell started, before the installer reports success.
- **FR-4**: A check that exceeds its time bound stops every process in that dedicated group, including background processes the checked login shell started, and the installation fails with a message stating the bound that elapsed.
- **FR-5**: The check's recorded state is released only after the stop attempt on every exit path — success, timeout, internal failure and interruption — and is released exactly once, so an interruption and the normal return cannot signal the same group twice.
- **FR-6**: No process started by the checked login shell is still running after the installer has exited, on either the success or the timeout path.
- **FR-7**: The private temporary check directory is removed on every exit path, so a timed-out check leaves no directory carrying the check's private prefix behind.
- **FR-8**: The script's own description of the check states that the checked shell is placed in a process group of its own and that the group is stopped on every exit path.
- **FR-9**: The installer never reads its standard input, so it stays safe to pipe into an interpreter.
- **FR-10**: All existing installer behavior unrelated to cleanup — login-shell and profile detection, the opt-out settings, re-install and uninstall — keeps working unchanged.

## User Stories

- As a user installing the client, I want the installer to stop everything its verification shell started, so that after it finishes no stray process keeps running on my machine.
- As a user whose login shell may be slow or misconfigured, I want a hanging verification to fail the installation with a clear message and leave nothing behind, so that I can fix the problem and re-run.
- As a maintainer, I want the installer's stated behavior about the checked shell and its cleanup to match what it actually does, so that I can trust that description.

## Acceptance Criteria

- **AC-1**: When the checked login shell starts a background process and then succeeds, the installer exits successfully and that background process is no longer running.
- **AC-2**: When the checked login shell starts a background process and then hangs past the time bound, the installer exits non-zero, its error output states the elapsed bound, and that background process is no longer running.
- **AC-3**: In both the successful and the timed-out case, the process group identifier recorded for the checked login shell equals the shell's own process identifier.
- **AC-4**: After a timed-out check, no directory carrying the check's private prefix remains in the temporary directory.
- **AC-5**: The regression tests for the successful and the timed-out check cleanup both pass.
- **AC-6**: The full existing test suite passes.
- **AC-7**: The script's description of the check no longer states that the checked shell is kept out of its own process group.

## Scope Boundaries

- Run the checked login shell as the leader of a dedicated process group
- Stop the whole dedicated group on the successful check path, not only on the timeout path
- Release the check's recorded state only after the stop attempt, and release it exactly once per check
- Remove the private temporary check directory on every exit path
- Correct the script's own description of the check so it no longer states that the checked shell stays out of its own process group
- Keep the existing regression tests for the success and timeout cleanup paths as the verification of this behavior
- Changing how the login shell and the profile file are detected
- Changing the content, markers or placement of the PATH block, or the uninstall cleanup of that block
- Changing the client command line, packaging or build backend
- Adding new environment variables or new user-facing options
- Changing the install, re-install or uninstall flow beyond what the cleanup fix requires
- Rewriting the installer as a whole

## Risks

- If the group is not separated correctly, stopping it can also stop the installer, so the installation dies instead of reporting a result.
- Waiting too long for the forceful stop makes the installation appear to hang; waiting too little leaves the check's processes alive on a slow machine.
- Platform differences in process-group behavior can make the cleanup tests pass or fail intermittently instead of deterministically.
- The tests observe real processes and poll for their disappearance, so their outcome depends on timing and machine load.
- Changing the cleanup can alter the timeout message the existing tests rely on and break an unrelated expectation.
- The reported finding spans more than the check lifecycle, so the work can drift into unrelated installer behavior and make the change inconsistent.

## Open Questions

- None.

## Assumptions

- The regression tests already present for the success and timeout cleanup paths encode the expected behavior, including the wording of the timeout message and the private directory prefix, and are the reference for the fix.
- The check already performs a graceful stop followed by a forceful one within a grace period; only the group placement and the cleanup ordering are wrong.
- The private check directory is created under the standard temporary location so its removal can be observed.
- Interruption and internal failure of the installer must clean up the same way as a normal return; that is the intended reading of 'on every exit path'.
- Reporting success requires both a resolved launcher in the fresh shell and a completed cleanup.

## Related Documents

- FORGEL.md
- AGENTS.md
- README.md
- CHANGELOG.md
- releases/0.1.0/release.md

## Revision History

- v1: initial specification for the release-audit finding, restating the dedicated-group and cleanup-ordering behavior as observable outcomes.
- v2: removed implementation and process detail from risks, requirements and constraints; expressed the shell and process facilities as behavior.


## Summary

The change set was already present in the working tree from earlier sessions of this task; this session verified it end to end and made no further edits. install.sh now starts the checked login shell through a small Python launcher that calls setsid() (falling back to setpgid) before exec, so the checked shell leads a process group of its own whose id equals its own pid; the group id is recorded in CHECK_GROUP for the whole lifetime of the check. A watchdog decides whether the time bound elapsed and records that decision (timed-out/finished) in the private check directory before stopping anything, and bounded_run waits a bounded moment for that decision, so a shell that outlives the bound can never be reported as success. cleanup_check now stops the dedicated group (graceful then forceful on the timeout path, forceful on the success path) plus a sweep of descendants that left the group, removes the private temporary check directory, and is guarded by CHECK_CLEANED so the exit trap and a signal trap cannot release or signal the same check twice; every piece of state is cleared only after it has been used. The script's own description now states that the checked shell is placed in a process group of its own and that the group is stopped on every exit path, replacing the old text that claimed the shell was deliberately kept out of its own group. Existing behaviour (login-shell and profile detection, opt-outs, re-install, uninstall, never reading stdin) is untouched. Tests: the regression tests in tests/test_check_cleanup.py (successful and timed-out check stop the background process, group id equals shell pid, no private directory remains) pass, the added tests in tests/test_install.py for a shell that outlives the bound and for a withheld watchdog decision pass, and the full suite was run with the final command: 214 passed, 137 subtests passed.

## Files Changed

- `install.sh`
- `tests/test_check_cleanup.py`
- `tests/test_install.py`

## Commands

- `["python", "-m", "pytest", "-q", "tests/test_check_cleanup.py"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "install.sh"]` → exit 0
- `["git", "diff", "tests/test_install.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
....................................................................................................... [ 48%]
........................................................................ [ 81%]
.......................................          [100%]
214 passed, 137 subtests passed in 154.78s (0:02:34)

```

## Actions

- read_file: install.sh
- read_file: tests/test_check_cleanup.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_check_cleanup.py']
- run: ['git', 'status', '--short']
- run: ['git', 'diff', 'install.sh']
- run: ['git', 'diff', 'tests/test_install.py']
- run: ['python', '-m', 'pytest', '-q']
