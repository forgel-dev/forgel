# Agent Run: Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install

- Task: `20261122174453_make-the-install-sh-path-check-strictly-`
- Status: `done`
- Repository: `code`
- Steps: 87
- Finished: 2026-11-22T18:28:52+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The whole fix stays inside install.sh and its tests; the client package and CHANGELOG are untouched.
- The verification bound stays at its current value; no new environment variable is added for it.
- The private temporary location is created under the system temporary directory with owner-only permissions and removed on every exit path.
- The release of the installer fix is re-checked and published by the normal release process after the fix is accepted; no version or tag is chosen here.
- The verification bound keeps its existing value: FORGEL_CODE_TIMEOUT when set, DEFAULT_VERIFY_LIMIT of 10 seconds otherwise, with a two-second grace before the forceful stop. No new environment variable or installer flag was added.
- The watchdog sleeps in whole seconds and, on timeout, signals the checked process with TERM, waits VERIFY_GRACE seconds, then signals with KILL, walking the process group when the child leads one and the process tree otherwise.
- The check's private directory is created under $TMPDIR (falling back to /tmp) with mode 700 under umask 077 and a random suffix from /dev/urandom, falling back to the pid when /dev/urandom or od is unavailable.
- The macOS `ls -ld` extended-attribute marker (`@`) is treated as unrelated to permissions, so the test asserts the ten-character permission field rather than the whole first word.
- The two empty scratch files err.txt and out.txt that were left over from an earlier session were removed; they are not part of the product.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 4
- Handoffs: 3
- Model calls: 87
- Estimated input tokens (all calls): 4145162
- Provider input/output tokens: 4130356 / 529067
- Provider cache hit/miss tokens: 3707136 / 423220
- Estimated prompt at the end: 60804 tokens
- State: `docs/program/agent/20261122174453_make-the-install-sh-path-check-strictly-.state.md`

## Specification (`docs/program/specs/20261122174453_make-the-install-sh-path-check-strictly-.md`)

# Task Spec: Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install

## Document Information

