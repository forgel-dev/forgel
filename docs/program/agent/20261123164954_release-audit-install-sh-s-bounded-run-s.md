# Agent Run: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

- Task: `20261123164954_release-audit-install-sh-s-bounded-run-s`
- Status: `done`
- Repository: `code`
- Steps: 17
- Finished: 2026-11-23T18:30:14+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The check's duration is measured from just before the command is started to just after its own status is available, and duration >= limit counts as exceeding the limit (the limit is inclusive, matching 'ends just before, at, or just after').
- When no usable clock is available (the helper reports 0), the watchdog's recorded 'timed-out' marker remains the fallback verdict, as before.
- The regression test forces the just-after-limit case deterministically with a stubbed clock rather than relying on real process timing, so it cannot be flaky.
- Existing exit cleanup (stop_check plus removal of the private check directory) already satisfies the no-residual-processes/artifacts requirement and was left unchanged.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 17
- Estimated input tokens (all calls): 365846
- Provider input/output tokens: 378515 / 3711
- Provider cache hit/miss tokens: 355968 / 22547
- Estimated prompt at the end: 28677 tokens
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
| Created | 2026-11-23T18:11:02+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The installer must give a truthful verdict about whether the project's verification command finished within its time limit. Today the verdict is inferred from how the run appears to have ended, so a command that ends just after the limit can be misjudged: the installation may be reported as successful, or the timeout may surface as an unrelated failure, and the person running the installer cannot tell that the limit was the cause.

**Outcome:** Whenever a verification command exceeds its time limit, the installer fails the run and tells the user the limit was exceeded, no matter whether the command ended just before, at, or after the moment the limit elapsed. Commands that finish within their limit keep the result they actually produced: success continues the installation, and their own failure is reported as that failure rather than as a timeout. Waiting after the limit stays short and finite. A regression test covering a command that ends just after the limit is part of the delivered change.

## Product Intent

The installation must only be reported as successful after the project's own verification genuinely passed within the time it was allowed; the milestone goal — a working installation whose command is found on PATH — depends on that verdict being trustworthy.

## User Experience

A person running the installer either sees the installation complete, sees their own verification failure reported as such, or sees a failure that clearly says the verification command exceeded the time limit it was given. They never see a success for a run that ran too long, and they never wait indefinitely after the limit has passed.

## Roadmap

—

## Goals

- Make the installer's time-limit verdict correct for commands that end just after the limit.
- Report an exceeded limit as an exceeded limit, never as success and never as an unrelated failure.
- Keep the post-limit wait short and finite while still cleaning up after the run.
- Lock the behavior in with a regression test for the just-after-limit case.

## Non-Goals

- Changing the time limit itself or its default value
- Changing how the verification command is supplied or what it runs
- Changing PATH placement behavior or the installer's primary milestone fix
- Rewording installer messages unrelated to the time limit
- Adding new user-facing installer options or prompts
- Changing how the installer is packaged, published or released

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | Documentation states behavior and contracts but never volatile implementation details such as timings or runtime bounds; divergence is fixed by removing the detail, not by changing code or tuning a limit. | FORGEL.md / AGENTS.md D-109 |
| — | A requirements document states functional requirements only, with no technical detail at all. | FORGEL.md / AGENTS.md D-110 |
| — | A task contains only the change selected for it; unrelated changes are never included or attributed to it. | FORGEL.md / AGENTS.md D-097 |
| — | Every uncommitted product file gets one decision at completion: keep, discard, ignore or escalate. | FORGEL.md / AGENTS.md D-105 |
| — | All committed project artifacts are English. | AGENTS.md D-025 |

## Functional Requirements

- **FR-1**: When a verification command does not finish within its time limit, the installer must fail the installation and its failure must state that the time limit was exceeded.
- **FR-2**: That failure must occur regardless of whether the command ends just before, at, or just after the moment the limit elapses.
- **FR-3**: A verification command that finishes within its limit and reports success must let the installation continue.
- **FR-4**: A verification command that finishes within its limit and reports failure must be reported as that failure and must not be presented as a time-limit failure.
- **FR-5**: No situation may exist in which the installation is reported as successful for a verification run that exceeded its limit.
- **FR-6**: The installer's additional waiting for the outcome of a verification run after the limit has passed must be finite and short.
- **FR-7**: The verification step must leave no residual processes and no temporary working artifacts behind, including when the limit is exceeded.
- **FR-8**: The project's test suite must contain a regression test whose verification command ends just after the limit and which asserts that the installation fails with a message naming the limit.
- **FR-9**: The behavior of the installer for verification commands that finish well within their limit must remain unchanged.
- **FR-10**: All project artifacts are in English.

