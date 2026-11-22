# Task Spec: Make install.sh put forgel-code on PATH for a new terminal

## Document Information

| Field | Value |
|-------|-------|
| Feature | Make install.sh put forgel-code on PATH for a new terminal |
| Project | — |
| Task | `20261122062911_make-install-sh-put-forgel-code-on-path-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T06:30:35+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

install.sh writes a PATH block into a shell profile but the block is a bare `export PATH=...`, the post-write check has no time bound and no defined failure report, a shell the installer does not recognise silently falls through to a POSIX family without telling the user which file was edited, and $SHELL resolution has no parent-process fallback for piped runs. A user whose login shell is zsh or macOS bash can end up with a block in a file their terminal never reads, or with no clear diagnosis at all, so `forgel-code` is not on PATH in a new terminal.

**Outcome:** install.sh resolves the login shell without assuming bash, edits the profile file that an interactive login session of that shell actually reads, writes a duplicate-safe marked block, verifies the result in a cleanly started login shell under a bounded timeout, and on failure exits non-zero with the edited file, the written block, the shell checked and the PATH that shell sees. --uninstall removes the marked block from every file the installer can write without touching other lines. tests/test_install.py and README.md describe and prove exactly this behaviour, and the full suite passes.

## Product Intent

Forgel Code is a Python client installed as `forgel-code` from one command (D-004). Installation must end with a working `forgel-code` command in the user's next terminal and no manual PATH edit, or with an honest failure.

## User Experience

The user pastes the one-line `curl ... | sh` command, opens a new terminal, and `forgel-code` runs. There is no activation step, no virtualenv and no hand-edited profile. If the installer cannot make the command resolvable it says so, names the file it edited, shows the exact block and the PATH the fresh shell saw, and exits non-zero instead of claiming success. Running the same command again or `--uninstall` leaves the profile files with exactly one block, or none.

## Roadmap

—

## Goals

- A new terminal of the user's login shell resolves `forgel-code` after one successful install, with no manual PATH edit.
- The block lives in a file the detected login shell actually reads, for zsh, bash and an unrecognised shell.
- Sourcing the block more than once leaves exactly one occurrence of the launcher directory in PATH.
- A failed verification is visible: non-zero exit plus the edited file, the block, the shell checked and its PATH.
- --uninstall leaves every profile file the installer can write without the marked block and without any other change.
- The test suite and the README describe and prove the same behaviour.

## Non-Goals

- Changing client code under forgel_code/ or the build backend
- New user-facing environment variables or CLI flags beyond the ones already documented (FORGEL_CODE_HOME, FORGEL_CODE_BIN, FORGEL_CODE_SOURCE, FORGEL_CODE_TAG, FORGEL_CODE_REPOSITORY, FORGEL_CODE_PYTHON, FORGEL_CODE_PROFILE, FORGEL_CODE_NO_MODIFY_PATH, FORGEL_CODE_NO_PROFILE_EDIT)
- Support for non-POSIX shells such as fish, csh or nushell as the login shell
- Editing system-wide files (/etc/profile, /etc/profile.d, /etc/zshrc) or requiring sudo
- Windows or PowerShell profile handling beyond the existing README fallback note
- Version bump, tag, release note or CHANGELOG release entry
- Replacing the installer with a packaging-based install path

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code, installed as `forgel-code`, a Python client that imports nothing from the engine. | User decision log D-004, accepted proposal 2026-11-16 18:34 |
| — | The client is a thin UI over the engine's parameterized commands and does not call the model, read project files or run checks itself. | User decision log D-002, 2026-11-16 18:31 |
| — | The client repository is public and lives in the same organization as the engine (`forgel-dev`), which is where the installer's raw.githubusercontent.com URL points. | User decision log D-005, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: Shell resolution never assumes bash. The detected login shell is, in order: $SHELL when it names a shell the installer handles (zsh, bash, sh, dash, ksh, ksh93, mksh, pdksh, ash, yash); otherwise the shell of the invoking process ancestry (the parent process, read with ps) when that names a handled shell; otherwise the account login shell (macOS `dscl . -read "$HOME" UserShell` first, then `getent passwd <uid>` or the /etc/passwd entry); otherwise /bin/sh. An empty or unset $SHELL must never by itself produce a bash decision.
- **FR-2**: When the detected shell is zsh, the block is written to ~/.zshrc, created when it does not exist.
- **FR-3**: When the detected shell is bash, the block is written to a file an interactive login bash reads: ~/.bash_profile when it exists; otherwise the first existing of ~/.bash_login and ~/.profile; when none of the three exists, ~/.bash_profile is created. The block is never written to ~/.bashrc alone.
- **FR-4**: When the detected shell is not zsh and not bash (the POSIX family, including the /bin/sh fallback and a shell the installer does not recognise), the block is written to ~/.profile and the installer prints a warning on stderr that names the edited file and the detected shell.
- **FR-5**: FORGEL_CODE_PROFILE, when set, replaces the selected profile file for both install and uninstall.
- **FR-6**: The written block is delimited by the marker lines `# >>> forgel-code >>>` and `# <<< forgel-code <<<`, compared byte for byte, and its body is a POSIX `case "$PATH:" in` guard that prepends the launcher directory to PATH only when that directory is not already present. No unguarded `export PATH=...` line is written.
- **FR-7**: Sourcing several profile files that each carry the block leaves exactly one occurrence of the launcher directory in PATH.
- **FR-8**: Unless the profile edit is opted out, after writing the block the installer starts the detected shell as a login shell from a cleared environment (`env -i` carrying only HOME, SHELL, TERM=dumb and PATH=/usr/bin:/bin, stdin from /dev/null), under a bounded time limit, and requires `command -v forgel-code` in that shell to resolve to the launcher path the installer wrote.
- **FR-9**: The bounded time limit must work on a host without GNU coreutils, so it cannot depend on the `timeout` binary alone; a portable watchdog that kills the shell and treats the result as a verification failure is required.
- **FR-10**: On verification failure the installer exits non-zero and prints, on stderr, the edited profile file, the exact block it wrote, the shell it checked and the PATH that shell reported.
- **FR-11**: On verification success the installer exits zero and prints the detected shell, the edited profile file and the path the fresh shell resolved.
- **FR-12**: When FORGEL_CODE_NO_MODIFY_PATH or FORGEL_CODE_NO_PROFILE_EDIT is set to an opt-out value, no profile file is opened for writing, no verification runs, the exact `export PATH="<bin dir>:$PATH"` line is printed and the installer exits zero.
- **FR-13**: --uninstall removes the marked block from every profile file the installer can write — ~/.zshrc, ~/.zprofile, ~/.zshenv, ~/.bash_profile, ~/.bash_login, ~/.profile, ~/.bashrc — and from FORGEL_CODE_PROFILE when it is set. It changes no other line of those files, creates no missing file, and exits zero when a file is absent or carries no marker.
- **FR-14**: Running the installer twice leaves exactly one marked block in the selected profile file and exactly one occurrence of the launcher directory in PATH.
- **FR-15**: The script stays POSIX sh: `sh -n install.sh` succeeds under dash, and the script never reads stdin, so `curl ... | sh` and `sh < install.sh` work.
- **FR-16**: Existing behaviour is preserved: installation from a local checkout with FORGEL_CODE_SOURCE and without network, installation into FORGEL_CODE_HOME and the launcher into FORGEL_CODE_BIN, no virtualenv, `forgel-code --version` printing `forgel-code <version>`, and the opt-out variables.
- **FR-17**: tests/test_install.py gains passing cases named (or selected by a -k expression matching) zsh without $SHELL, bash with an existing ~/.bash_profile, bash with a missing ~/.bash_profile, unknown shell, the duplicate-safe guard when several profiles are sourced, failing verification, repeated install, --uninstall cleanup, and installation through a shell reading install.sh from stdin.
- **FR-18**: No existing test in tests/ is deleted or loosened; tests that assert the exact block text are updated to the guarded block.
- **FR-19**: README.md's Install, Options, Update and Uninstall text matches the resulting behaviour (guarded block, warning for an unrecognised shell, the verification and its failure report, the profile list) and names no step the installer no longer requires; tests/test_readme_install.py still passes.

