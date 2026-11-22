# Task Review: Fix install.sh so a new terminal finds forgel-code on PATH

- Task: `20261122025705_fix-install-sh-so-a-new-terminal-finds-f`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-22T03:41:44+00:00

## Summary

The attributed change implements the specification in install.sh: profile selection now goes through a detected login shell ($SHELL first when handled, then the account login shell from dscl/getent/passwd, then /bin/sh), zsh writes to ~/.zshrc, bash writes to the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile and creates ~/.bash_profile when none exists, ~/.bashrc is no longer used, the override and both opt-outs keep working (printing the exact `export PATH="<bin>:$PATH"` line and exiting 0), and after writing the block the installer starts the detected shell as `env -i ... -l -i -c` and only reports success when `command -v forgel-code` resolves to the launcher it just wrote; a failed check prints the login shell, profile file, block and the PATH the fresh shell saw and exits non-zero. --uninstall now strips the marked block from the six candidate profile files while leaving the rest untouched, re-runs stay idempotent, the script remains POSIX sh with `set -eu` and never reads stdin (the fresh shell is given </dev/null), and README documents the per-shell file, the fresh-shell verification, the opt-out line and what uninstall removes without adding a second install path. The dscl stub in tests matches the recorded external-dependency evidence exactly, and passwd/zsh/bash are used as direct interfaces. The attributed file tests/test_diag_tmp.py is not present in the current tree and no test removals were detected, so nothing is missing there. QA's gate (full suite, sh -n, the fresh-shell acceptance case, environment checks) passed, and I found no requirement violation, no unrequested feature, no weakened test, and no security issue in the attributed diff.

## Requirements

- FR-1: profile selection does not rely on $SHELL alone; an unusable $SHELL falls back to the account login shell (macOS dscl, otherwise passwd) and only then to ~/.profile: pass — detect_login_shell uses $SHELL when handled, then account_login_shell (dscl, getent, /etc/passwd awk), then /bin/sh whose family maps to ~/.profile.
- FR-2: for zsh the block goes into $HOME/.zshrc, created when missing: pass — profile_path zsh branch prints $HOME_DIR/.zshrc and add_profile_block creates the file.
- FR-3: for bash the block goes into the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile, creating ~/.bash_profile when none exists, never into ~/.bashrc alone: pass — bash branch loops over the three names in order and defaults to ~/.bash_profile; .bashrc no longer appears in profile_path.
- FR-4: FORGEL_CODE_PROFILE overrides the chosen file; FORGEL_CODE_NO_MODIFY_PATH and FORGEL_CODE_NO_PROFILE_EDIT leave every profile untouched, print the exact export line and exit 0: pass — profile_path returns the override first; add_path's opt-out branch prints `export PATH="<bin>:$PATH"` and returns 0 before any detection or write.
- FR-5: after writing, the installer starts the detected login shell as a login interactive shell in a cleared environment and requires command -v forgel-code to resolve to the launcher just written: pass — verify_profile runs `env -i HOME=... SHELL=... TERM=dumb PATH=/usr/bin:/bin $shell -l -i -c ...` and compares the resolved path to $LAUNCHER; no stub or re-implementation of profile loading.
- FR-6: a failed verification exits non-zero and prints the edited profile file, the block written and the PATH seen in the fresh shell, and does not claim the change is active: pass — verification_failure prints the shell, profile file, the marker block, the fresh PATH and the resolved path, returns 1, and add_path propagates failure so the success message is never emitted.
- FR-7: on success the installer prints the detected shell, the profile file written and the fresh-shell check result: pass — The success branch prints login shell, profile path and `command -v forgel-code -> $VERIFIED_PATH`.
- FR-8: re-running keeps exactly one marked block per edited file and leaves the rest of the file byte-identical: pass — add_profile_block removes any existing block before appending, and the trailing-newline guard is stable across runs, so the remainder is unchanged and one block remains.
- FR-9: --uninstall removes the block from every candidate file (.zshrc, .zprofile, .zshenv, .bash_profile, .bash_login, .profile), leaves the rest unchanged, and still removes the prefix and launcher: pass — The uninstall loop iterates PROFILE_NAMES and calls remove_profile_block, which uses awk to drop only the marked block; prefix and launcher removal is unchanged.
- FR-10: the curl | sh shape keeps working: POSIX sh, sh -n clean, set -eu, never reads stdin: pass — `set -eu` remains at the top, no bashisms, and the fresh shell is started with `</dev/null` so it cannot consume the piped script; QA's `sh -n install.sh` and piped-install checks passed.
- FR-11: README documents the file per shell, the fresh-shell verification, the printed opt-out line and what --uninstall removes: pass — README adds the per-shell table, detection/verification paragraphs, the printed export line and the uninstall candidate list.
- Technical: markers and block content unchanged, block is the exact export line matching the opt-out output: pass — MARKER_START/MARKER_END are byte-identical to before and both write and opt-out paths use the same printf of `export PATH="$BIN_DIR:$PATH"`.
- Technical: existing tests keep passing and no test is weakened; no unjustified test removal: pass — No test removals were detected; the suite gained constants (CANDIDATE_PROFILES, DSCL_STUB) and the full suite plus the acceptance cases pass under QA.
- External dependencies: dscl stub matches the recorded evidence; passwd, zsh and bash used as direct interfaces: pass — DSCL_STUB reproduces the recorded stub verbatim (4-arg check, FORGEL_STUB_USER_SHELL, `UserShell: %s`); the installer reads passwd via getent/awk and starts the real zsh/bash binaries.
- Non-goals respected: no change to install location, launcher format, FORGEL_CODE_HOME/BIN defaults, options, README install path, tag pinning or the test_readme_install policy: pass — Only profile selection, verification, uninstall cleanup and their documentation changed; the pip invoke call was reflowed, not altered, and the README one-command block remains first and unchanged.
- AC-1..AC-10 acceptance checks: pass — QA reported pass for the fresh-shell zsh case, `sh -n install.sh`, the full test suite and both environment checks; no failing acceptance check was recorded.
- Committed artifacts are English and the commit uses the imperative mood with git commit -s: pass — README and test names are English; the commit message is imperative and carries a Signed-off-by line, without a tool name attribution line.

## Blocking

- none

## Test Removals

- none


