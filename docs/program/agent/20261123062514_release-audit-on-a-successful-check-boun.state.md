# Session State: Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check`

- Task: `20261123062514_release-audit-on-a-successful-check-boun`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- R-1: `bounded_run` starts the checked login shell in a new dedicated process group, and that group identity is available to `cleanup_check` for the whole lifetime of the check.
- R-2: On the success path, `bounded_run` calls `cleanup_check` before clearing `CHECK_CHILD` or any other state `cleanup_check` reads; `CHECK_CHILD` is not cleared while cleanup still needs it.
- R-3: `cleanup_check` signals the dedicated process group, so processes started by the checked login shell that remain in that group are terminated on the success path as well as the failure path.
- R-4: Descendants of the checked login shell that left the dedicated group are terminated too, via a descendant sweep performed in addition to the group signal.
- R-5: The timeout path performs cleanup through the dedicated process group, not through a process-tree walk as its primary mechanism.
- R-6: Cleanup is idempotent and runs at most once per check; a second call is a no-op and does not raise.
- R-7: `bounded_run` returns the same result (status, exit code, output) as before the change on the success, failure and timeout paths.
- R-8: A test starts a background process from the checked login shell and asserts, after `bounded_run` returns, that the process is no longer running, for the success path and for the timeout path.

## Acceptance Criteria

- A-1: After a bounded check whose checked login shell starts a background process and exits successfully, the background process is no longer running when `bounded_run` returns.
- A-2: After a bounded check whose checked login shell starts a background process and the check times out, the background process is no longer running when `bounded_run` returns.
- A-3: On the success path, `cleanup_check` runs before `CHECK_CHILD` is cleared; code inspection shows no ordering in which state needed by `cleanup_check` is cleared first.
- A-4: The timeout path cleans up via the dedicated process group; no process-tree walk is the primary cleanup mechanism.
- A-5: The checked login shell runs in its own process group, not in the caller's group.
- A-6: Check results (status, exit code, output) are unchanged for success, failure and timeout paths.
- A-7: The existing test suite passes.

## Constraints

- none

## Assumptions

- none

## Files Changed

- install.sh
- tests/test_check_cleanup.py
- tests/test_install.py

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

## Commands

- none

## Recent Observations

- read_file tests/test_cli.py: tests/test_cli.py: lines 1-40 of 1012
- read_file tests/test_extras.py: tests/test_extras.py: lines 1-473 of 473
- write_file tests/test_check_cleanup.py

## Next Step

Continue from the current repository state and the changed files.
