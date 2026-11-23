# Task Review: Release audit: `bounded_run` does not make the watchdog's timeout decision authoritative. After

- Task: `20261123062514_release-audit-bounded-run-does-not-make-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T11:22:13+00:00

## Summary

The task is attributed to no product files; the single attributed commit only adds a README paragraph about the suite's runtime budget, which belongs to the earlier test-runtime work and is not a change to the installer. Following the fallback rule for a task with no attributed product change, I checked the current repository state: install.sh now states in its header that the watchdog is the only authority on whether the bound elapsed and that the outcome is read only after that decision exists, and DECISION_WAIT is derived from VERIFY_GRACE with a floor of one second, so the wait for the decision cannot block the installer. tests/test_install.py carries the bounded-check scenarios that drive the real installer, including a check that outlives FORGEL_CODE_TIMEOUT under a short configured limit. The QA gate reports every deterministic acceptance check as passing (timed-out check fails with a message naming the limit, in-limit check keeps its status and output, no watchdog or forgel-code-check directory left after either path, sh -n install.sh clean with no GNU timeout invocation, and the whole suite green), and no test was removed or weakened. The only imperfection is the attributed README paragraph, which is outside the specification's affected-file list but only documents a previously delivered test-runtime change and alters no product behaviour, so it is not blocking.

## Requirements

- FR-1: bounded_run must not treat the absence of the timed-out marker at the child's exit as proof the bound did not elapse; the decision is resolved after the watchdog decides.: pass — install.sh's header documents the watchdog as the only authority whose recorded decision is read before the outcome, and the bounded-check acceptance scenario passes.
- FR-2: When the bound elapsed before the checked command exited, bounded_run sets CHECK_STATUS=124 regardless of the ordering between the child's exit and the marker write.: pass — The acceptance check for a check outliving FORGEL_CODE_TIMEOUT, including an exit landing between the limit and the marker write, passes.
- FR-3: verify_profile reports CHECK_STATUS=124 as a failed verification with a non-zero installer exit and a message naming the configured limit.: pass — The timed-out scenario acceptance check passes: non-zero exit and a failure message naming the limit.
- FR-4: When the checked command exits before the bound elapses, bounded_run returns its own exit status and captured output unchanged.: pass — The in-limit scenario acceptance check passes, with the verification result unchanged.
- FR-5: Every exit path of bounded_run leaves no watchdog process and no private check directory behind, including the timeout path and paths after a failure.: pass — The cleanup acceptance check passes for both the timed-out and the successful run; no forgel-code-check directory or watchdog process remains.
- FR-6: The wait for the watchdog's decision is bounded by a fixed, small limit derived from VERIFY_GRACE.: pass — install.sh defines DECISION_WAIT from VERIFY_GRACE with a one-second floor and documents it as an upper bound; the no-hang acceptance and whole-module runs pass.
- FR-7: The installer stays POSIX sh (sh -n clean, set -eu) and invokes neither GNU timeout nor any binary not already used.: pass — The sh -n and no-GNU-timeout acceptance check passes; set -eu remains at the top of the script and the watchdog plus sleep/kill mechanism is unchanged in kind.
- FR-8: A regression test in tests/test_install.py exercises the real install.sh with a fresh-shell check exceeding FORGEL_CODE_TIMEOUT and asserts failure at the bound.: pass — The bounded-check scenarios in tests/test_install.py drive the real installer with a limit below the product default and assert failure; the corresponding acceptance checks pass.
- FR-9: No existing test may be weakened to accommodate the change.: pass — No test removals are recorded, the change adds scenarios and configures a short limit instead of relaxing assertions, and the whole suite passes.
- FR-10: The whole existing test suite must still pass.: pass — python -m pytest -q passes for the whole repository (acceptance check exit 0).
- AC-1: A checked command outliving FORGEL_CODE_TIMEOUT makes install.sh exit non-zero with a message naming the limit, even when the exit lands between the limit and the watchdog's marker write.: pass — Acceptance check passed.
- AC-2: A checked command finishing inside the limit keeps its own exit status and output, and the verification result is unchanged.: pass — Acceptance check passed.
- AC-3: After a timed-out run and after a successful run, no watchdog process and no private forgel-code-check directory remain.: pass — Acceptance check passed for both paths.
- AC-4: The bounded wait for the watchdog decision terminates on its own, so no run of install.sh blocks indefinitely.: pass — The test module run and the e2e checks complete within the module's TIMEOUT bound.
- AC-5: sh -n install.sh reports no syntax error and the script contains no invocation of GNU timeout.: pass — Acceptance check passed.
- AC-6 (review-only): The new regression test fails against the previous bounded_run and passes against the fixed one.: pass — The regression scenario asserts a failure at the bound for a check that outlives the configured limit; the pre-fix behaviour reported such a check as a success, so that assertion cannot hold before the fix, and it passes now. The observable premise of the scenario (failure at the bound) is stated directly in the test's own expectation rather than derived from a private interface.
- AC-7: python -m pytest -q passes for the whole repository.: pass — Acceptance check passed (exit 0), as did the environment test and e2e gates.
- Scope: change only the files the specification lists (install.sh, tests/test_install.py) and add no unrequested feature.: pass — The install.sh and tests/test_install.py changes stay within the installation-scope described; the attributed README paragraph is outside the listed affected files but only documents an already delivered test-runtime budget, changes no product behaviour and does not weaken anything.

## Blocking

- none

## Test Removals

- none


