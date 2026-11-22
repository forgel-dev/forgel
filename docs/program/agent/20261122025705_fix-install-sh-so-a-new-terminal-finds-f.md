# Agent Run: Fix install.sh so a new terminal finds forgel-code on PATH

- Task: `20261122025705_fix-install-sh-so-a-new-terminal-finds-f`
- Status: `done`
- Repository: `code`
- Steps: 62
- Finished: 2026-11-22T03:36:29+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The fix belongs to the `code` repository, which holds install.sh, the launcher and the installer tests.
- The earlier install run used the opt-out switch, so no profile was edited at all; that path works as designed and the change focuses on the silent-ineffective-profile case.
- The default tag v0.1.0 stays; the release is published after this change is accepted so the tag contains the fixed script.
- $SHELL counts as unusable when it is empty or names a shell the installer does not handle; because a POSIX shell re-exports SHELL from the passwd entry, the detection tests set SHELL to the empty string to exercise the account login-shell lookup, which behaves exactly like an unset value inside the script.
- The account login-shell lookup tries `dscl . -read "$HOME" UserShell` whenever dscl is on PATH (the recorded stub interface), then getent/passwd, then falls back to /bin/sh, which reads ~/.profile.
- Verification runs only the real `-l -i` startup of the detected shell under `env -i`; when that shell's login mode reads no file (a POSIX sh with no login file), the block is unverifiable, so the installer fails and names the file rather than reporting a false success.
- The --uninstall candidate list is exactly .zshrc, .zprofile, .zshenv, .bash_profile, .bash_login and .profile, matching the recorded assumption.
- README's opt-out example uses the default $HOME/.local/bin so the shown line is character-identical to what the installer prints for a default install.
- No CHANGELOG entry was added because the specification lists only install.sh, tests/test_install.py and README.md as affected files and no decision changed.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 62
- Estimated input tokens (all calls): 4473866
- Provider input/output tokens: 4832452 / 167957
- Estimated prompt at the end: 99205 tokens
- State: not needed

## Specification (`docs/program/specs/20261122025705_fix-install-sh-so-a-new-terminal-finds-f.md`)

# Task Spec: Fix install.sh so a new terminal finds forgel-code on PATH

## Document Information

| Field | Value |
|-------|-------|
| Feature | Fix install.sh so a new terminal finds forgel-code on PATH |
| Project | — |
| Task | `20261122025705_fix-install-sh-so-a-new-terminal-finds-f` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T03:18:10+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

install.sh currently chooses the profile file from $SHELL alone and writes the PATH block without checking that the detected login shell actually reads that file. On machines where $SHELL is unset, empty or names an unhandled shell the block lands in a file the login shell never sources, and bash installs can end up in ~/.bashrc which a login bash does not read, so a new terminal cannot find forgel-code on PATH. The installer also gives no evidence that the change became active.

**Outcome:** install.sh detects the account login shell when $SHELL is unusable, writes the marked PATH block into the file that detected shell actually reads for interactive login sessions (creating it when missing), verifies in a freshly started login interactive shell with a cleared environment that `command -v forgel-code` resolves to the launcher it just wrote, and reports the detected shell, the edited file and the verification result. A failed verification exits non-zero and names the file and block. Re-running keeps exactly one marked block per edited file, --uninstall removes the block from every candidate file, the opt-out variables still leave every profile file untouched and print the exact export line, the `curl … | sh` shape still works, and README documents all of it.

## Goals

- A new terminal started after install resolves `forgel-code` to the installed launcher.
- Profile file selection follows the detected login shell rather than $SHELL alone.
- The installer proves the result in a freshly started login interactive shell and reports it.
- Idempotent re-runs and complete --uninstall behaviour are preserved and documented.

## Non-Goals

- Changing where the client is installed or the launcher format
- Changing FORGEL_CODE_HOME / FORGEL_CODE_BIN defaults
- Adding new installer options or environment variables beyond those already documented
- Widening the client or engine command surface
- Removing the installation prefix or the launcher outside --uninstall behaviour already present
- Changing the README one-command install path, tag pinning or the pip-install line policy enforced by tests/test_readme_install.py
- Supporting fish, csh, tcsh, PowerShell or non-POSIX shells for profile editing
- Windows support for the installer

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The client is a thin UI over the engine's parameterized commands. It does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |

