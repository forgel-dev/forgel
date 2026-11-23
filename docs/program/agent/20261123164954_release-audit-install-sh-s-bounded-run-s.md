# Agent Run: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

- Task: `20261123164954_release-audit-install-sh-s-bounded-run-s`
- Status: `failed`
- Repository: `code`
- Steps: 11
- Finished: 2026-11-23T18:09:09+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The installer already exposed a configurable timeout and a way to record a timeout; only the verdict decision was wrong, as the spec's Assumptions state.
- The verdict is derived from the measured duration of the check against the bound, not from the presence of the watchdog's record; the spec leaves the mechanism to the developer and the Risks section names re-polling as unsound.
- The regression test drives the real installer entry point with a controlled overrunning step rather than performing a real installation, which the spec's Assumptions permit.
- The stub `date` follows the real external interface (`+%s%N` answers nanoseconds since the epoch), so the test exercises the same clock the installer times with.
- Existing timeout message wording was kept unchanged, as the spec's Assumptions require.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 11
- Estimated input tokens (all calls): 186710
- Provider input/output tokens: 193782 / 3680
- Provider cache hit/miss tokens: 172032 / 21750
- Estimated prompt at the end: 23018 tokens
- State: not needed

## Specification (`docs/program/specs/20261123164954_release-audit-install-sh-s-bounded-run-s.md`)

# Task Spec: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out |
| Project | — |
| Task | `20261123164954_release-audit-install-sh-s-bounded-run-s` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T17:07:04+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The installer decides whether a checked step timed out by looking for a recorded timeout at the moment the checked step's result becomes available. When a checked step runs past the configured timeout but exits on its own before the timeout is recorded, no timeout is found, the timeout monitoring is shut down, and the step's own outcome is kept, so an overrun is reported as a verified success. An earlier attempt to correct this produced no lasting correction and no regression test, so the false-success window remains.

**Outcome:** The installer reports a timeout whenever a checked step ran past the configured timeout, regardless of whether the timeout had been recorded by the time the step's result became available. A regression test that reproduces the overrun-then-exit-before-timeout-recorded ordering deterministically exists in the test suite, fails against the previous behavior and passes with the correction. All previously existing tests still pass.

## Product Intent

A new terminal must find forgel-code on PATH after installation; an installation step that silently overruns its time budget and is reported as a verified success hides a broken install.

## User Experience

A user running the installer sees an explicit timeout failure with a nonzero result when an installation step overruns its time budget, instead of a success message for an install that was not verified.

## Roadmap

—

## Goals

- Close the false-success window in the timeout verdict.
- Keep the fast-path outcome propagation unchanged.
- Prove the race is closed with a deterministic regression test.
- Keep the existing suite green.

## Non-Goals

- Changing what the installer installs, where it installs, or how the installed command becomes available on PATH
- Changing the user-facing timeout setting or its default value
- Reworking unrelated parts of the installer
- Packaging, release or documentation changes
- Weakening, skipping or removing any existing test

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code; it is a Python client installed as forgel-code. | User decision log, D-004 (user accepted the proposal, 2026-11-16 18:34) |

## Functional Requirements

- **FR-1**: When a checked step runs longer than the configured timeout and exits on its own before the timeout has been recorded, the installer reports a timeout failure for that step.
- **FR-2**: The absence of a recorded timeout at the moment a checked step's result becomes available is never taken as evidence that the step finished within the timeout.
- **FR-3**: Every checked step produces exactly one verdict: either the step's own outcome or a timeout; the verdict is never left undetermined and never defaults to success for a step that overran.
- **FR-4**: A checked step that finishes before the timeout expires produces no timeout verdict and keeps its own outcome unchanged, including a nonzero outcome.
- **FR-5**: When a timeout verdict is produced, the installation result is a failure and no success message is shown for that step.
- **FR-6**: The test suite includes a regression test for the overrun-then-exit-before-timeout-recorded ordering that fails against the previous behavior and passes with the correction.
- **FR-7**: The regression test is deterministic: it forces the ordering explicitly and does not depend on elapsed-time delays, scheduling luck or real network access.
- **FR-8**: Every test that existed before this correction still passes, with its premise unchanged.

## User Stories

- As someone installing Forgel Code for the first time, I want an overrunning installation step to fail loudly, so that a broken install is not reported to me as a verified success.
- As a maintainer, I want a deterministic regression test for the timeout verdict, so that the defect cannot silently return.
- As a user whose installation step finishes just within the timeout, I want the installer to keep that step's real outcome, so that a legitimate failure is not mislabeled as a timeout.

## Acceptance Criteria

- **AC-1**: A checked step that overruns the configured timeout and exits on its own before the timeout is recorded is reported as a timeout with a nonzero result and is never reported as a verified success.
- **AC-2**: A checked step that completes before the timeout expires yields its own outcome and no timeout verdict, including when that outcome is nonzero.
- **AC-3**: The test suite contains a regression test for the overrun-then-exit-before-timeout-recorded ordering that is deterministic and would fail if the installer reverted to deciding the verdict solely by the presence of a recorded timeout.
- **AC-4**: The complete pre-existing test suite passes alongside the correction.
- **AC-5**: The installer still parses and runs without syntax errors in its supported shell environment.

