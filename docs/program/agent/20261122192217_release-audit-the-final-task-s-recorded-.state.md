# Session State: Release audit: The final task's recorded test run shows only `timed out after 120s` and partial

- Task: `20261122192217_release-audit-the-final-task-s-recorded-`
- Session: 3
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- R1. From the repository root, `python -m unittest discover -s tests` exits 0 and reports `OK` with 0 failures and 0 errors.
- R2. That run completes in less than 120 seconds of wall clock, verified by running it under `timeout 120`.
- R3. No test method, assertion, fixture check or scenario is removed, skipped or relaxed: the number of executed test methods is not lower than at the parent commit and the number of skips is not higher.
- R4. Every installer scenario still runs the real `install.sh` with a real pip install into a temporary HOME and a real detected login shell: install, re-install (exactly one marked block), `--uninstall`, the `FORGEL_CODE_NO_MODIFY_PATH` opt-out, profile byte stability, and the fresh-login-shell check that resolves `forgel-code` to the written launcher.
- R5. Wall time is recovered only by removing duplication: one client install per scenario group instead of one per test, shared read-only build artefacts, and bounded-wait tests configured below the product default instead of waiting the full default limit per case.
- R6. Tests stay independent of each other: each test module passes when run on its own, and no test observes installation or profile state left by another test.
- R7. The default command runs the whole suite; no environment variable, marker or default option excludes any test from `unittest discover` or `pytest -q`.
- R8. The README `## Tests` section states the suite's runtime bound and that the documented command runs the whole suite.
- R9. CHANGELOG.md records the change under `[Unreleased]`.
- R10. Before changing code, the measured per-module or per-test durations that identify where the wall time goes are recorded, so the reduction is a diagnosis and not a guess.

## Acceptance Criteria

- AC1. `python -m unittest discover -s tests` finishes with exit code 0 and `OK`, without failures or errors.
- AC2. The same command still exits 0 when wrapped in `timeout 120`, i.e. the complete suite fits the bound the release audit applies.
- AC3. The diff removes no test method, assertion or scenario and adds no skip, xfail or default opt-out: the executed-test count does not drop and the skipped count does not rise compared with the parent commit (reviewed on the diff together with the run output).
- AC4. The real installer scenarios still pass one by one: `python -m unittest tests.test_install -v` exits 0 and its output shows the install, re-install, uninstall, opt-out, byte-stability and fresh-login-shell cases running.
- AC5. Test modules remain independently runnable: `python -m unittest tests.test_cli -v` and the other modules each exit 0 on their own.
- AC6. The README `## Tests` section states the runtime bound of the default suite.
- AC7. CHANGELOG.md `[Unreleased]` records the change.
- AC8. The task report carries the measured before/after durations that justify the bound is met (review).
- AC9. The next recorded release audit run of this repository shows a completed, passing suite instead of `timed out after 120s` (verified on the audit output, not in this repository).

## Constraints

- none

## Assumptions

- none

## Files Changed

- tests/probe_timing.py
- tests/test_install.py

## Actions

- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing', '-v']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_cli.py', 'tests/test_cli_extra.py', 'tests/test_extras.py', 'tests/test_packaging.py', 'tests/test_packaging_types.py', 'tests/test_readme_install.py', 'tests/test_stub_contract.py', '--durations=0', '-p', 'no:cacheprovider', '--no-header']
- read_file: tests/test_cli.py
- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing', '-v']
- recall
- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py']
- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing']
- read_file: _build_backend.py
- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: README.md
- read_file: README.md
- write_file: tests/probe_timing.py
- run: ['python', '-m', 'unittest', 'tests.probe_timing', '-v']

## Commands

- `['python', '-m', 'pytest', '-q', 'tests/test_install.py', '--durations=0', '-p', 'no:cacheprovider', '--no-header']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing', '-v']` -> exit 0
- `['python', '-m', 'pytest', '-q', 'tests/test_cli.py', 'tests/test_cli_extra.py', 'tests/test_extras.py', 'tests/test_packaging.py', 'tests/test_packaging_types.py', 'tests/test_readme_install.py', 'tests/test_stub_contract.py', '--durations=0', '-p', 'no:cacheprovider', '--no-header']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing', '-v']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing', '-v']` -> exit 1
- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing']` -> exit 0
- `['python', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 0
- `['python', '-m', 'unittest', 'tests.probe_timing', '-v']` -> exit 0

## Recent Observations

- read_file README.md: README.md: lines 196-214 of 214
- write_file tests/probe_timing.py
- run python -m unittest tests.probe_timing -v -> exit 0

## Next Step

Continue from the current repository state and the changed files.
