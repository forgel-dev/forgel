# Agent Run: Release audit: The final task's recorded test run shows only `timed out after 120s` and partial

- Task: `20261122192217_release-audit-the-final-task-s-recorded-`
- Status: `done`
- Repository: `code`
- Steps: 19
- Finished: 2026-11-23T04:08:36+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The README bound sentence names both "120 seconds" and "about two minutes" so the acceptance grep matches on either token.
- The bound is documented as applying to a development machine, matching the specification's own assumption that the audit machine resembles one.
- The `elapsed 80.01s rc=0` run under a 120 s timeout is the AC2 evidence, executed with `sys.executable` because `python` is not on `PATH` under `sh -c` in this environment (the earlier exit 127 was that, not the suite).
- The pre-change timings (134.1 s suite, 91.4 s for `tests.test_install`, and the 124/partial run at the 120 s bound) were recorded in the earlier session before code was touched and are reported here as the "before" half of AC8.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 19
- Estimated input tokens (all calls): 532104
- Provider input/output tokens: 561957 / 9332
- Provider cache hit/miss tokens: 532736 / 29221
- Estimated prompt at the end: 35238 tokens
- State: not needed

## Specification (`docs/program/specs/20261122192217_release-audit-the-final-task-s-recorded-.md`)

# Task Spec: Release audit: The final task's recorded test run shows only `timed out after 120s` and partial

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The final task's recorded test run shows only `timed out after 120s` and partial |
| Project | — |
| Task | `20261122192217_release-audit-the-final-task-s-recorded-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T21:26:50+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit for the final milestone task ("make a new terminal find forgel-code on PATH") recorded only `timed out after 120s` and partial progress for the full test suite, with no completed passing run. The acceptance criterion "the full repository test suite passes" therefore has no evidence and the release audit finding stays open. The repository's suite, as it stands, does not finish inside the time bound the audit runner applies: it repeats expensive real work (a full offline pip install of the client per installer test, 10 s default waits for the bounded fresh-shell check, repeated builds/installs in the packaging and extras tests). This task makes the whole suite finish and pass inside that bound without weakening a single test, and records the evidence.

**Outcome:** A single run of the full suite from a clean checkout exits 0 with zero failures and zero errors inside the audit's 120 s bound, executing the same installer, packaging, extras and CLI scenarios with the same assertions as before; the README states the suite's runtime bound, the CHANGELOG records the change, and the release audit finding for the final task can be closed by the next recorded run.

## Product Intent

Forgel Code is published with its audit: per FORGEL.md and AGENTS.md, a release without its audit is not published, and the recorded test run is the evidence that the shipped client installs and works. The milestone's product promise is that after `curl ... | sh` a new terminal finds `forgel-code` on PATH; that promise is only releasable when the suite that proves it completes and passes.

## User Experience

A maintainer reading the release audit sees a complete, green suite run with a total duration under the bound instead of a truncated log ending in `timed out after 120s`, and can publish. A contributor running the documented command gets the same complete result in under two minutes instead of waiting for a suite that does not finish, with the same installer behaviour verified end to end (real `install.sh`, real pip install into a temporary HOME, real login shell resolving `forgel-code`).

## Roadmap

—

## Goals

- A complete, passing, timed run of the full suite exists and fits the 120 s bound the release audit applies.
- Installer coverage stays real and unchanged in substance: the same scenarios, assertions and real external commands.
- The suite's runtime bound is documented so the next release audit knows what to expect.
- The release audit finding for the final task is resolved with recorded evidence.

## Non-Goals

- Changing install.sh behaviour, the PATH block, profile detection or the fresh-shell check (the product change of the milestone is already in place).
- Deleting, skipping, marking xfail, or relaxing any test, assertion or covered scenario.
- Replacing the real install.sh runs with a stub, a mock or a fake pip.
- Adding a default-on fast path, marker or environment variable that leaves part of the suite unrun under `python -m unittest discover -s tests` or `python -m pytest -q`.
- Introducing a new test framework, a runner daemon or any third-party test dependency beyond the existing `test` extra.
- Assigning, promising or rewriting release versions, tags or the `releases/` records.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | User decision log, user accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: R1. From the repository root, `python -m unittest discover -s tests` exits 0 and reports `OK` with 0 failures and 0 errors.
- **FR-2**: R2. That run completes in less than 120 seconds of wall clock, verified by running it under `timeout 120`.
- **FR-3**: R3. No test method, assertion, fixture check or scenario is removed, skipped or relaxed: the number of executed test methods is not lower than at the parent commit and the number of skips is not higher.
- **FR-4**: R4. Every installer scenario still runs the real `install.sh` with a real pip install into a temporary HOME and a real detected login shell: install, re-install (exactly one marked block), `--uninstall`, the `FORGEL_CODE_NO_MODIFY_PATH` opt-out, profile byte stability, and the fresh-login-shell check that resolves `forgel-code` to the written launcher.
- **FR-5**: R5. Wall time is recovered only by removing duplication: one client install per scenario group instead of one per test, shared read-only build artefacts, and bounded-wait tests configured below the product default instead of waiting the full default limit per case.
- **FR-6**: R6. Tests stay independent of each other: each test module passes when run on its own, and no test observes installation or profile state left by another test.
- **FR-7**: R7. The default command runs the whole suite; no environment variable, marker or default option excludes any test from `unittest discover` or `pytest -q`.
- **FR-8**: R8. The README `## Tests` section states the suite's runtime bound and that the documented command runs the whole suite.
- **FR-9**: R9. CHANGELOG.md records the change under `[Unreleased]`.
- **FR-10**: R10. Before changing code, the measured per-module or per-test durations that identify where the wall time goes are recorded, so the reduction is a diagnosis and not a guess.

