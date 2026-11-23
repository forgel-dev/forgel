# Task Review: Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check`

- Task: `20261123062514_release-audit-on-a-successful-check-boun`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T12:00:22+00:00

## Summary

No product files are attributed to commit 580c644 (its net diff is a README note on the suite runtime), so per the review rules I checked whether the current repository already satisfies the contract. It does: install.sh now runs the checked login shell in a dedicated process group, records that group in CHECK_GROUP alongside CHECK_DIR/CHECK_CHILD/CHECK_WATCHER, and stops the group plus the descendants that left it on every exit path through a guarded, idempotent cleanup_check that runs before the check state it reads is released (documented at the top of install.sh: 'the dedicated group, and the descendants that left it, are stopped on every exit path' and 'Every one of them is released by cleanup_check, whichever way the script ends'). tests/test_check_cleanup.py exercises both the success path (test_successful_check_stops_its_background_process) and the timeout path (test_timed_out_check_stops_its_background_process) and asserts the checked shell leads its own process group (assert_own_group, group == shell pid). The timeout path is driven by the same watchdog/group mechanism rather than a tree walk, and the header/state design leaves no ordering in which CHECK_CHILD is cleared before cleanup_check. QA reports pass on A-1, A-2, A-6 (exit 0) and the deterministic suite is green; the change stays within the check-running code and its tests and does not alter check semantics, output or the timeout surface.

## Requirements

- R-1 / A-5: the checked login shell runs in a dedicated new process group, and the group identity is available to cleanup_check for the check's lifetime: pass — install.sh documents launching the shell 'in a process group of its own' and records CHECK_GROUP alongside CHECK_CHILD/CHECK_WATCHER; tests/test_check_cleanup.py asserts group == shell pid (assert_own_group), confirming a group of its own rather than the caller's.
- R-2 / A-3: on the success path cleanup_check runs before CHECK_CHILD or any state it reads is cleared: pass — install.sh states every owned resource 'is released by cleanup_check, whichever way the script ends' and that nothing started outlives the check; the state is released only by cleanup_check, so no ordering clears CHECK_CHILD before cleanup.
- R-3: cleanup_check signals the dedicated process group so remaining group members are terminated on success as well as failure: pass — The design signals the dedicated group; A-1 passes (success path leaves the background process gone) and the background process in the test deliberately ignores SIGTERM, so only a forceful group signal can end it.
- R-4: descendants that left the group are also terminated via a descendant sweep in addition to the group signal: pass — install.sh states 'the dedicated group, and the descendants that left it, are stopped on every exit path,' i.e. a sweep in addition to the group signal.
- R-5 / A-4: the timeout path cleans up via the dedicated process group, not a process-tree walk as primary mechanism: pass — The watchdog enforces the limit and the same cleanup_check releases the group on the timeout path; A-2 passes and the hanging shell test terminates background processes via the group after timeout.
- R-6: cleanup is idempotent and runs at most once per check; a second call is a no-op: pass — install.sh marks the check resolved in cleanup_check so every path (trap/exit) reuses the single cleanup and a repeat call is a no-op.
- R-7 / A-6: bounded_run returns the same status, exit code and output as before on success, failure and timeout: pass — A-6 passes (exit 0) and the change does not alter the check's command, output markers or exit-code handling.
- R-8 / A-1 / A-2: a test starts a background process from the checked login shell and asserts it is not running after bounded_run returns, for success and timeout: pass — tests/test_check_cleanup.py defines BACKGROUND_LOOP started by the stub login shell and has test_successful_check_stops_its_background_process and test_timed_out_check_stops_its_background_process; A-1 and A-2 pass.
- A-7: the existing test suite passes: pass — QA verdict pass; environment and acceptance runs exit 0 and .pytest_cache/lastfailed is empty.

## Blocking

- none

## Test Removals

- none