## Functional Requirements

- **FR-1**: install.sh must not derive the profile file from $SHELL alone: when $SHELL is unset, empty or names an unhandled shell, it reads the account login shell (macOS `dscl . -read "$HOME" UserShell`, otherwise the passwd entry) and only then falls back to $HOME/.profile.
- **FR-2**: For zsh the block goes into $HOME/.zshrc, created when missing.
- **FR-3**: For bash the block goes into the first existing file of $HOME/.bash_profile, $HOME/.bash_login, $HOME/.profile; if none exists, $HOME/.bash_profile is created. The block is never written to $HOME/.bashrc alone, because a login bash shell does not read it.
- **FR-4**: FORGEL_CODE_PROFILE still overrides the chosen file; FORGEL_CODE_NO_MODIFY_PATH and FORGEL_CODE_NO_PROFILE_EDIT still leave every profile file untouched, print the exact `export PATH="<bin>:$PATH"` line and exit 0.
- **FR-5**: After writing the block the installer verifies it: it starts the detected login shell as a login interactive shell in a cleared environment (HOME, SHELL, TERM, minimal PATH) and resolves `command -v forgel-code`; the result must be the launcher just written.
- **FR-6**: If verification fails, the installer exits non-zero and prints the edited profile file, the block written and the PATH seen in the fresh shell. It must not claim the change is active unless verification passed.
- **FR-7**: On success the installer prints the detected shell, the profile file written and the fresh-shell check result.
- **FR-8**: Re-running keeps exactly one marked block per edited file and leaves the rest of the file byte-identical.
- **FR-9**: --uninstall removes the marked block from every profile file this installer can have written (.zshrc, .zprofile, .zshenv, .bash_profile, .bash_login, .profile), leaves the rest of each file unchanged, and still removes the prefix and the launcher.
- **FR-10**: The documented `curl … | sh` shape keeps working: POSIX sh, passes `sh -n`, uses `set -eu`, never reads stdin.
- **FR-11**: README documents which file is edited per shell, that the installer verifies the result in a fresh shell, how the opt-out line is printed, and what --uninstall removes.

## Technical Requirements

- install.sh stays POSIX sh: no bashisms, no arrays, no `local`, no `[[ ]]`, no process substitution.
- `set -eu` remains in effect at the top of the script.
- The script never reads from stdin, so `curl … | sh` keeps working.
- The marked block keeps the existing markers `# >>> forgel-code >>>` and `# <<< forgel-code <<<`, one start marker per edited file.
- The block content stays the exact `export PATH="<bin>:$PATH"` line, matching what the opt-out path prints.
- Verification must run the real login shell in a cleared environment, not a stub or a re-implementation of profile loading.
- Existing tests in tests/test_install.py must keep passing; a test is never weakened to make a change pass.
- All committed artifacts, including README.md and test names, are in English.
- Commits use the imperative mood with `git commit -s`, without tool attribution lines.

## User Stories

- As a user who installs forgel-code and opens a new terminal, I want forgel-code to be on PATH so that I can run it without editing shell files by hand.
- As a user whose $SHELL is unset or unusual, I want the installer to use my account login shell so that the PATH block lands where my shell reads it.
- As a user who edits their own profile, I want the installer to leave the rest of the file byte-identical so that my customisations are preserved.
- As a user who wants no automatic edits, I want the opt-out to print the exact export line so that I can add it myself.
- As a user uninstalling, I want the marked block removed from every candidate profile file so that no stale PATH entry remains.

## Tests

