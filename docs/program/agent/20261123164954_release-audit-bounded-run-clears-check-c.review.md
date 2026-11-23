# Task Review: Release audit: bounded_run clears CHECK_CHILD before calling cleanup_check, and install.sh deli

- Task: `20261123164954_release-audit-bounded-run-clears-check-c`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T17:06:03+00:00

## Summary

The change implements the requested cleanup fix coherently. install.sh now starts the checked login shell under a small Python launcher that calls setsid (falling back to setpgid), so the checked shell leads a dedicated process group whose id equals its own pid, while stdin/stdout/stderr are redirected so no terminal can hold it. bounded_run no longer clears CHECK_CHILD/CHECK_WATCHER before cleanup; instead cleanup_check is guarded by CHECK_CLEANED, stops the dedicated group (plus a descendant sweep) before clearing state, and removes the private check directory on every exit path including timeout. The watchdog records a 'timed-out'/'finished' decision in the private directory and the installer only reads the outcome once that decision exists, so a hanging shell reliably fails with the elapsed bound in the message. The script header and the bounded_run comment now describe the dedicated process group and its cleanup, and the old claim that the shell is kept out of its own group is gone. The new tests/test_check_cleanup.py exercises the success and timeout cleanup paths (asserting own-group placement, background-process termination, and no leftover check directory), and no existing test was removed. Only a minor, non-blocking observation: after the watcher has been reaped, bounded_run leaves CHECK_WATCHER set, so cleanup_check issues a TERM against an already-reaped pid; this is harmless in practice (kill returns ESRCH) and does not violate any stated requirement, but clearing CHECK_WATCHER after the wait would be tidier.

## Requirements

- The installer starts the checked login shell so that it leads a process group of its own, distinct from the installer's group.: pass — start_check runs a Python launcher that calls os.setsid() (falling back to os.setpgid(0,0)) before exec'ing the shell, and redirects its three standard descriptors.
- In the checked login shell, the observed process group identifier equals the shell's own process identifier.: pass — The new test records $$ and ps -o pgid for the checked shell and asserts they are equal; acceptance check passes.
- A successful check stops every process in that dedicated group, including background processes, before the installer reports success.: pass — cleanup_check runs at the end of bounded_run and calls stop_check KILL on CHECK_GROUP before returning; the success-path test confirms the background process is gone.
- A check that exceeds its time bound stops every process in the dedicated group and the installation fails with a message stating the elapsed bound.: pass — The watchdog records timed-out and performs TERM then KILL on the group; CHECK_STATUS becomes 124 and the timeout test asserts non-zero exit, 'stopped after 1s', and no surviving background process.
- The check's recorded state is released only after the stop attempt on every exit path and is released exactly once.: pass — CHECK_CLEANED guards cleanup_check so the signal trap and exit trap cannot release twice; state fields are cleared only after the stop and directory removal.
- No process started by the checked login shell is still running after the installer exits, on the success or timeout path.: pass — Group signal plus descendant sweep covers the check's processes; both regression tests confirm the background process is gone.
- The private temporary check directory is removed on every exit path, including the timed-out check.: pass — cleanup_check removes CHECK_DIR after stopping; the timeout test asserts no CHECK_PREFIX directory remains.
- The script's own description of the check states that the checked shell is placed in a process group of its own and that the group is stopped on every exit path.: pass — Header and bounded_run comment now describe the dedicated group and its stop on every exit path; review-only criterion verified by reading the file.
- The script's description of the check no longer states that the checked shell is kept out of its own process group.: pass — The former 'deliberately not given its own process group' text was replaced; review-only criterion satisfied (AC-7).
- The installer never reads its standard input and stays safe to pipe into an interpreter.: pass — No added stdin reads; the launcher redirects the child's stdin from /dev/null.
- All existing installer behavior unrelated to cleanup keeps working unchanged.: pass — Detection, opt-outs, re-install and uninstall paths are untouched; the full existing test suite passes.
- The regression tests for the successful and timed-out check cleanup both pass.: pass — tests/test_check_cleanup.py adds both cases and both pass (AC-5).
- The full existing test suite passes.: pass — Acceptance reports the full suite passing; no tests were removed.

## Blocking

- none

## Test Removals

- none


