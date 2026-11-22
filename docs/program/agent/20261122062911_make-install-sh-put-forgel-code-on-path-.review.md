# Task Review: Make install.sh put forgel-code on PATH for a new terminal

- Task: `20261122062911_make-install-sh-put-forgel-code-on-path-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-22T07:33:31+00:00

## Summary

The attributed change implements the specification faithfully. install.sh now resolves the login shell in the required order ($SHELL, then the invoking process via ps, then the account login shell via dscl/getent/passwd, then /bin/sh), selects the profile an interactive login session of that shell actually reads (zsh → ~/.zshrc, bash → first existing of ~/.bash_profile/~/.bash_login/~/.profile or a created ~/.bash_profile, POSIX family → ~/.profile with a stderr warning naming shell and file), writes a byte-delimited block whose body is a POSIX `case ":$PATH:"` guard instead of an unguarded export, verifies the result in a cleared login interactive shell under a portable background-watchdog bound that needs no GNU timeout and maps a kill to exit status 124, and reports failures with the edited file, the exact block, the checked shell and the PATH that shell saw. Uninstall covers every writable profile plus FORGEL_CODE_PROFILE without creating or altering other lines, the opt-out path still prints the plain export line and skips verification, and the script stays POSIX sh with stdin redirected to /dev/null on every child. README.md matches the new behaviour (guarded block, unrecognised-shell warning, bounded verification and its failure report, the full uninstall profile list) without adding a step the installer no longer needs. The recorded dscl stub in tests/test_install.py answers the exact invocation the installer makes (`dscl . -read <home> UserShell` → `UserShell: <path>`), so it does not contradict the recorded dependency. No test removals were detected and the full suite plus the dash parse check pass. Two non-blocking observations: the watchdog uses a predictable name under ${TMPDIR:-/tmp} that is truncated with `: >`, a low-severity local symlink race, and tests/_timing_probe.py was committed and then dropped inside this task's history, so it is absent from the final tree and leaves no stale test behind.

## Requirements

- FR-1: shell resolution order ($SHELL, parent process via ps, account login shell via dscl/getent//etc/passwd, /bin/sh) with no bash assumption on an empty $SHELL: pass — detect_login_shell tries a handled $SHELL, then parent_login_shell (ps -p $PPID -o comm= with basename and leading-dash normalisation, re-resolved with command -v), then account_login_shell (dscl, then getent passwd <uid>, then /etc/passwd field 7), and only then prints /bin/sh.
- FR-2/FR-3: zsh writes to ~/.zshrc (created); bash writes to the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile, else creates ~/.bash_profile; never ~/.bashrc alone: pass — profile_path implements exactly that order and creation; .bashrc only appears in the uninstall list.
- FR-4: unrecognised/POSIX shell writes to ~/.profile and prints a stderr warning naming the edited file and the detected shell: pass — add_path emits "warning: $DETECTED_SHELL is neither zsh nor bash; the PATH block is in $profile" for the posix family, including the /bin/sh fallback, while the exit status still depends on verification.
- FR-5: FORGEL_CODE_PROFILE replaces the selected profile for install and uninstall: pass — profile_path returns it first; the uninstall path also cleans the exact file (documented in README).
- FR-6: block delimited by the exact markers and body is a POSIX `case "$PATH:"` guard, no unguarded export: pass — print_block writes the markers, the guarded case, `esac` and `export PATH`; the old bare export line is gone from both the writer and the failure report.
- FR-7/FR-14: sourcing several blocks or installing twice leaves one occurrence of the launcher directory: pass — The guard tests the directory before prepending, and add_profile_block removes the previous block before appending, so re-running keeps exactly one block.
- FR-8/FR-9/FR-10/FR-11: bounded verification in a cleared login interactive shell, portable watchdog without GNU timeout, defined failure report with non-zero exit, success report: pass — bounded_run starts the shell via `env -i HOME=... SHELL=... TERM=dumb PATH=/usr/bin:/bin <shell> -l -i -c ... </dev/null` in the background with a sleeper-based watcher that kills it at the internal 5s bound and marks status 124; verification_failure prints profile, exact block, shell, fresh PATH and the resolved path, and the success path prints shell, profile and resolved path. No `timeout` binary is required.
- FR-12: opt-out skips the profile write and verification, prints the exact export PATH line, exits zero: pass — no_profile_edit still covers both variable names and the opt-out branch is unchanged in the install flow; README documents that no fresh-shell check runs in that case.
- FR-13: --uninstall strips the block from ~/.zshrc, ~/.zprofile, ~/.zshenv, ~/.bash_profile, ~/.bash_login, ~/.profile, ~/.bashrc and FORGEL_CODE_PROFILE, creating no file and touching no other line: pass — PROFILE_NAMES now lists all seven names; remove_profile_block returns early for a missing file or missing marker, copies to a sibling temp, rewrites with awk line-exact marker matching and moves back.
- FR-15/Technical: POSIX sh, no bashisms, never reads stdin so `curl ... | sh` and `sh -s` work: pass — `sh -n install.sh` passes; the only arithmetic is the POSIX `$((...))` in the watchdog, no arrays/local/[[ ]], and every child is started with `< /dev/null`.
- FR-16: existing behaviour preserved (local checkout install, FORGEL_CODE_HOME/BIN, no virtualenv, --version, opt-out variables): pass — install_client, launcher creation and the option parsing are untouched by the diff apart from the comment and the verification call.
- FR-17: tests/test_install.py gains the named cases (zsh without $SHELL, bash with/without ~/.bash_profile, unknown shell, guard, failed verification, repeated install, uninstall, piped install): pass — QA ran each -k expression in the spec to exit 0 and the node list shows the corresponding test classes; the zsh/bash cases are gated on those binaries as the spec allows.
- FR-18: no existing test deleted or weakened; exact-block assertions updated to the guarded block (review-only): pass — Removal detection reports none, the suite passes, and the diff shows the block text updated in the writer and the failure report together with the tests' expectations rather than an assertion being dropped.
- FR-19/AC-8: README Install, Options, Update and Uninstall match the implemented behaviour (review-only): pass — README documents the shell resolution chain with the ps step, the warning for an unrecognised shell, the guarded block, the bounded verification with its failure report, and the full seven-file uninstall list plus FORGEL_CODE_PROFILE; no obsolete manual step remains, and tests/test_readme_install.py still passes.
- External dependencies: POSIX sh, zsh, bash, ps and getent used directly; dscl used through the recorded stub contract: pass — The installer invokes exactly the recorded interfaces; the dscl stub in tests/test_install.py answers `dscl . -read <home> UserShell` with `UserShell: <path>` from FORGEL_STUB_USER_SHELL, matching the evidence for every call the installer makes.

## Blocking

- none

## Test Removals

- none