## Technical Requirements

- The suite stays standard-library `unittest`: `python -m unittest discover -s tests` must work from a checkout with nothing installed, exactly as the README promises.
- The suite must also keep passing under `python -m pytest -q` with the wheel's `test` extra.
- Tests run offline: `PIP_NO_INDEX=1` and no package-index access.
- Repository rule: never weaken a test to make it pass; fix the product or the test's premise.
- Do not change install.sh, `_build_backend.py` metadata behaviour or `dependencies = []`; the client keeps zero runtime dependencies.
- All committed artifacts are English, including commit messages.
- Each test that starts an external process keeps a subprocess timeout; the suite's total budget is the sum of those bounds, not a single unbounded wait.

## User Stories

- As a maintainer preparing a release, I want a complete passing run of the whole suite inside the audit's time bound so that the release is not blocked by missing evidence.
- As a contributor, I want the suite to stay as strict as it is today while finishing quickly, so that a faster run never means a weaker guarantee about install.sh.
- As a reviewer of the release, I want the runtime bound and the change recorded in the repository, so that I can tell a complete run from a truncated one.

## Tests

- AC1 and AC2: the full suite exits 0 and fits the 120 s bound: `sh -c timeout 120 python -m unittest discover -s tests`
- AC4: the real installer scenarios still run and pass individually: `python -m unittest tests.test_install -v`
- AC5: test modules remain independently runnable: `python -m unittest tests.test_cli -v`
- AC6: the README Tests section states the runtime bound: `sh -c sed -n '/^## Tests/,/^## /p' README.md | grep -Eiq 'minute|120'`
- AC7: CHANGELOG [Unreleased] records the change: `sh -c sed -n '/## \[Unreleased\]/,/## \[0.1.0\]/p' CHANGELOG.md | grep -Eiq 'suite|tests'`
- AC3: no test method, assertion, scenario or skip was weakened: review
- AC8: measured before/after durations justify that the bound is met: review
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: AC1. `python -m unittest discover -s tests` finishes with exit code 0 and `OK`, without failures or errors.
- **AC-2**: AC2. The same command still exits 0 when wrapped in `timeout 120`, i.e. the complete suite fits the bound the release audit applies.
- **AC-3**: AC3. The diff removes no test method, assertion or scenario and adds no skip, xfail or default opt-out: the executed-test count does not drop and the skipped count does not rise compared with the parent commit (reviewed on the diff together with the run output).
- **AC-4**: AC4. The real installer scenarios still pass one by one: `python -m unittest tests.test_install -v` exits 0 and its output shows the install, re-install, uninstall, opt-out, byte-stability and fresh-login-shell cases running.
- **AC-5**: AC5. Test modules remain independently runnable: `python -m unittest tests.test_cli -v` and the other modules each exit 0 on their own.
- **AC-6**: AC6. The README `## Tests` section states the runtime bound of the default suite.
- **AC-7**: AC7. CHANGELOG.md `[Unreleased]` records the change.
- **AC-8**: AC8. The task report carries the measured before/after durations that justify the bound is met (review).
- **AC-9**: AC9. The next recorded release audit run of this repository shows a completed, passing suite instead of `timed out after 120s` (verified on the audit output, not in this repository).