## User Stories

- As a person installing the client, I want to be told plainly when my verification command exceeded its time limit, so that I fix the command instead of chasing an unrelated error.
- As a person installing the client, I want success reported only when verification really succeeded in time, so that I can trust the installation.
- As a maintainer, I want a regression test for the just-after-limit case, so that this misjudgement cannot silently return.

## Acceptance Criteria

- **AC-1**: A verification command that ends just after the time limit makes the installation fail with a message naming the time limit.
- **AC-2**: A verification command that succeeds well within the time limit lets the installation complete.
- **AC-3**: A verification command that fails with its own error within the time limit produces that error and not a time-limit message.
- **AC-4**: No run in which the time limit elapsed is reported as a successful installation.
- **AC-5**: The regression test for the just-after-limit case exists and passes, and the full test suite passes.
- **AC-6**: The pre-existing tests for within-limit verification pass without being weakened, showing that behavior for those cases is unchanged.
- **AC-7**: After an exceeded-limit run, no verification processes remain and no temporary working artifacts are left behind.
- **AC-8**: Every artifact produced is in English.

## Scope Boundaries

- Correctness of the installer's verdict when a verification command exceeds its time limit
- Forcing the exceeded-limit failure regardless of the moment the command ends relative to the limit
- Short, finite waiting for the outcome after the limit has passed
- No residual processes or temporary work artifacts after the verification step, including after an exceeded limit
- A regression test covering a verification command that ends just after the limit and asserting a failure naming the limit
- Preserving existing installer behavior for commands that finish within the limit
- Changing the time limit itself or its default value
- Changing how the verification command is supplied or what it runs
- Changing PATH placement behavior or the installer's primary milestone fix
- Rewording installer messages unrelated to the time limit
- Adding new user-facing installer options or prompts
- Changing how the installer is packaged, published or released

## Risks

- A too-short extra wait could misreport a slow but in-limit command on a heavily loaded machine.
- A too-long extra wait delays the report a user sees after the limit has passed.
- A regression test that depends on precise process timing can be flaky; it must place the command's end deterministically after the limit rather than relying on a race.
- The task title frames this as a release audit; widening the change to other audit findings would break the single-change rule and delay the milestone fix.

## Open Questions

- None.

## Assumptions

- The product already allows a short, finite extra wait after the limit before the installer concludes the run exceeded it.
- A configuration knob already exists to make the limit small in tests, so the regression test does not depend on changing the default limit.
- The failure message for an exceeded limit keeps naming the limit in the form users already see.

## Related Documents

- FORGEL.md
- AGENTS.md

## Revision History

- v1 — initial specification for the installer time-limit verdict task.
- v2 — removed implementation and process detail from the outcome, requirements, acceptance, constraints, goals, user stories, risks and assumptions; decisions now restated as behavior.


## Summary

Fixed install.sh so the bounded verification check reports a time-limit failure whenever the check's own measured duration reaches the configured limit, instead of inferring the verdict solely from the watchdog's recorded marker. bounded_run now takes a timestamp with a new now_millis helper before starting the check and again when the check's result is available; the verdict is 124 when the elapsed time reaches limit*1000 milliseconds or when the watchdog recorded 'timed-out'. The wait for the watchdog's record stays bounded by DECISION_WAIT, the existing graceful/forceful stop and cleanup paths are unchanged (so no residual processes or private directories remain), and the time limit, its default and all user-facing message wording are untouched. Added tests/test_install_timeout_verdict.py, which drives the real installer through tests/test_install helpers with a deterministic 'date' stub (a fabricated clock) and asserts: just-after-limit, at-limit and early-exit-before-marker runs all fail with 'the check was stopped after 1s' and leave no check directory behind, while an in-limit run keeps its own nonzero status and is not reported as a timeout. Verified with `sh -n install.sh` and the full suite: `python -m pytest -q` -> 218 passed, 137 subtests passed.

## Files Changed

- `install.sh`
- `tests/test_install_timeout_verdict.py`

## Commands

- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["python", "-m", "pytest", "-q", "-x", "--timeout=120"]` → exit 4
- `["python", "-m", "pytest", "-q", "tests/test_install_timeout_verdict.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "diff", "install.sh"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
....................................................................................................... [ 47%]
........................................................................ [ 80%]
...........................................      [100%]
218 passed, 137 subtests passed in 150.71s (0:02:30)

```

## Actions

- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: tests/test_install_timeout_verdict.py
- run: ['python', '-m', 'pytest', '-q', '-x', '--timeout=120']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install_timeout_verdict.py']
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'diff', 'install.sh']
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
