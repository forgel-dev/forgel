# Session State: Release audit: `bounded_run` does not make the watchdog's timeout decision authoritative. After

- Task: `20261123062514_release-audit-bounded-run-does-not-make-`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- `bounded_run` must not treat the absence of the `timed-out` marker at the moment the checked child exits as proof that the bound did not elapse; the timeout decision must be resolved after the watchdog has reached its own decision.
- When the bound elapsed before the checked command exited, `bounded_run` must set `CHECK_STATUS=124` regardless of the ordering between the child's exit and the marker write.
- `verify_profile` must report `CHECK_STATUS=124` as a failed verification: a non-zero installer exit and a message that names the configured limit, never a success.
- When the checked command exits before the bound elapses, `bounded_run` must return that command's own exit status and its captured output unchanged.
- Every exit path of `bounded_run` must leave no watchdog process and no private check directory behind, including the timeout path and paths taken after a failure.
- The wait for the watchdog's decision must itself be bounded by a fixed, small limit derived from `VERIFY_GRACE`, so `install.sh` cannot hang waiting for a watchdog that never answers.
- The installer must remain POSIX `sh` (`sh -n install.sh` clean, `set -eu`) and must not invoke GNU `timeout` or any binary not already used by the script.
- A regression test in `tests/test_install.py` must exercise the real `install.sh` with a fresh-shell check whose runtime exceeds `FORGEL_CODE_TIMEOUT` and assert that the install fails at the bound instead of reporting success.
- No existing test may be weakened to accommodate the change.
- The whole existing test suite must still pass.

## Acceptance Criteria

- A checked command that outlives `FORGEL_CODE_TIMEOUT` makes `install.sh` exit non-zero with a failure message naming the limit, and this holds even when the command's exit lands between the limit and the watchdog's marker write.
- A checked command that finishes inside the limit keeps its own exit status and output, and the installer's verification result is unchanged from the documented behaviour.
- After a timed-out run and after a successful run, no watchdog process from the check and no private `forgel-code-check` directory remain.
- The bounded wait for the watchdog decision terminates on its own, so no run of `install.sh` blocks indefinitely.
- `sh -n install.sh` reports no syntax error and the script contains no invocation of GNU `timeout`.
- The new regression test fails against the current `bounded_run` and passes against the fixed one.
- `python -m pytest -q` passes for the whole repository.

## Constraints

- none

## Assumptions

- none

## Files Changed

- install.sh
- tests/test_install.py

## Actions

- read_file: install.sh
- read_file: tests/test_install.py
- write_file: install.sh
- write_file: install.sh
- write_file: tests/test_install.py
- read_file: install.sh
- write_file: tests/test_install.py
- run: ['sh', '-n', 'install.sh']
- run: ['python', '-m', 'pytest', 'tests/test_install.py', '-q', '-x', '-k', 'outlives or never_arrives or bounded or timeout']
- run: ['python', '-m', 'pytest', '-q']
- read_file: tests/test_install.py
- read_file: install.sh
- write_file: tests/test_install.py

## Commands

- `['python', '-m', 'pytest', 'tests/test_install.py', '-q', '-x', '-k', 'outlives or never_arrives or bounded or timeout']` -> exit 0
- `['python', '-m', 'pytest', '-q']` -> exit 0

## Recent Observations

- read_file tests/test_install.py: tests/test_install.py: lines 464-503 of 1883
- read_file install.sh: install.sh: lines 1-100 of 919
- write_file tests/test_install.py

## Next Step

Continue from the current repository state and the changed files.