- With SHELL unset and a zsh login shell the block lands in $HOME/.zshrc and a fresh `env -i` zsh resolves forgel-code to the installed launcher.: `python -m unittest tests.test_install -v`
- With SHELL=/bin/bash and an existing ~/.bash_profile the block lands there and ~/.bashrc is neither created nor modified.: `python -m unittest tests.test_install -v`
- With SHELL=/bin/bash and no bash profile file the installer creates ~/.bash_profile with the block.: `python -m unittest tests.test_install -v`
- When the edited file is not read by the detected shell (for example FORGEL_CODE_PROFILE points at an ignored file) the installer exits non-zero and the message names that file.: `python -m unittest tests.test_install -v`
- With FORGEL_CODE_NO_MODIFY_PATH=1 no profile file in the temporary HOME is created or modified, the export line is printed, the exit code is 0.: `python -m unittest tests.test_install -v`
- Running the installer twice leaves exactly one marked block and identical content.: `python -m unittest tests.test_install -v`
- --uninstall removes the block from every candidate file holding it and leaves unrelated lines unchanged.: `python -m unittest tests.test_install -v`
- A piped `sh` install with the script on stdin still installs and verifies.: `python -m unittest tests.test_install -v`
- `sh -n install.sh` exits 0.: `sh -n install.sh`
- The full test suite passes.: `python -m unittest discover -s tests`
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: With SHELL unset and a zsh login shell the block lands in $HOME/.zshrc and a fresh `env -i` zsh resolves forgel-code to the installed launcher.
- **AC-2**: With SHELL=/bin/bash and an existing ~/.bash_profile the block lands there and ~/.bashrc is neither created nor modified.
- **AC-3**: With SHELL=/bin/bash and no bash profile file the installer creates ~/.bash_profile with the block.
- **AC-4**: When the edited file is not read by the detected shell (for example FORGEL_CODE_PROFILE points at an ignored file) the installer exits non-zero and the message names that file.
- **AC-5**: With FORGEL_CODE_NO_MODIFY_PATH=1 no profile file in the temporary HOME is created or modified, the export line is printed, the exit code is 0.
- **AC-6**: Running the installer twice leaves exactly one marked block and identical content.
- **AC-7**: --uninstall removes the block from every candidate file holding it and leaves unrelated lines unchanged.
- **AC-8**: A piped `sh` install with the script on stdin still installs and verifies.
- **AC-9**: `sh -n install.sh` exits 0.
- **AC-10**: The full test suite passes.

## Scope Boundaries

- install.sh profile-file selection: shell detection from $SHELL, then account login shell, then fallback
- install.sh profile block placement per shell (zsh, bash, other/fallback)
- install.sh creating the chosen profile file when missing
- install.sh post-write verification in a fresh login interactive shell
- install.sh failure reporting for a profile file the detected shell does not read
- install.sh idempotency of the marked block and byte-identical remainder of the file
- install.sh FORGEL_CODE_PROFILE override and FORGEL_CODE_NO_MODIFY_PATH / FORGEL_CODE_NO_PROFILE_EDIT opt-outs
- install.sh --uninstall removal of the marked block from every candidate profile file
- install.sh preserving POSIX sh, `sh -n`, `set -eu`, and never reading stdin
- tests/test_install.py coverage of the above behaviours in a temporary HOME
- README.md installation documentation of the edited file per shell, the fresh-shell verification, the opt-out line and what --uninstall removes
- Changing where the client is installed or the launcher format
- Changing FORGEL_CODE_HOME / FORGEL_CODE_BIN defaults
- Adding new installer options or environment variables beyond those already documented
- Widening the client or engine command surface
- Removing the installation prefix or the launcher outside --uninstall behaviour already present
- Changing the README one-command install path, tag pinning or the pip-install line policy enforced by tests/test_readme_install.py
- Supporting fish, csh, tcsh, PowerShell or non-POSIX shells for profile editing
- Windows support for the installer

## Risks

- macOS `dscl` and the passwd lookup cannot be exercised on a Linux CI host, so the fallback path may stay untested in the suite.
- A fresh interactive shell may read files the test does not control (system-wide profiles, /etc/zshrc, /etc/profile), making the `env -i` check flaky or environment-dependent.
- A zsh or bash executable may be missing on the QA host, so the fresh-shell verification tests would need to skip rather than fail, which weakens coverage.
- The verification message must name the edited file when the shell does not read it; if the shell silently succeeds through another PATH source the installer could report success for the wrong reason.
- The existing `tests/test_install.py` sets `SHELL=/bin/sh` and `FORGEL_CODE_PROFILE` explicitly; keeping those green while adding shell detection requires careful ordering of override and detection.
- `set -eu` plus command substitution around shell detection can abort the script on a non-zero exit unless guarded.
- README must stay within the single-install-path policy enforced by tests/test_readme_install.py, so the new documentation must not introduce an alternative installation path.