## Technical Requirements

- POSIX sh only: no bashisms, no arrays, no `local`, no `[[ ]]`; `sh -n install.sh` must pass under dash.
- The installer never reads stdin, so `curl ... | sh` and `sh -s` remain valid.
- The profile write must be atomic enough to survive a crash: write to a temporary file next to the target and move it into place, or append only after the previous block is removed.
- Bounded verification must not require GNU coreutils on macOS.
- Installer tests run offline in a temporary HOME against the real install.sh, never against the developer's real profile files.
- Artifacts, comments, test names and the README stay in English.
- Commit in imperative mood with `git commit -s`, no tool attribution.
- Do not weaken or delete an existing test to make a change pass.

## User Stories

- As a new user on zsh, I want the one-line installer to put forgel-code on PATH so that my next terminal just works without editing a profile.
- As a macOS user whose login shell is bash, I want the block in a file login bash reads so that `forgel-code` is found and my startup files keep working.
- As a user whose login shell the installer does not recognise, I want to be told which file it edited so that I can check or remove the change.
- As a user whose shell never reads the edited profile, I want the installer to fail loudly with the file, the block and the PATH so that I can fix it instead of wondering why the command is missing.
- As a maintainer, I want --uninstall to leave my profile files exactly as they were so that removing the client is safe.
- As a maintainer, I want the tests and README to describe the same profile and verification behaviour so that a change to one is caught by the other.