| Field | Value |
|-------|-------|
| Feature | Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install |
| Project | — |
| Task | `20261122174453_make-the-install-sh-path-check-strictly-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T17:45:34+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

install.sh verifies that a fresh login shell resolves forgel-code on PATH, but the check is unbounded: a shell that never answers blocks the installer, a timed-out shell can still be counted as success, and the check leaves temporary files in a predictable, world-readable location. The profile edit is also not byte-stable across re-installs, so repeated installs can accumulate blank lines and dropping the block does not restore the original file exactly.

**Outcome:** The fresh-shell check in install.sh runs under a hard time bound that stops the checked shell (graceful signal first, forceful stop after a short grace) and treats the timeout as failure; success requires an exact match between the reported path and the launcher path just written; failures report the profile file, the checked login shell, the written PATH block and the observed PATH; the check uses a private, unpredictably named temporary directory that is removed on every outcome with no leftover process; a second install leaves the profile byte-identical to the file after the first install and removing the block restores the original bytes; install.sh remains POSIX sh without GNU timeout; existing installer behaviour is unchanged and the new defect fixes are covered by tests in the repository suite.

## Product Intent

A one-command installer that never hangs and never lies about the result, and that leaves the user's shell profile exactly as it found it apart from the managed block.

## User Experience

Running the install command returns within a bounded time with either a verified PATH or an actionable failure message naming the file, shell, block and observed PATH; running the same install again changes nothing in the profile, and --uninstall restores the profile to its exact pre-install bytes.

## Roadmap

—

## Goals

- The fresh-shell check in install.sh is strictly bounded and cannot hang the installer.
- A timeout is a failure, and success requires an exact match with the launcher path.
- Failure output identifies profile file, checked shell, written block and observed PATH.
- The check leaves no process and no readable temporary file behind.
- Re-install is byte-idempotent and uninstall restores the original profile bytes.
- install.sh stays POSIX sh without GNU timeout.
- Every fixed defect is covered by a test in the repository suite.

## Non-Goals

- Changing the one-command install/update/uninstall lines documented in README.md
- Changing the PATH block contents, the marker lines or the `case "$PATH"` guard
- Changing login shell detection, profile selection, FORGEL_CODE_PROFILE or FORGEL_CODE_NO_MODIFY_PATH semantics
- Adding new opt-out environment variables or new installer flags
- Replacing `sh` with bash or any other shell; adding a Python-side helper for the shell check
- Depending on GNU coreutils `timeout`, `gtimeout`, `setsid` or `flock`
- Publishing or versioning the change

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code, installed as `forgel-code`. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-006: The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-001/D-005: The interactive client lives in a separate public repository in the `forgel-dev` organization; this task stays inside that client repository. | User, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: The fresh-shell check runs under a hard time bound; when the bound elapses the checked shell process is sent a graceful termination signal, and after a short grace period is forcefully stopped together with any remaining process in its group.
- **FR-2**: The timeout outcome is part of the success decision: a timed-out or signalled check is a failure and is never reported as a verified PATH.
- **FR-3**: Success is declared only when the path reported by the fresh login shell for forgel-code exactly equals the launcher path the installer just wrote; any other path, an empty answer, a non-zero shell exit status or a timeout is a failure.
- **FR-4**: On failure the installer prints a report that names the edited profile file, the login shell that was checked, the PATH block that was written and the PATH the fresh shell reported, and exits with a non-zero status.
- **FR-5**: Temporary files created by the check live in a directory usable only by the current user (owner-only permissions), carry unpredictable names, and are removed on every outcome — success, mismatch, timeout and interruption.
- **FR-6**: After the check finishes, no process started by it and no file created by it is left behind.
- **FR-7**: A second install over the same profile leaves the file byte-identical to the file after the first install; repeated installs do not accumulate blank lines.
- **FR-8**: Dropping the block restores the file content exactly as it was before the block was added, including whether the file ended with a trailing newline and the original file's existing final line.
- **FR-9**: install.sh stays POSIX sh, and the bounded check works without GNU coreutils `timeout`, on macOS and Linux.
- **FR-10**: Existing behaviour is preserved: login shell detection (including the macOS directory-service branch), profile selection, FORGEL_CODE_PROFILE, FORGEL_CODE_NO_MODIFY_PATH, idempotent --uninstall across candidate profiles including ~/.bashrc and FORGEL_CODE_PROFILE, --help, and exit code 2 for an unknown argument.
- **FR-11**: Each fixed defect gets a test in the repository test suite; no existing test is weakened, deleted or loosened.
- **FR-12**: The time bound is configurable through the existing FORGEL_CODE_TIMEOUT variable and has a default that keeps the installer usable when the variable is unset.

## Technical Requirements

- install.sh is a single POSIX sh script and must not require bash, zsh or a Python helper for the shell check.
- No dependency on GNU coreutils `timeout`; macOS ships without it.
- Tests must run offline, with HOME redirected to a temporary tree, and must not use the network.
- Repository rule: never weaken a test to make the suite pass; fix the product or the test's premise.
- All committed artifacts are English; commits are imperative mood and signed off.
- The check must not modify the profile in ways visible outside the marked block; profile writes stay confined to the managed block.
- The failure report must go to stderr and must not break the `| sh` pipeline contract for the success path.

## User Stories

- As a developer installing Forgel Code, I want the installer's PATH verification to finish within a bounded time so that a broken shell profile cannot hang my install.
- As a developer whose shell reports the wrong path, I want the failure message to name the profile file, the shell, the block written and the path observed so that I can fix it without guessing.
- As a security-conscious user, I want the installer's temporary files to be private and removed so that nothing of mine is left readable or behind.
- As a returning user, I want a second install to change nothing in my profile and an uninstall to restore it exactly so that my dotfiles stay byte-stable.

## Tests

- A check against a shell that never answers and ignores the graceful stop signal ends within a bounded time with a non-zero exit status and a report naming the profile file and the observed PATH.: `python -m pytest -q tests/test_install.py`
- The shell-inspection test finishes, leaves no stray child process and leaves no temporary file or temporary directory behind.: `python -m pytest -q tests/test_install.py`
- Installing twice over the same profile produces a file byte-identical to the file after the first install, and dropping the block restores the original content exactly.: `python -m pytest -q tests/test_install.py`
- The full repository test suite passes, including the existing installer, shell-detection, opt-out, uninstall and packaging tests.: `python -m pytest -q`
- Temporary files created by the check are not readable by other users and are absent after both a successful and a failed check.: `python -m pytest -q tests/test_install.py`
- install.sh parses as POSIX sh and contains no invocation of GNU `timeout`.: `sh -n install.sh`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: A check against a shell that never answers and ignores the graceful stop signal ends within a bounded time with a non-zero exit status and a report naming the profile file and the observed PATH.
- **AC-2**: The shell-inspection test finishes, leaves no stray child process and leaves no temporary file or temporary directory behind.
- **AC-3**: Installing twice over the same profile produces a file byte-identical to the file after the first install, and dropping the block restores the original content exactly.
- **AC-4**: The full repository test suite passes, including the existing installer, shell-detection, opt-out, uninstall and packaging tests.
- **AC-5**: Temporary files created by the check are not readable by other users and are absent after both a successful and a failed check.
- **AC-6**: install.sh parses as POSIX sh and contains no invocation of GNU `timeout`.

## Scope Boundaries

- install.sh: bounded fresh-login-shell check with graceful then forceful termination and timeout participating in the success decision
- install.sh: exact-match success rule against the launcher path just written
- install.sh: failure report naming profile file, checked login shell, written PATH block and observed PATH
- install.sh: private, unpredictably named temporary directory with cleanup on every outcome and no leftover process
- install.sh: byte-stable profile edit — repeated installs do not add blank lines, block removal restores original content including trailing-newline state
- tests/test_install.py: new tests covering the bounded check, the cleanup, the permissions and the byte-identical re-install
- Repository test suite stays green, including installer, shell-detection, opt-out, uninstall and packaging tests
- Changing the one-command install/update/uninstall lines documented in README.md
- Changing the PATH block contents, the marker lines or the `case "$PATH"` guard
- Changing login shell detection, profile selection, FORGEL_CODE_PROFILE or FORGEL_CODE_NO_MODIFY_PATH semantics
- Adding new opt-out environment variables or new installer flags
- Replacing `sh` with bash or any other shell; adding a Python-side helper for the shell check
- Depending on GNU coreutils `timeout`, `gtimeout`, `setsid` or `flock`
- Publishing or versioning the change

## Risks

- install.sh could not be read while writing this specification; the exact current shape of the fresh-shell check, of the profile append and of the block-removal code is therefore assumed, and a coding agent must confirm it against the file before editing.
- Killing only the direct child is not enough if the checked shell forks; the forceful stop must reach the process group, which is awkward in pure POSIX sh without `setsid` and may need a subshell plus a recorded pid.
- Signal handling for cleanup in POSIX sh differs between dash, bash-as-sh and zsh-as-sh; a trap that works on Linux may behave differently on macOS.
- Byte-identical re-install is easy to break again if the block is appended with unconditional extra newlines; the test must compare raw bytes, not split lines.
- Restoring the original trailing-newline state requires remembering whether the pre-block file ended with a newline; guessing it loses the guarantee.
- Owner-only temporary permissions can be defeated if the directory is created in a world-readable temp parent without a restrictive umask.
- A default bound that is too short can make the installer fail on slow machines with heavy profiles; too long makes the bound meaningless.
- Making the new tests deterministic requires a shell that ignores the graceful signal; that fixture process must itself be cleaned up or the suite hangs.

## Open Questions

- None.

## Affected Files

- install.sh
- tests/test_install.py
- tests/test_readme_install.py

## Assumptions

- The existing environment knob FORGEL_CODE_TIMEOUT (already cleared by the test environment helper) is the intended bound; its default is kept short, on the order of ten seconds, with a grace period of a couple of seconds before the forceful stop.
- The check's temporary directory is created under the system temp directory with owner-only permissions and a random suffix, and cleaned with a trap on EXIT plus the usual interrupt/termination signals.
- A mismatch in trailing-newline state is treated as a defect only for the region outside the managed block, since the block itself is appended text.
- The existing macOS directory-service branch is exercised in tests through the recorded `dscl` stub; the stub is unchanged.
- The new tests belong in tests/test_install.py next to the existing installer tests, since that file already runs the real install.sh into a temporary HOME.

## Related Documents

- README.md
- AGENTS.md
- FORGEL.md
- CHANGELOG.md
- releases/0.1.0/plan.md

## Revision History

- 1.0 — initial specification for the bounded PATH check and byte-identical re-install task

## External Dependencies

- **POSIX shell (/bin/sh, dash, ksh, mksh)** — mode `direct`; interface: install.sh is a POSIX sh script run through `#!/bin/sh` and through the documented `curl ... | sh` pipeline. The fresh-shell check launches the detected login shell with `-l -i -c '<command>'`, uses shell-level background jobs plus signal delivery (`kill -TERM`, then `kill -KILL` after a short grace period) and `wait` to bound the check without any GNU utility.; docs: POSIX.1 Shell Command Language (XCU), sections on shell invocation, asynchronous lists, signals and job control; the documented install pipeline in the repository README; evidence: The specification states install.sh stays POSIX sh and must not rely on GNU coreutils timeout; install.sh carries the `#!/bin/sh` shebang and the documented install path pipes the script into `sh`, so the shell is the single execution interface. No external shell-specific tooling (bash arrays, `timeout`, `mktemp --suffix`) may be assumed.
- **GNU coreutils timeout** — mode `stub`; interface: Explicitly NOT used. The bounded check is implemented inside install.sh with POSIX job control, so the dependency is only exercised negatively: the test suite puts a failing stand-in named `timeout` first on PATH and asserts the install still completes, proving no call path depends on the utility.; docs: GNU coreutils manual, `timeout` invocation: `timeout [OPTION] DURATION COMMAND [ARG]...`, exit status 124 on timeout, 125 on timeout's own failure, 126/127 for command not executable/found; coreutils is absent by default on macOS.; evidence: Dependency statement in the specification: "Explicitly NOT used: it is absent on macOS and the bounded check must not depend on it", with the coreutils manual as the referenced documentation. Because the contract is absence-derived, a deterministic stand-in is required to pin the behaviour in tests rather than relying on host tooling.
  ```
  #!/bin/sh
  # Deterministic stand-in for GNU coreutils `timeout`.
  # Contract mirrored: timeout [OPTION] DURATION COMMAND [ARG]...
  # The utility is treated as unavailable, so COMMAND is never executed.
  echo 'timeout: utility unavailable in this environment' >&2
  exit 127
  ```