## Open Questions

- None.

## Affected Files

- install.sh
- tests/test_install.py
- README.md

## Assumptions

- The account login shell is authoritative when $SHELL is missing or unhandled, because $SHELL reflects the invoking process rather than the account.
- `dscl . -read "$HOME" UserShell` on macOS and the passwd entry elsewhere are the accepted ways to read the account login shell in a POSIX sh script.
- A minimal PATH for the fresh-shell check is enough to find basic utilities and the shell itself; the check compares only the resolved `forgel-code` path.
- The candidate profile file list for --uninstall is exactly .zshrc, .zprofile, .zshenv, .bash_profile, .bash_login and .profile.
- The existing marker lines and block layout are the format tests rely on and are kept unchanged.
- zsh and bash executables used by verification may be absent on some machines; when the detected shell binary cannot be started the installer treats verification as failed with a message naming the file.

## Related Documents

- README.md
- AGENTS.md
- FORGEL.md
- CHANGELOG.md

## Revision History

- v1 initial specification from the milestone task intent

## External Dependencies

- **macOS Directory Service command `dscl`** — mode `stub`; interface: Used only for macOS login-shell detection: `dscl . -read "$HOME" UserShell` prints `UserShell: <path>`. A test stub is placed first on PATH so macOS behavior is deterministic on Linux.; docs: `install.sh` macOS login-shell branch; `environment.yaml` / `environment/Dockerfile`; evidence: `install.sh` requires the macOS lookup `dscl . -read "$HOME" UserShell`; the repository Linux environment does not provide `dscl`, so tests need a deterministic stand-in.
  ```
  #!/bin/sh
  # Deterministic test stub for the macOS Directory Service call:
  #   dscl . -read "$HOME" UserShell
  # The shell is selected by FORGEL_STUB_USER_SHELL (default /bin/zsh).
  if [ "$#" -ne 4 ] || [ "$1" != "." ] || [ "$2" != "-read" ] || [ "$4" != "UserShell" ]; then
      printf '%s\n' 'dscl stub: supports only: dscl . -read <home> UserShell' >&2
      exit 64
  fi
  shell=${FORGEL_STUB_USER_SHELL:-/bin/zsh}
  printf 'UserShell: %s\n' "$shell"
  ```
- **passwd database (getent / /etc/passwd)** — mode `direct`; interface: Fallback login-shell lookup: `getent passwd "$(id -u)" | cut -d: -f7`, with an `/etc/passwd` fallback such as `awk -F: -v u="$(id -u)" '$3 == u { print $7 }' /etc/passwd`. Tests may inject a fake `getent` first on PATH for controlled output.; docs: `environment/Dockerfile`; Linux passwd database at `/etc/passwd`; evidence: The environment is a Linux base with the account database available locally; `install.sh` uses the account login shell when `$SHELL` is unset, empty or unhandled.
- **zsh** — mode `direct`; interface: Verification shell: `env -i HOME="$HOME" SHELL=/bin/zsh TERM=dumb PATH="/usr/bin:/bin" /bin/zsh -l -i -c 'command -v forgel-code'`. Profile writes target `$HOME/.zshrc` for zsh.; docs: `environment/Dockerfile`; install verification tests; evidence: The environment contract provides zsh, and the required fresh-shell test invokes zsh as a login interactive shell under `env -i` to resolve `forgel-code` from the written `.zshrc`.
- **bash** — mode `direct`; interface: Verification shell: `env -i HOME="$HOME" SHELL=/bin/bash TERM=dumb PATH="/usr/bin:/bin" /bin/bash -l -i -c 'command -v forgel-code'`. Login profile writes target the first existing of `$HOME/.bash_profile`, `$HOME/.bash_login`, `$HOME/.profile`, creating `.bash_profile` when none exists.; docs: `environment/Dockerfile`; install verification tests; evidence: Bash is provided by the environment and is required by the fresh-shell verification and login-profile behavior described in the task.


## Summary