## Tests

- After a successful install a login shell of the detected shell, started from a cleared environment, resolves forgel-code to the installed launcher without any manual PATH edit.: `python -m pytest -q tests/test_install.py -k login_shell_resolves`
- An install that cannot make forgel-code resolvable exits non-zero and prints the edited file, the written block, the shell checked and the PATH that shell sees.: `python -m pytest -q tests/test_install.py -k failed_verification`
- Running the installer twice leaves exactly one marked block and exactly one occurrence of the launcher directory in PATH.: `python -m pytest -q tests/test_install.py -k repeated_install`
- Sourcing several profile files that carry the block yields exactly one occurrence of the launcher directory in PATH.: `python -m pytest -q tests/test_install.py -k guard`
- --uninstall removes the marked block from every profile file the installer can have written, keeps every unrelated line byte-identical and creates no file.: `python -m pytest -q tests/test_install.py -k uninstall`
- A zsh login shell with $SHELL unset receives the block in ~/.zshrc; a bash login shell with an existing ~/.bash_profile receives it there; a bash login shell with no bash startup file gets ~/.bash_profile created; an unrecognised shell receives it in ~/.profile with a warning naming that file.: `python -m pytest -q tests/test_install.py -k zsh or bash_profile or unknown_shell`
- tests/test_install.py passes with the new cases, and the full repository test suite passes with no existing installer test weakened.: `python -m pytest -q tests/test_install.py`
- The full repository test suite passes.: `python -m pytest -q`
- Installation through a shell reading install.sh from stdin still works and the script never consumes stdin.: `python -m pytest -q tests/test_install.py -k piped or stdin`
- The script is POSIX sh and parses under dash.: `sh -n install.sh`
- No existing installer test was weakened or deleted, only adapted to the guarded block and the new stderr warning.: review
- README.md describes the behaviour the installer now implements and no step the installer no longer needs.: review
- The README install-section guards still hold (one install command, no alternative main path, one update and one uninstall line).: `python -m pytest -q tests/test_readme_install.py`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: After a successful install a login shell of the detected shell, started from a cleared environment, resolves forgel-code to the installed launcher without any manual PATH edit.
- **AC-2**: An install that cannot make forgel-code resolvable in that shell exits non-zero and prints the edited file, the written block, the shell checked and the PATH that shell sees.
- **AC-3**: Running the installer twice leaves exactly one marked block in the selected profile file and exactly one occurrence of the launcher directory in PATH.
- **AC-4**: Sourcing several profile files that carry the block yields exactly one occurrence of the launcher directory in PATH.
- **AC-5**: --uninstall removes the marked block from every profile file the installer can have written, keeps every unrelated line byte-identical and creates no file.
- **AC-6**: A zsh login shell with $SHELL unset receives the block in ~/.zshrc; a bash login shell with an existing ~/.bash_profile receives it there; a bash login shell with no bash startup file gets ~/.bash_profile created; an unrecognised shell receives it in ~/.profile with a warning naming that file.
- **AC-7**: tests/test_install.py passes with the new cases, and the full repository test suite passes with no existing installer test weakened.
- **AC-8**: README.md describes the behaviour the installer now implements and no step the installer no longer needs.

## Scope Boundaries

- install.sh: login-shell resolution and profile-file selection
- install.sh: the marked PATH block and its duplicate guard
- install.sh: post-write verification in a clean login shell with a bounded timeout and a defined failure report
- install.sh: --uninstall cleanup of the marked block across all writable profile files
- tests/test_install.py: new cases proving each of the above
- README.md: installation, options and uninstall text aligned with the resulting behaviour
- Changing client code under forgel_code/ or the build backend
- New user-facing environment variables or CLI flags beyond the ones already documented (FORGEL_CODE_HOME, FORGEL_CODE_BIN, FORGEL_CODE_SOURCE, FORGEL_CODE_TAG, FORGEL_CODE_REPOSITORY, FORGEL_CODE_PYTHON, FORGEL_CODE_PROFILE, FORGEL_CODE_NO_MODIFY_PATH, FORGEL_CODE_NO_PROFILE_EDIT)
- Support for non-POSIX shells such as fish, csh or nushell as the login shell
- Editing system-wide files (/etc/profile, /etc/profile.d, /etc/zshrc) or requiring sudo
- Windows or PowerShell profile handling beyond the existing README fallback note
- Version bump, tag, release note or CHANGELOG release entry
- Replacing the installer with a packaging-based install path