- **macOS Directory Service CLI `dscl`** — mode `direct`; interface: Login shell detection on macOS runs `dscl . -read "$HOME" UserShell` and parses the `UserShell: <path>` line. The test suite substitutes a stub executable named `dscl` placed ahead of the real search path; the stub answers `UserShell: <shell>` for exactly that argument shape and exits 64 for any other arguments.; docs: tests/test_install.py — DSCL_STUB fixture excerpt; install.sh macOS branch that reads UserShell from dscl; evidence: The repository test suite declares the dscl contract itself: `tests/test_install.py` defines DSCL_STUB, which prints `UserShell: <shell>` and rejects any other argument shape with exit status 64. That fixture is the local test interface the code and tests address, so detection is exercised deterministically on Linux and macOS without the real directory service.
- **pytest / unittest test runners** — mode `direct`; interface: The repository suite is executed with `python -m pytest` and, when pytest is not installed, with the documented `python -m unittest` fallback. Both runners collect the same `unittest`-based test modules, including tests/test_install.py, so the new installer tests run under either entry point.; docs: README.md — Tests section (pytest entry point with the `unittest` fallback); evidence: README.md documents the Tests section with pytest as the primary runner and `unittest` as the fallback; the repository layout table lists `tests/` as a `unittest` suite, so both runners address the same test modules.