Reworked install.sh so the PATH block lands in the profile the login shell actually reads and is proven active in a fresh shell; documented the behaviour in README.md and covered it in tests/test_install.py. install.sh now: (1) keeps the FORGEL_CODE_PROFILE override first; (2) detects the login shell from $SHELL only when that names a shell the installer handles, otherwise from the account login shell (dscl . -read "$HOME" UserShell, then getent passwd / /etc/passwd), falling back to /bin/sh; (3) picks ~/.zshrc for zsh, the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile for bash (creating ~/.bash_profile) and never ~/.bashrc alone, ~/.profile otherwise, creating the file when missing; (4) writes the single marked block with the unchanged markers and the exact export PATH="<bin>:$PATH" line; (5) verifies by starting the detected shell with env -i (HOME, SHELL, TERM, PATH=/usr/bin:/bin) as `-l -i` and requiring `command -v forgel-code` to equal the launcher just written; on failure it exits non-zero and prints the login shell, the edited profile file, the block written, the fresh PATH and the resolved path; on success it prints the detected shell, the profile file and the fresh-shell result; (6) --uninstall removes the marked block from .zshrc, .zprofile, .zshenv, .bash_profile, .bash_login and .profile plus the prefix and launcher, leaving the rest of each file unchanged. The opt-out variables still leave every profile untouched, print the exact export line and exit 0, and a piped `sh` install still works (the script never reads stdin). README now documents the per-shell profile table, the account-login-shell fallback, the fresh-shell verification and its failure report, the exact opt-out line and what --uninstall removes. Added tests: shell detection from the account login shell through the recorded dscl stub with a fresh `env -i` zsh resolving the launcher, bash profile placement with and without an existing ~/.bash_profile (and no ~/.bashrc), installer reporting of shell/profile/fresh-check, non-zero exit naming the edited file when the shell ignores it, and --uninstall clearing the block from every candidate file. Verified with `python -m unittest tests.test_install -v` (23 tests OK), `python -m unittest tests.test_readme_install -v` (26 tests OK, including the `sh -n install.sh` guard) and the full suite `python -m unittest discover -s tests` (171 tests OK).

## Files Changed

- `README.md`
- `install.sh`
- `tests/test_diag_tmp.py`
- `tests/test_install.py`

## Commands

- `["python", "-m", "unittest", "tests.test_install.InstallerTest.test_profile_gets_one_marked_path_block", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install", "-v"]` → exit 1
- `["python", "-m", "unittest", "tests.test_install.InstallerShellDetectionTest.test_unset_shell_puts_the_block_in_zshrc", "-v"]` → exit 1
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 1
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_diag_tmp", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_readme_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
...........................................................................................................................................................................
----------------------------------------------------------------------
Ran 171 tests in 75.170s

OK

```

## Actions

- read_file: install.sh
- read_file: tests/test_install.py
- read_file: README.md
- read_file: tests/test_readme_install.py
- read_file: CHANGELOG.md
- read_file: AGENTS.md
- list_files
- write_file: install.sh
- run: ['sh', '-c', 'ls -l /bin/sh; for s in zsh bash dash; do command -v $s || echo "no $s"; done']
- run: ['sh', '-n', 'install.sh']
- write_file: install.sh
- write_file: install.sh
- run: ['python', '-m', 'unittest', 'tests.test_install.InstallerTest.test_profile_gets_one_marked_path_block', '-v']
- run: ['python', '-m', 'unittest', 'tests.test_install', '-v']
- run: ['python', '-m', 'unittest', 'tests.test_install', '-v']
- write_file: install.sh
- run: ['python', '-m', 'unittest', 'tests.test_install', '-v']
- read_file: tests/test_install.py
- write_file: tests/test_install.py
- run: ['python', '-m', 'unittest', 'tests.test_install', '-v']
- write_file: tests/test_install.py
- run: ['python', '-m', 'unittest', 'tests.test_install.InstallerShellDetectionTest.test_unset_shell_puts_the_block_in_zshrc', '-v']
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- delete_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- read_file: tests/test_install.py
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- read_file: tests/test_install.py
- delete_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- write_file: tests/test_diag_tmp.py
- run: ['python', '-m', 'unittest', 'tests.test_diag_tmp', '-v']
- delete_file: tests/test_diag_tmp.py
- write_file: tests/test_install.py
- run: ['python', '-m', 'unittest', 'tests.test_install', '-v']
- write_file: README.md
- run: ['python', '-m', 'unittest', 'tests.test_readme_install', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- list_files
- read_file: install.sh
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