## Risks

- The intent asks for a non-interactive login shell for verification while also requiring the block in ~/.zshrc; a non-interactive login zsh does not read ~/.zshrc, so a strictly `-l -c` check would fail every zsh install. This spec uses the mode a new terminal uses (login, interactive for zsh); a planner decision is recorded as an open question.
- A portable bounded wait in POSIX sh without coreutils is easy to get wrong; a watchdog that leaks a background process or returns success after a kill would make the failure-report criterion untestable.
- Creating ~/.bash_profile when it is absent changes what login bash reads and can shadow an existing ~/.bash_login; this spec avoids the shadowing case but the coder must keep that branch correct.
- A new stderr warning for unrecognised shells can break existing assertions that expect empty stderr; such assertions must be updated to the new contract, not deleted.
- The zsh and bash test cases need those binaries on the test host and in CI; on a host without them the cases would be skipped, leaving the criterion unproved for that run.
- tests/test_install.py defines the exact block text in its `_marked_block` helper; the guarded block changes that text, so the helper and any exact-text assertions must change together with install.sh.
- I could read install.sh only through line 302 of 484 with the repository tool, so the existing verify/uninstall/main functions were not inspected; parts of this task may already be implemented and the coder must confirm each requirement rather than rewrite blindly.
- tests/test_readme_install.py enforces a strict README shape (single install command, no alternative main path, one update and one uninstall line); new wording must keep those guards green.
- The guard only prevents the installer's own duplicate when several of its blocks are sourced; a PATH entry the user added by hand elsewhere is untouched and could still duplicate.
- No decision in the user decision log covers shell-profile behaviour, so the recorded intent is the only binding source for the profile and verification rules.

## Open Questions

- The recorded intent says the post-write check runs the login shell as a clean non-interactive login shell, while zsh users need the block in ~/.zshrc, which only an interactive zsh reads. Confirm that the check may run the shell in the mode a new terminal uses (login plus interactive for zsh), or that zsh users must instead get the block in ~/.zprofile.

## Affected Files

- install.sh
- tests/test_install.py
- README.md
- tests/test_readme_install.py (only if a new README guard is needed for the warning or the guarded block)

## Assumptions

- 'The shell of the parent/login process' is read as two sources: the parent process ancestry (via ps) and the account login shell; both are consulted between $SHELL and the /bin/sh fallback, because a piped run inside a container often has no useful $SHELL but a meaningful parent shell.
- For bash the intent's 'macOS uses ~/.bash_profile' is reconciled with an existing ~/.bash_login or ~/.profile: an existing login startup file is edited rather than shadowed by a freshly created ~/.bash_profile, since creating an empty ~/.bash_profile would silently stop bash from reading the user's existing ~/.bash_login. Creating ~/.bash_profile happens only when none of the three exists.
- The verification shell is a login shell in the mode a new terminal uses; for a block in an interactive-only file such as ~/.zshrc that means interactive as well, because a non-interactive login zsh does not read ~/.zshrc.
- An unrecognised shell means a shell outside the zsh and bash families, including the /bin/sh fallback; the warning is emitted in that case even though the exit status stays zero when verification passes.
- The time bound for verification is an internal constant, not a new documented environment variable.
- The unit of change is one commit; the coder may further split tests by class as long as the named cases exist and are selectable by the -k expressions in the checks.
- Running the suite requires /bin/sh; the zsh and bash cases are gated on those binaries being present on the test host.

## Related Documents

- README.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md
- pyproject.toml
- releases/0.1.0/plan.md

## Revision History

- v1: initial specification for making install.sh put forgel-code on PATH for a new terminal.

## External Dependencies

