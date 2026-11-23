# Task Review: Release audit: The final task's recorded test run shows only `timed out after 120s` and partial

- Task: `20261122192217_release-audit-the-final-task-s-recorded-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T04:59:19+00:00

## Summary

The attributed change attacks the suite's wall time exactly where the specification locates it: the per-test checkout copy becomes one lazily created, read-only shared source (`_shared_source`, cached `_install_python`), the read-only installer checks share one prepared real `install.sh` run per scenario group (`plain_install`, `opt_out_install`), and the bounded-check case is configured below the product default (1 s instead of 2 s) instead of waiting the full limit. No test method, assertion or scenario is removed; the external-command bound is lowered (600 -> 60), the elapsed-time assertions are tightened (90/60 -> 30) and no skip, xfail or default opt-out is added, so the diff strengthens rather than weakens the guarantees. The tests that share an installation only read it, so no test observes state mutated by another, and each module still builds its own state when run alone. README `## Tests` and CHANGELOG `[Unreleased]` both record the change, and the deterministic acceptance checks (full suite, `timeout 120`, `tests.test_install -v`, module-by-module runs, README/CHANGELOG greps) all pass per the QA verdict. The numeric before/after durations of the task report live outside this repository (project control artefact) and were not part of the review context; nothing in the repository contradicts the reported bound.

## Requirements

- R1/AC1: `python -m unittest discover -s tests` exits 0 with OK, 0 failures, 0 errors: pass — QA acceptance check passed (exit 0).
- R2/AC2: the same run exits 0 when wrapped in `timeout 120`: pass — QA acceptance check `timeout 120 python -m unittest discover -s tests` passed; the change removes the duplicated expensive work rather than hiding it.
- R3/AC3: no test method, assertion, fixture check or scenario removed, skipped or relaxed; executed count not lower, skip count not higher: pass — The diff contains no deletions of test methods and adds no skip/xfail/default opt-out. The only assertion edits tighten bounds (assertLess 90/60 -> 30), lower the subprocess timeout (600 -> 60) and update the expected directory list because the source tree is no longer created under each test's base (`source` moved to the shared read-only copy), which is stricter, not weaker.
- R4: every installer scenario still runs the real install.sh with a real pip install into a temporary HOME and a real detected login shell (install, re-install with exactly one marked block, --uninstall, opt-out, byte stability, fresh-login-shell resolution): pass — All scenarios are still present and still drive the real `install.sh` against a real checkout with `FORGEL_CODE_SOURCE`; only the number of repeated runs per read-only group is reduced. `python -m unittest tests.test_install -v` passes per QA.
- R5: wall time recovered only by removing duplication (one client install per scenario group, shared read-only build artefacts, bounded waits configured below the product default): pass — Exactly these three mechanisms are used: `_shared_source()`/cached `_install_python()`, class-level `plain_install`/`opt_out_install` for read-only checks, and `FORGEL_CODE_TIMEOUT=1` with tightened elapsed assertions in the bounded-check case.
- R6: tests stay independent; each module passes on its own; no test observes installation or profile state left by another test: pass — Only read-only checks share an installation, and untouched state cannot change between them; the sharing is per subclass (`cls = type(self)`), created lazily, so a module or single test run alone still performs its own real install. Modifying scenarios (re-install, uninstall, block removal) keep their own per-test installation. AC5 module runs passed per QA.
- R7: the default command runs the whole suite; no environment variable, marker or default option excludes any test: pass — The diff introduces no conditional skipping or defaulted exclusion; all changes are internal helpers.
- R8/AC6: README `## Tests` states the suite's runtime bound and that the documented command runs the whole suite: pass — Added paragraph states the command runs the whole suite with no opt-out and completes in under 120 seconds, covering the real installer scenarios; the README grep check passed.
- R9/AC7: CHANGELOG.md records the change under [Unreleased]: pass — A `### Changed` entry under `[Unreleased]` describes the de-duplication and the README update; the CHANGELOG grep check passed.
- R10/AC8: measured per-module/per-test durations recorded, so the reduction is a diagnosis rather than a guess (review-only): pass — The reduction targets precisely the time sinks named in the specification (per-test pip install, per-test checkout copy, full default bounded waits), and the CHANGELOG records that diagnosis; the numeric before/after figures belong to the task report, a project-control artefact outside this repository, and were not part of the review context. Nothing in the attributed diff or the repository contradicts the reported bound, and the deterministic 120 s run passed.
- AC5: test modules remain independently runnable (`tests.test_cli`, others): pass — QA acceptance check passed; the shared helpers are lazily initialised per module and per class.
- Acceptance criteria not reproducible in the repository: AC9 (next recorded release audit shows a completed, passing suite): pass — Verified on the runtime's audit output, not in this repository; nothing in the change can be judged against it here, and it is not a repository-side defect.

## Blocking

- none

## Test Removals

- none


