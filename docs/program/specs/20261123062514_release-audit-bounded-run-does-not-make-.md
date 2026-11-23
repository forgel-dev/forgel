# Task Spec: Release audit: `bounded_run` does not make the watchdog's timeout decision authoritative. After

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `bounded_run` does not make the watchdog's timeout decision authoritative. After |
| Project | — |
| Task | `20261123062514_release-audit-bounded-run-does-not-make-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T10:42:20+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

In `install.sh`, `bounded_run` reports the checked shell's own exit status as the outcome and treats the watchdog only as a killer: once the checked child exits, the parent looks for the `timed-out` marker and, when it is absent, immediately kills the watchdog and honours the child's status. A child that finishes after the configured limit but before the watchdog has written the marker is therefore reported as a successful check, so neither the hard bound nor the rule that a timed-out check fails the install is guaranteed. The release audit recorded this as a release blocker.

**Outcome:** The watchdog's timeout decision is authoritative: `bounded_run` resolves the outcome only after the watchdog has finished its decision, a bound that elapsed before the checked command exited is reported as status 124 and fails the install with a message naming the limit, a command that finished in time keeps its own status and output, no watchdog or marker is left behind, and the installer still never waits unboundedly.

## Product Intent

A one-command installer (D-004, D-007 in the engine plan) may only report an installation as verified when the fresh login shell really resolved `forgel-code` within the advertised hard time limit; a check that outlived the limit must never be reported as a success, otherwise the post-install verification claim is false.

## User Experience

A user who runs the piped installer sees either a successful verification of their fresh shell's PATH or, when the fresh shell does not answer within `FORGEL_CODE_TIMEOUT` seconds, a failure that names the limit and leaves no stray process or temporary directory behind; a slow shell can no longer slip through as a success just because its exit happened to land in the gap before the watchdog's decision.

## Roadmap

—

## Goals

- Make the watchdog's timeout decision authoritative for `bounded_run`.
- Guarantee that a check exceeding `FORGEL_CODE_TIMEOUT` fails the installation, whatever the ordering of the child's exit and the marker write.
- Preserve the success path's status and output and the installer's documented one-command behaviour.
- Prove the fix with a regression test that fails before and passes after, and keep the existing suite green.

## Non-Goals

- Changing the default `FORGEL_CODE_TIMEOUT` value, `VERIFY_GRACE`, or the documented meaning of either.
- Redesigning shell detection, profile selection, the marked PATH block, `--uninstall`, or the launcher layout.
- Replacing the watchdog with GNU coreutils `timeout` or any new external binary.
- Changing the engine-side release policy, release train or tag handling (D-001..D-007 concern the client split, not this check).
- Rewriting the release audit report itself; this task resolves the finding in code and tests.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: the client's working name is Forgel Code, installed as `forgel-code`, with a Pareto 20/80 scope; the installer's launcher name and layout follow from this. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-007: every client-facing operation is a parameterized command; the installer's post-install verification only checks that the `forgel-code` launcher resolves in a fresh login shell and performs no other client work. | User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: `bounded_run` must not treat the absence of the `timed-out` marker at the moment the checked child exits as proof that the bound did not elapse; the timeout decision must be resolved after the watchdog has reached its own decision.
- **FR-2**: When the bound elapsed before the checked command exited, `bounded_run` must set `CHECK_STATUS=124` regardless of the ordering between the child's exit and the marker write.
- **FR-3**: `verify_profile` must report `CHECK_STATUS=124` as a failed verification: a non-zero installer exit and a message that names the configured limit, never a success.
- **FR-4**: When the checked command exits before the bound elapses, `bounded_run` must return that command's own exit status and its captured output unchanged.
- **FR-5**: Every exit path of `bounded_run` must leave no watchdog process and no private check directory behind, including the timeout path and paths taken after a failure.
- **FR-6**: The wait for the watchdog's decision must itself be bounded by a fixed, small limit derived from `VERIFY_GRACE`, so `install.sh` cannot hang waiting for a watchdog that never answers.
- **FR-7**: The installer must remain POSIX `sh` (`sh -n install.sh` clean, `set -eu`) and must not invoke GNU `timeout` or any binary not already used by the script.
- **FR-8**: A regression test in `tests/test_install.py` must exercise the real `install.sh` with a fresh-shell check whose runtime exceeds `FORGEL_CODE_TIMEOUT` and assert that the install fails at the bound instead of reporting success.
- **FR-9**: No existing test may be weakened to accommodate the change.
- **FR-10**: The whole existing test suite must still pass.

## Technical Requirements

- `install.sh` is POSIX `sh` piped from `curl ... | sh`: it must never read stdin and must stay compatible with dash, ksh, zsh and bash.
- The script must not depend on GNU coreutils `timeout`; the existing watchdog plus `sleep`/`kill` is the mechanism.
- `set -eu` stays on, so every new variable must be initialised before use and every command whose failure is tolerable must be guarded.
- The install and uninstall contract in the header comment (prefix, bin directory, marked block, `--uninstall`, environment variables) must not change.
- Tests in `tests/test_install.py` run the real `install.sh` offline into a temporary `HOME` and are bounded by the module's `TIMEOUT = 60`; the new test must fit inside that budget.
- Repository rules: never weaken a test to make it pass; commits carry no tool attribution lines; artifacts are English.

## User Stories

- As a user running the piped installer, I want a fresh shell that exceeds the time limit to be reported as a failure, so that a successful install message really means `forgel-code` is on PATH.
- As a maintainer, I want the watchdog's timeout decision to be the single authority for the bounded check, so that the hard bound cannot be bypassed by an unlucky exit ordering.

## Tests

- A checked command that outlives FORGEL_CODE_TIMEOUT makes install.sh exit non-zero with a failure message naming the limit, even when the exit lands between the limit and the marker write.: `python -m pytest tests/test_install.py -q -k timeout or bounded`
- A checked command that finishes inside the limit keeps its own exit status and output, and the verification result is unchanged.: `python -m pytest tests/test_install.py -q -k verify or fresh`
- After a timed-out run and after a successful run, no watchdog process and no private forgel-code-check directory remain.: `python -m pytest tests/test_install.py -q -k cleanup or process or check_dir`
- The bounded wait for the watchdog decision terminates on its own, so no run of install.sh blocks indefinitely.: `python -m pytest tests/test_install.py -q`
- sh -n install.sh reports no syntax error and the script contains no invocation of GNU timeout.: `sh -n install.sh`
- The new regression test fails against the current bounded_run and passes against the fixed one.: review
- python -m pytest -q passes for the whole repository.: `python -m pytest -q`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: A checked command that outlives `FORGEL_CODE_TIMEOUT` makes `install.sh` exit non-zero with a failure message naming the limit, and this holds even when the command's exit lands between the limit and the watchdog's marker write.
- **AC-2**: A checked command that finishes inside the limit keeps its own exit status and output, and the installer's verification result is unchanged from the documented behaviour.
- **AC-3**: After a timed-out run and after a successful run, no watchdog process from the check and no private `forgel-code-check` directory remain.
- **AC-4**: The bounded wait for the watchdog decision terminates on its own, so no run of `install.sh` blocks indefinitely.
- **AC-5**: `sh -n install.sh` reports no syntax error and the script contains no invocation of GNU `timeout`.
- **AC-6**: The new regression test fails against the current `bounded_run` and passes against the fixed one.
- **AC-7**: `python -m pytest -q` passes for the whole repository.

## Scope Boundaries

- `bounded_run` in `install.sh`: how the checked child's exit, the watchdog's decision and the `timed-out` marker are combined into `CHECK_STATUS`/`CHECK_OUTPUT`.
- `verify_profile` in `install.sh`: treating the timed-out status as a failure of the installation.
- `cleanup_check` and every exit path: releasing `CHECK_CHILD`, `CHECK_WATCHER` and `CHECK_DIR` without leaking a process or a private directory.
- The header comment in `install.sh` that describes the bounded check, so the documented behaviour matches the code.
- A regression test in `tests/test_install.py` that drives the real `install.sh` with a fresh-shell check that outlives `FORGEL_CODE_TIMEOUT` and asserts the install fails at the timeout.
- Keeping the script POSIX `sh` and free of a GNU `timeout` dependency.
- Changing the default `FORGEL_CODE_TIMEOUT` value, `VERIFY_GRACE`, or the documented meaning of either.
- Redesigning shell detection, profile selection, the marked PATH block, `--uninstall`, or the launcher layout.
- Replacing the watchdog with GNU coreutils `timeout` or any new external binary.
- Changing the engine-side release policy, release train or tag handling (D-001..D-007 concern the client split, not this check).
- Rewriting the release audit report itself; this task resolves the finding in code and tests.

## Risks

- Timing-based regression tests are inherently racy: a delay that is too short may not exceed the bound, and one that is too long may hit the suite's 60-second subprocess bound, so the test needs margins on both sides.
- Waiting for the watchdog can itself introduce a hang if the wait is not bounded; getting the synchronisation wrong trades a race for a deadlock.
- Killing the watchdog too early on the success path can still leave the marker unwritten and the decision unresolved, reproducing the defect in the opposite direction.
- On hosts where `kill` to a finished pid or `wait` on a non-child behaves differently (dash vs. ksh vs. zsh), cleanup may print a spurious error under `set -eu`.
- The release audit finding lives outside this repository, so the fix cannot be confirmed against the audit text itself; only the described behaviour can be tested.
- An implementation that simply lengthens the grace period would hide the race rather than make the decision authoritative and would not fail the intended regression test.

## Open Questions

- None.

## Affected Files

- install.sh (bounded_run, verify_profile, cleanup_check and the header comment describing the bounded check)
- tests/test_install.py (new regression test for a check that outlives the limit)

## Assumptions

- The watchdog implementation and the `timed-out` marker path inside the private check directory are the only place where the bound is decided, so resolving that decision after the watchdog is enough to make it authoritative.
- The existing grace period `VERIFY_GRACE=2` is an acceptable upper bound for waiting on the watchdog's decision; no new configuration variable is introduced.
- The regression test can obtain a shell that ignores or delays its startup work through a profile written by the test itself, so the delay is deterministic enough to exceed a small `FORGEL_CODE_TIMEOUT`.
- `verify_profile` remains the only caller that interprets `CHECK_STATUS=124`, so the failure wording lives there.

## Related Documents

- README.md (one-command install section)
- releases/0.1.0/release.md
- CHANGELOG.md

## Revision History

- v1: initial specification for the release-audit finding on bounded_run.

## External Dependencies

- **POSIX shell (`/bin/sh`, dash, bash, zsh, ksh)** — mode `direct`; interface: Execute `install.sh` as a POSIX shell script: the suite runs the real `install.sh` as a subprocess through `/bin/sh` (or the script's shebang) — argv, stdin/stdout/stderr and exit status only; the installer and tests additionally start login interactive shells as `-l -i -c` invocations of the available shell (`/bin/sh`, dash, bash, zsh, ksh). No emulation layer is needed because the concrete shell executable is provided by the host environment.; docs: POSIX.1-2017 Shell Command Language; repository contract quoted in the header of `install.sh`; evidence: The header of `install.sh` states the POSIX shell contract for the script, and `tests/test_install.py` executes the real `install.sh` as a subprocess, so the shell is consumed only through its standard process interface.
- **Python 3 with pip (the interpreter the installer installs the client with)** — mode `direct`; interface: Invoke the interpreter selected by `FORGEL_CODE_PYTHON` (falling back to `python3`) to create the install prefix and install the client; the test module first probes an interpreter of version 3.9 or newer whose `python -m pip --version` succeeds, then runs the installer.; docs: `pyproject.toml` in the code repository (requires-python and build backend); `README.md`, Tests section; evidence: `pyproject.toml` declares the Python version requirement and packaging metadata that `install.sh` installs against; `README.md`'s Tests section documents probing a Python 3.9+ interpreter with pip before running the installer.
- **pytest / unittest test runner** — mode `direct`; interface: Collect and run `tests/test_install.py` with `python -m pytest -q`; the same module is also runnable with the standard library as `python -m unittest discover -s tests -v`, so the suite does not depend on a third-party runner being installed.; docs: `README.md`, Tests section; `tests/test_install.py`; evidence: `README.md`'s Tests section names the runner and command for the suite, and `tests/test_install.py` is the module it collects; the file is a plain test module, so the stdlib `unittest` entry point covers the same collection.