## Summary

Implemented the bounded, private, exact-match fresh-shell check in install.sh and made the profile edit byte-stable, then covered each fixed defect with tests in tests/test_install.py.

install.sh changes:
- The fresh-shell check runs through `bounded_run`, which starts a watchdog built from POSIX shell background jobs only (no GNU `timeout`, no `gtimeout`, no `setsid`, no `flock`): the watchdog counts the bound with `sleep`, sends `kill -TERM` to the checked process and everything it started, waits a short grace period, then sends `kill -KILL`, and records the timeout so the caller can treat it as failure.
- A timed-out or signalled check yields status 124, which can never be reported as a verified PATH; success additionally requires the reported `command -v forgel-code` to equal the launcher path byte for byte, plus a clean shell exit status and a non-empty answer.
- The verification failure report on stderr names the edited profile file, the checked login shell, the exact PATH block that was written and the PATH the fresh shell observed (plus what `forgel-code` resolved to and why the check failed).
- The check's temporary files live in a directory created under `$TMPDIR`/`/tmp` with a random name and mode 700 under `umask 077`; `cleanup_check` removes the watchdog, the checked process tree and the directory, and is called from the exit trap and from the HUP/INT/TERM traps, so nothing survives any outcome.
- The profile edit is byte-stable: the previous block is removed before the new one is appended, the separator comment records when the pre-block file lacked a final newline, so a second install rewrites the same bytes and removal restores the original file including its trailing-newline state.
- FORGEL_CODE_TIMEOUT still configures the bound with the existing ten-second default; detection, profile selection, opt-out variables, uninstall behavior, `--help` and the exit status 2 for an unknown argument are unchanged, and the script stays POSIX sh.

