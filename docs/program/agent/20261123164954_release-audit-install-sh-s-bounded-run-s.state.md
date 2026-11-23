# Session State: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

- Task: `20261123164954_release-audit-install-sh-s-bounded-run-s`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- When a checked step runs longer than the configured timeout and exits on its own before the timeout has been recorded, the installer reports a timeout failure for that step.
- The absence of a recorded timeout at the moment a checked step's result becomes available is never taken as evidence that the step finished within the timeout.
- Every checked step produces exactly one verdict: either the step's own outcome or a timeout; the verdict is never left undetermined and never defaults to success for a step that overran.
- A checked step that finishes before the timeout expires produces no timeout verdict and keeps its own outcome unchanged, including a nonzero outcome.
- When a timeout verdict is produced, the installation result is a failure and no success message is shown for that step.
- The test suite includes a regression test for the overrun-then-exit-before-timeout-recorded ordering that fails against the previous behavior and passes with the correction.
- The regression test is deterministic: it forces the ordering explicitly and does not depend on elapsed-time delays, scheduling luck or real network access.
- Every test that existed before this correction still passes, with its premise unchanged.

## Acceptance Criteria

- A checked step that overruns the configured timeout and exits on its own before the timeout is recorded is reported as a timeout with a nonzero result and is never reported as a verified success.
- A checked step that completes before the timeout expires yields its own outcome and no timeout verdict, including when that outcome is nonzero.
- The test suite contains a regression test for the overrun-then-exit-before-timeout-recorded ordering that is deterministic and would fail if the installer reverted to deciding the verdict solely by the presence of a recorded timeout.
- The complete pre-existing test suite passes alongside the correction.
- The installer still parses and runs without syntax errors in its supported shell environment.

## Constraints

- none

## Assumptions

- none

## Files Changed

- install.sh
- tests/test_install_timeout_verdict.py

## Actions

- read_file: install.sh
- read_file: tests/test_check_cleanup.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_readme_install.py
- write_file: install.sh
- run: ['sh', '-n', 'install.sh']
- read_file: tests/test_stub_contract.py
- write_file: tests/test_install_timeout_verdict.py
- write_file: tests/test_install_timeout_verdict.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install_timeout_verdict.py']
- write_file: install.sh
- write_file: install.sh

## Commands

- `['python', '-m', 'pytest', '-q', 'tests/test_install_timeout_verdict.py']` -> exit 0

## Recent Observations

- run python -m pytest -q tests/test_install_timeout_verdict.py -> exit 0
- write_file install.sh
- write_file install.sh

## Next Step

Continue from the current repository state and the changed files.