## Scope Boundaries

- Remove duplicated expensive work from the test suite so the full suite completes inside the recorded 120 s bound.
- Keep every installer, packaging, extras and CLI scenario and every assertion; only the repetition goes.
- Bound every external command the tests start by a subprocess timeout well below the suite budget, so no single waiting step can consume it.
- Record the measured before/after timings that show where the suite's time went and that the budget is met.
- State the suite's runtime bound in the README `## Tests` section.
- Record the change in the `[Unreleased]` section of CHANGELOG.md.
- Changing install.sh behaviour, the PATH block, profile detection or the fresh-shell check (the product change of the milestone is already in place).
- Deleting, skipping, marking xfail, or relaxing any test, assertion or covered scenario.
- Replacing the real install.sh runs with a stub, a mock or a fake pip.
- Adding a default-on fast path, marker or environment variable that leaves part of the suite unrun under `python -m unittest discover -s tests` or `python -m pytest -q`.
- Introducing a new test framework, a runner daemon or any third-party test dependency beyond the existing `test` extra.
- Assigning, promising or rewriting release versions, tags or the `releases/` records.

## Risks

- The suite may not fit under 120 s even after duplication is removed, because every installer scenario pays for a real pip install. If the floor stays above the bound, the bound itself must be raised in the audit runner, which is outside this repository, and the finding cannot be closed here.
- Sharing one installation across tests can couple them: a suite that passes in one order may fail in another, and a shared fixture can hide a real regression that a fresh install would expose.
- Shortening the configured bounded-check limit can make those tests flaky on a loaded machine.
- Reviewers may read the change as weakening tests; the diff and the run output must show identical assertions and scenarios.
- The audit runner may have cancelled the run for a reason other than total runtime (host load, cold caches); then this change alone does not change the recorded outcome.
- A local run of 119 s is not evidence: variance on the audit machine can push a marginal suite over the bound.

## Open Questions

- Is the release audit runner's time bound a fixed 120 s, or is it configured per project? If it is configurable, raising the bound may be the correct fix instead of compressing the suite; this cannot be decided from the `code` repository.

## Affected Files

- tests/test_install.py
- tests/test_extras.py
- tests/test_packaging.py
- tests/test_cli.py
- tests/test_cli_extra.py
- tests/__init__.py
- README.md
- CHANGELOG.md

## Assumptions

- The 120 s figure is the bound the release audit runner applies to the recorded test run; if the runner's bound is configurable, the same requirement holds with that number.
- The recorded `timed out after 120s` is total wall clock rather than one single hanging test; if one test hangs, making that test finish satisfies the same requirements.
- The audit machine resembles a normal development machine; the suite must have margin under 120 s, so a run near 119 s locally is not sufficient evidence.
- `pip` as a Python module and a POSIX login shell (`sh`, `zsh` or `bash`) are available in the test environment, which the existing suite already assumes.
- The user-decision log records no decision about test runtime or audit bounds, so nothing here contradicts a recorded product decision.

## Related Documents

- releases/0.1.0/release.md
- releases/0.1.0/plan.md
- CHANGELOG.md
- README.md
- FORGEL.md
- AGENTS.md

## Revision History

- v1 — initial specification for the release-audit remediation task.

## External Dependencies

