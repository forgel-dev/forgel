# Task Review: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

- Task: `20261123164954_release-audit-install-sh-s-bounded-run-s`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T18:39:12+00:00

## Summary

The change replaces the marker-only timeout verdict in install.sh with a measured-duration verdict: a new now_millis() times the check around start_check and wait, and bounded_run reports 124 when either the watchdog's timed-out marker exists or the measured duration reached the limit, so a run that overran but exited before the marker was written can no longer be reported as success, while a run that finished inside the bound keeps its own status (including a nonzero one). The post-limit wait is still the unchanged, bounded DECISION_WAIT, and cleanup_check is untouched, so no process or check directory survives. A new regression test drives the real installer with a deterministic clock stub that forces the check's end just after, at, and well past the bound, plus an in-bound nonzero case, so the just-after-limit case is exercised without a timing race and would fail against the previous code. Only install.sh and tests/test_install_timeout_verdict.py are attributed; the worktree is clean, no test was removed or weakened, the header comments were updated to describe behavior rather than the removed marker-authority claim, and all text is English. QA passed the environment gate, e2e checks and the acceptance commands, so the behavioral criteria are taken as verified.

## Requirements

- FR-1 / AC-1: A verification command that does not finish within its time limit fails the installation with a message naming the time limit (just-after/beyond cases).: pass — bounded_run sets CHECK_STATUS=124 when the timed-out marker exists or measured >= limit*1000; the existing 'stopped after ${limit}s' message is emitted and the new just-after-limit test asserts it.
- FR-2: The failure occurs regardless of where the command's own exit falls relative to the moment the limit elapses, so ordering cannot change the verdict.: pass — The verdict is derived from the measured start-to-exit duration and the marker, not from which record happened to be present at read time, so the command's exit ordering no longer decides the outcome; a run strictly inside the bound keeps its own status as FR-3/FR-4/FR-9 require.
- FR-3: A verification command that finishes within its limit and reports success lets the installation continue.: pass — No branch forces 124 when the measurement is below the limit, so a successful in-bound run keeps status 0 and the installer continues to the PATH resolution step; this is covered by the pre-existing in-limit tests that still pass.
- FR-4 / AC-3: A verification command that fails within its limit is reported as its own failure, never as a time-limit failure.: pass — CHECK_STATUS keeps the child's status when the measurement is under the limit; the new test test_step_inside_the_bound_keeps_its_own_nonzero_outcome asserts status 3 is reported and 'stopped after 1s' is absent.
- FR-5 / AC-4: No run in which the limit elapsed is reported as a successful installation.: pass — The verdict no longer depends on a marker being observed in time; the new tests cover the previously-successful ordering (fast exit, marker not yet written) and assert failure.
- FR-6: Additional waiting for the outcome after the limit has passed is finite and short.: pass — await_decision and DECISION_WAIT are unchanged and bounded by the grace period; the end time is captured before that wait, so the wait does not extend the measured duration.
- FR-7 / AC-7: The verification step leaves no residual processes and no temporary working artifacts, including when the limit is exceeded.: pass — cleanup_check and the watchdog's graceful/forceful stop are untouched; every new test asserts no check directories remain under TMPDIR, and the acceptance check for residual processes passed.
- FR-8 / AC-1, AC-5: The test suite contains a regression test whose verification command ends just after the limit and which asserts failure with a message naming the limit, and it passes.: pass — tests/test_install_timeout_verdict.py test_step_ending_just_after_the_limit_is_a_failure forces the measured end one millisecond past the bound via a deterministic clock stub and asserts 'stopped after 1s'; QA reports it and the full suite passing, and it would fail against the previous marker-only code.
- FR-9 / AC-6: Behavior for commands finishing well within their limit is unchanged and pre-existing tests pass without weakening.: pass — No pre-existing test was modified or removed; the in-bound path is untouched apart from gaining a measured-duration guard that cannot trip below the limit, and the full suite passes.
- FR-10 / AC-8: All produced artifacts are in English.: pass — The changed header comments, function comments, commit message and the new test module, docstrings and comments are all in English.
- Review-only: the change is coherent and complete, contains only the files it needs, and adds no unrelated, temporary, debug or generated file.: pass — Only install.sh and the new test file are attributed; the worktree is clean with no escalated changes. A partially executed command produced an empty tool result, but no truncated string is committed — the delivered files read as complete and the QA suite passes.
- Review-only: no security problem, committed secret or weakened/deleted test.: pass — No secret, credential or new external surface is introduced; the clock stub lives only in the test's temporary directory, and no existing test was edited or deleted.
- Review-only: the time limit and its default are unchanged and no new option or prompt is added.: pass — DEFAULT_VERIFY_LIMIT, FORGEL_CODE_TIMEOUT handling and usage text are unchanged; the new test reuses the existing knob rather than adding an interface.

## Blocking

- none

## Test Removals

- none