- **POSIX sh (dash, ash, ksh)** — mode `direct`; interface: install.sh is executed as a POSIX sh script: `sh install.sh` (including the `curl ... | sh` path) and `sh install.sh --uninstall`; the script must stay POSIX-compatible (no bashisms) and is exercised by the suite through the system /bin/sh.; docs: POSIX.1 Shell Command Language; sh(1), dash(1); evidence: Repository instruction files (FORGEL.md/AGENTS.md) define the repository as a plain POSIX shell installer project; the specification's dependency entry records the installer is a POSIX sh script whose login session reads ~/.profile; the system provides /bin/sh as a local executable.
- **zsh** — mode `direct`; interface: Verification shell: `zsh -l -i -c '<command>'`; the interactive flag is required so that ~/.zshrc is sourced in the login session, which is where the installer writes the PATH block. Used by tests for the "zsh without $SHELL" case.; docs: zsh(1), section STARTUP/SHUTDOWN FILES; evidence: Specification dependency entry: zsh started as `zsh -l -i -c '<command>'`; an interactive login zsh reads /etc/zshenv, ~/.zshenv, /etc/zprofile, ~/.zprofile, /etc/zshrc, ~/.zshrc in that order. The suite must cover a zsh login shell, so zsh is a locally installed executable used directly by tests.
- **bash** — mode `direct`; interface: Verification shell: `bash -l -i -c '<command>'`; login bash reads /etc/profile then the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile, so the installer writes ~/.bash_profile on macOS. Used by tests for bash with an existing and a missing ~/.bash_profile.; docs: bash(1), section INVOCATION; evidence: Specification dependency entry: bash started as `bash -l -i -c '<command>'`; login bash reads /etc/profile then the first existing of ~/.bash_profile, ~/.bash_login, ~/.profile, while ~/.bashrc is read by non-login interactive shells. bash is a locally installed executable used directly by tests.
- **macOS Directory Service `dscl`** — mode `stub`; interface: On macOS the real `dscl . -read "$HOME" UserShell` prints `UserShell: <path>` and the installer parses the path. It is not present on Linux CI, so the suite substitutes a deterministic stub selected through FORGEL_STUB_USER_SHELL (tests/test_install.py DSCL_STUB contract); the installer code path is unchanged, only the executable is replaced by the stub on PATH.; docs: dscl(1); stub contract recorded in tests/test_install.py (DSCL_STUB); evidence: Specification dependency entry: 'dscl . -read "$HOME" UserShell' prints 'UserShell: <path>'; the rest of the suite may stub it through FORGEL_STUB_USER_SHELL as tests/test_install.py already records (DSCL_STUB). dscl exists only on macOS and is therefore not callable directly in this environment.
  ```
  #!/bin/sh
  # Deterministic dscl stub (DSCL_STUB contract).
  # Emulates: dscl . -read "$HOME" UserShell  ->  "UserShell: <path>"
  # The login shell is supplied by FORGEL_STUB_USER_SHELL.
  
  if [ "$1" != "." ] || [ "$2" != "-read" ] || [ -z "$3" ]; then
      echo "dscl stub: unsupported invocation: $*" >&2
      exit 64
  fi
  
  case "$4" in
      UserShell|'') ;;
      *)
          echo "dscl stub: unsupported attribute: $4" >&2
          exit 64
          ;;
  esac
  
  if [ -z "${FORGEL_STUB_USER_SHELL:-}" ]; then
      echo "dscl stub: FORGEL_STUB_USER_SHELL is not set" >&2
      exit 1
  fi
  
  printf 'UserShell: %s\n' "$FORGEL_STUB_USER_SHELL"
  exit 0
  ```
- **passwd database (`getent`, /etc/passwd)** — mode `direct`; interface: Login-shell lookup when $SHELL is empty and dscl is unavailable: `getent passwd <uid>` and, as fallback, the /etc/passwd line for the uid; field 7 is the login shell.; docs: getent(1), passwd(5); evidence: Specification dependency entry: `getent passwd <uid>` or the /etc/passwd line for the uid, field 7 is the login shell. `getent` and /etc/passwd are local facilities present in the environment contract for a Linux sandbox (environment/Dockerfile, environment.yaml).
- **ps** — mode `direct`; interface: Parent/login process fallback for the invoking user's shell: `ps -p <pid> -o comm=` (BSD and GNU both accept -o comm=), with basename normalisation so `/bin/sh` maps to sh; used when $SHELL is empty and no account database entry is usable.; docs: ps(1); evidence: Specification dependency entry: `ps -p <pid> -o comm=` (BSD and GNU both accept -o comm=) to read the parent process command for the parent-shell fallback; the output may need basename normalisation. ps is a locally installed executable (procps/BSD base).
- **GNU coreutils `timeout` (optional)** — mode `direct`; interface: Optional bound on the verification shell: `timeout <seconds> <shell> -l -i -c '<command>'` when `timeout` is on PATH; when absent the installer must use a portable background-and-kill watchdog instead, so `timeout` is never a hard requirement.; docs: timeout(1); evidence: Specification dependency entry: used when present to bound the verification shell; when absent the installer must fall back to a portable background-and-kill watchdog. Must not be a hard requirement. GNU coreutils timeout is the local executable used when available.