- **Forgel release audit runner (runtime tool that records the test run)** — mode `direct`; interface: Owned by the Forgel runtime, not by repository code: the runtime's release-audit stage executes the repository's declared test command, captures stdout/stderr as the release evidence, and terminates the run when its per-run time bound (observed: 120 s) elapses. Deterministic use from the repository side is therefore indirect: expose exactly one declared, fast, deterministic test entry point (AGENTS.md 'Change Workflow' step 4: `make test`) that exits 0 well inside the bound and produces progress output as it goes; unit tests must never invoke or depend on the runner itself, and any simulated runner belongs in a test fixture, never in product code.; docs: FORGEL.md (Releases; Runtime Process Model), AGENTS.md (Release Rules; Change Workflow); evidence: FORGEL.md 'Releases': 'A release without its audit is not published'; AGENTS.md 'Release Rules' repeats it, and 'Change Workflow' step 4 declares the repository test command as `make test` (with `make lint`). The runner's existence and its 120 s per-run bound are recorded in this task's release-audit output: the final recorded test run shows only `timed out after 120s` with partial progress and no completed passing suite.
- **pip (Python packaging)** — mode `direct`; interface: `python -m pip install --no-index --target <dir> <checkout>` executed offline by the repository's `install.sh`, followed by assertions in the unittest suite on the installed distribution: entry-point metadata (`Requires-Dist`, `Provides-Extra`) and the console script `forgel-code` written into the target's bin directory, which must be executable and importable from the target.; docs: https://pip.pypa.io/en/stable/; evidence: The repository's `install.sh` is the offline installation entry point (`python -m pip install --no-index --target`-style installation of the checkout) and the test suite invokes the same pip path and asserts the resulting metadata and the `forgel-code` console script; project AGENTS.md 'Layout' declares `tests/` as the `unittest` suite and `environment.yaml` as the environment contract covering build, commands and env.
- **POSIX login shell (sh, zsh, bash)** — mode `direct`; interface: Each shell in the supported set is started as `<shell> -l -i -c 'command -v forgel-code'` from a cleared environment (inherited PATH removed) so that only the profile block written by `install.sh` can resolve the launcher; exit status 0 with an absolute path on stdout is the pass condition, non-zero or empty stdout is a failure. Shells absent from the image are skipped by the test matrix rather than failing it.; docs: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html ; https://www.gnu.org/software/bash/manual/ ; https://zsh.sourceforge.io/Doc/; evidence: `install.sh` writes the PATH/profile block for the launcher, and the test invokes `<shell> -l -i -c 'command -v forgel-code'` from a cleared environment to prove the block puts the launcher on PATH; the project AGENTS.md 'Change Workflow' requires the suite to run against the installed checkout, and `environment/` plus `environment.yaml` define the shells available in the sandbox image.
- **GNU coreutils timeout** — mode `direct`; interface: `timeout [OPTION] DURATION COMMAND [ARG]...`, used as `timeout 120 <repository test command>` in the acceptance check to prove the full suite exits 0 within the 120 s bound. Exit status 0 means the suite finished in time; exit status 124 means the bound elapsed and the check must be treated as a failure, with the partial output kept as evidence.; docs: https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html; evidence: The acceptance criterion 'the full repository test suite passes' is checked by wrapping the declared test command (`make test`, AGENTS.md 'Change Workflow' step 4) in `timeout 120`; the current recorded run shows the suite reaching the bound and being cut off (`timed out after 120s` with partial progress), which is exactly the exit-124 case the command distinguishes.


## Summary

Finished the release-audit remediation by completing the README `## Tests` section (the only failing acceptance point, AC6), then re-verified the whole suite.

README.md `## Tests` now states both contract points explicitly: the documented command `python -m unittest discover -s tests` "runs the whole suite — no environment variable, marker or default option leaves a test out" and "completes in under 120 seconds (about two minutes)", and that the budget covers the installer scenarios, which run the real `install.sh` with a real pip install into a temporary home and a real detected login shell. The existing `pip install ...[test]` + `python -m pytest -q` block and the unittest command the README guard tests require are unchanged.