## Scope Boundaries

- How the installer decides the outcome of a checked step that ran past its configured timeout
- The ordering between a checked step's completion and the reporting of a timeout verdict
- A deterministic regression test for the overrun-then-exit-before-timeout-recorded ordering
- Preserved behavior for checked steps that finish within the timeout, including propagation of their own nonzero outcome
- Changing what the installer installs, where it installs, or how the installed command becomes available on PATH
- Changing the user-facing timeout setting or its default value
- Reworking unrelated parts of the installer
- Packaging, release or documentation changes
- Weakening, skipping or removing any existing test

## Risks

- A correction that merely polls again for a recorded timeout remains racy under load, so a false success can survive in practice while the test passes.
- A regression test built on elapsed-time delays can be flaky in continuous integration and either hide the race or fail intermittently.
- Waiting for both the checked step and the timeout monitoring without a deterministic shutdown can hang the installer on the fast path.
- The earlier attempt produced no lasting correction and described a mechanism absent from the result; repeating that leaves the audit finding open.
- A correction that treats every late exit as a timeout could mislabel a step that finished within the timeout but whose outcome became available late.

## Open Questions

- None.

## Assumptions

- The installer already exposes a configurable timeout and already has a way to record that a timeout occurred; only the verdict decision is wrong.
- The regression test may drive the checked-step behavior through the installer's existing entry point with a controlled overrunning step instead of performing a real installation.
- The form and location of the recorded timeout are internal to the installer and are the developer's choice, provided the verdict requirements hold.
- Existing wording of timeout messages is kept; only the correctness of the verdict is in scope.

## Related Documents

- AGENTS.md
- FORGEL.md

## Revision History

- v1 — initial specification for the audit finding on the installer's timeout verdict ordering
- v2 — restated behavior without implementation, commit or file references; checks aligned with the task repository


## Summary

Closed the installer's false-success window for overrunning checked steps and added the deterministic regression test named by FR-6/FR-7.

install.sh: `bounded_run` now times the checked step itself with the millisecond clock (`now_millis`, which reads `date +%s%N`) and derives the verdict from that measured duration: `CHECK_STATUS=124` whenever the elapsed time reached the bound, regardless of whether the watchdog had already written its `timed-out` marker when the step's result arrived. The watchdog's `timed-out`/`finished` records are still used only to decide which stop to expect and to sequence the cleanup, never as the verdict. A step that finished inside the bound keeps its own status, a nonzero one included, so a legitimate failure is not relabelled a timeout. The header comment and the function comment state the corrected behaviour (the verdict is the measured duration; the absence of a recorded timeout proves nothing).

tests/test_install_timeout_verdict.py: new regression test that forces the overrun-then-exit-before-timeout-recorded ordering explicitly by handing the installer a stub `date +%s%N` clock (the same external interface the installer times with). The clock reports a 3 s step under a 1 s bound while the checked shell exits at once, so only a `finished` record can exist; the test asserts a nonzero result, the timeout report, no success lines and no leftover check directory. A second test covers the fast path: a step inside the bound keeps its own nonzero status and produces no timeout verdict. Neither test waits for real time or touches the network.

Uncommitted-file decision, enumerated from `git status --porcelain --untracked-files=all --ignored`:
- `install.sh` (M) — commit: the corrected timeout verdict, required by FR-1 to FR-5.
- `tests/test_install_timeout_verdict.py` (??) — commit: the regression test required by FR-6/FR-7.
- `tests/test_install.py`, `tests/test_check_cleanup.py` — not dirty; they are already committed fixtures the new test imports from, and nothing in them was modified by this task.
- `.pytest_cache/**` and every `__pycache__/**` entry — ignore: already covered by the committed `.gitignore` rules; no new rule needed and nothing is tracked.
No file is left undecided and no unrelated change is part of the change set.

Verification: `python -m pytest -q` on the whole suite passed — 216 tests and 137 subtests, no failures, no existing test changed or removed. A narrow run of the touched install/cleanup/verdict modules also passed (60 tests). The installer is executed as `sh install.sh` throughout that suite, which covers AC-5; a standalone `sh -n install.sh` was refused by the sandbox's shell-command policy, so parse validity rests on those real runs.; the completion step could not decide what to do with every uncommitted file

## Files Changed

- `install.sh`
- `tests/test_install_timeout_verdict.py`

## Commands

- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all", "--ignored"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_install_timeout_verdict.py", "tests/test_install.py", "tests/test_check_cleanup.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
....................................................................................................... [ 47%]
........................................................................ [ 81%]
.........................................        [100%]
216 passed, 137 subtests passed in 167.22s (0:02:47)

```

## Actions

- run: ['git', 'status', '--porcelain']
- read_file: install.sh
- read_file: tests/test_install_timeout_verdict.py
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'status', '--porcelain', '--untracked-files=all', '--ignored']
- run: ['sh', '-n', 'install.sh']
- read_file: install.sh
- recall
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install_timeout_verdict.py', 'tests/test_install.py', 'tests/test_check_cleanup.py']