tests/test_install.py changes:
- New `InstallerBoundedCheckTest`: a shell that ignores the graceful stop is still stopped within the bound with a non-zero status, a report naming the profile and the observed PATH, no surviving process and no temporary entry; successful and failed checks leave no temporary entry; the check directory is created owner-only (`drwx------`).
- New `InstallerProfileByteStabilityTest`: installing twice leaves the profile byte-identical, repeated installs do not accumulate blank lines, and `--uninstall` restores the original bytes for a profile with and without a final newline.
- New `InstallerBoundedToolsTest`: install.sh never invokes GNU `timeout`, and the install succeeds with a failing `timeout` stand-in first on PATH.
- The owner-only assertion compares the ten-character permission field of `ls -ld` output: macOS appends an `@` marker when extended attributes are present, which is not a permission change and would otherwise make the assertion reject a correct 700 directory.

Testing: `python -m pytest -q tests/test_install.py` -> 49 passed; `python -m pytest -q` -> 197 passed, 137 subtests passed. `sh -n install.sh` is also exercised by `InstallerTest.test_script_is_executable_and_parses_with_sh`, which passes; the sandbox refused a direct `sh -n install.sh` invocation.

## Files Changed

- `err.txt`
- `install.sh`
- `out.txt`
- `tests/test_install.py`
- `tests/test_zz_probe.py`

## Commands

- `["python", "-m", "pytest", "-q", "tests/test_install.py", "-x", "-k", "InstallerTest"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_install.py", "-k", "Watchdog or ShellDetection or OptOut or Uninstall or ProfileOverride"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_zz_probe.py", "-s"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_zz_probe.py", "-s"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_install.py", "-k", "ShellDetection or Watchdog or OptOut or Uninstall or ProfileOverride", "-x"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_install.py", "-k", "Bounded or ByteStability", "-x"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_install.py", "-k", "Bounded or ByteStability", "-x"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_install.py"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_install.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
...................................................... [ 27%]
................................................. [ 52%]
........................................................................ [ 88%]
......................                           [100%]
197 passed, 137 subtests passed in 112.04s (0:01:52)

```

## Actions

- read_file: install.sh
- read_file: tests/test_install.py
- read_file: tests/test_readme_install.py
- read_file: forgel_code/cli.py
- write_file: install.sh
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-x', '-k', 'InstallerTest']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Watchdog or ShellDetection or OptOut or Uninstall or ProfileOverride']
- write_file: tests/test_zz_probe.py
- read_file: install.sh
- recall
- read_file: tests/test_install.py
- read_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']
- read_file: install.sh
- recall
- read_file: tests/test_install.py
- read_file: tests/test_zz_probe.py
- recall
- write_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']
- write_file: install.sh
- read_file: tests/test_install.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'ShellDetection or Watchdog or OptOut or Uninstall or ProfileOverride', '-x']
- read_file: tests/test_readme_install.py
- write_file: tests/test_install.py
- delete_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Bounded or ByteStability', '-x']
- write_file: tests/test_install.py
- read_file: install.sh
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Bounded or ByteStability', '-x']
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- recall
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py']
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- write_file: tests/test_install.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py']
- run: ['python', '-m', 'pytest', '-q']
- read_file: err.txt
- read_file: .gitignore
- read_file: out.txt
- delete_file: err.txt
- delete_file: out.txt
- run: ['sh', '-n', 'install.sh']