Nothing else was touched in this session: `tests/test_install.py` (shared per-scenario-group installation, one read-only checkout copy, bounded-check limit configured below the product default) and the CHANGELOG `[Unreleased]` entry were already in place from the earlier session and were left as-is.

Diagnosis and measurements (R10/AC8), measured before any change:
- suite did not complete inside the audit bound: `timeout 120` produced partial progress and exit 124; one completed measurement of the pre-change 202 tests took 134.1 s with `tests.test_install` alone at 91.4 s (54 tests); per-test `--durations` plus a timing probe showed the cost was one full checkout copy + offline pip install per installer test, the opt-out install repeated per test in `InstallerOptOutTest`, another copy in `PlainPipInstallTest`, and bounded-check cases waiting the product's default limit.

After the change (this session):
- `python -m unittest discover -s tests` — exit 0, `Ran 202 tests in 84.017s`, `OK`.
- same command under a 120 s bound (`subprocess.run(..., timeout=120)` with `sys.executable`) — exit 0, `elapsed 80.01s rc=0`, `OK`, so AC2 holds with margin.
- `python -m unittest tests.test_install` — exit 0, `Ran 54 tests in 52.465s`, `OK`.
- `python -m unittest tests.test_readme_install tests.test_install tests.test_cli -v` — exit 0, 151 tests, `OK`; the verbose output shows the install, re-install, uninstall, opt-out, byte-stability and fresh-login-shell cases plus the `--uninstall`/bounded-check/watchdog/profile-override cases all running (AC4, AC5, and the README guard suite green against the new text).
- `python -m pytest -q` — exit 0, `202 passed, 137 subtests passed in 80.48s` (R7: the whole suite, no marker or default option excluding anything).
- README AC6 check re-read from the file: the `## Tests` body contains "120 seconds (about two minutes)" and the whole-suite statement, so `sed -n '/^## Tests/,/^## /p' README.md | grep -Eiq 'minute|120'` matches.
- CHANGELOG `[Unreleased]` keeps the `### Changed` entry recording the suite change and the README bound (AC7).

No test method, assertion, fixture check or scenario was removed, skipped, xfailed or relaxed, and no default opt-out, marker or environment variable was added.

## Files Changed

- `CHANGELOG.md`
- `README.md`
- `tests/test_install.py`

## Commands

- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-c", "import subprocess,sys,time\ns=time.monotonic()\ntry:\n    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],capture_output=True,text=True,timeout=120)\n    print('elapsed %.2fs rc=%s' % (time.monotonic()-s, r.returncode))\n    print(r.stderr.strip().splitlines()[-1])\nexcept subprocess.TimeoutExpired:\n    print('TIMED OUT after %.2fs' % (time.monotonic()-s))"]` → exit 0
- `["python", "-m", "unittest", "tests.test_readme_install", "tests.test_install", "tests.test_cli", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install"]` → exit 0
- `["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
..........................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 202 tests in 79.948s

OK

```

## Actions

- read_file: README.md
- read_file: README.md
- read_file: tests/test_readme_install.py
- write_file: README.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['sh', '-c', "sed -n '/^## Tests/,/^## /p' README.md | grep -Eiq 'minute|120' && echo AC6-OK; sed -n '/^## Tests/,/^## /p' README.md"]
- run: ['grep', '-n', '-E', 'minute|120', 'README.md']
- read_file: README.md
- run: ['timeout', '120', 'python', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['python', '-c', "import subprocess,sys,time\ns=time.monotonic()\ntry:\n    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],capture_output=True,text=True,timeout=120)\n    print('elapsed %.2fs rc=%s' % (time.monotonic()-s, r.returncode))\n    print(r.stderr.strip().splitlines()[-1])\nexcept subprocess.TimeoutExpired:\n    print('TIMED OUT after %.2fs' % (time.monotonic()-s))"]
- run: ['python', '-m', 'unittest', 'tests.test_readme_install', 'tests.test_install', 'tests.test_cli', '-v']
- read_file: CHANGELOG.md
- list_files
- read_file: .gitignore
- run: ['python', '-m', 'unittest', 'tests.test_install']
- run: ['python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider']
