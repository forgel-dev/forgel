# Feature: Fix install.sh so a new terminal finds forgel-code on PATH

## Document Information

| Field | Value |
|-------|-------|
| Feature | Fix install.sh so a new terminal finds forgel-code on PATH |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-22T02:57:05+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

The installer currently completes while the launcher directory never reaches PATH in a freshly opened terminal. It picks the profile file from $SHELL alone: on macOS a bash login shell never reads ~/.bashrc, and under `curl … | sh` $SHELL can be empty, sending the block to ~/.profile while the terminal reads ~/.zshrc. It also never checks that its own change took effect. This change makes the installer detect the real login shell, write the block into a profile file a new terminal actually reads, start a clean login shell afterwards and verify that `forgel-code` resolves, and fail with a message naming the edited file and the observed PATH when it does not. --uninstall removes the block from every profile file the installer can have written.

## Goals

- install.sh must not derive the profile file from $SHELL alone: when $SHELL is unset, empty or names an unhandled shell, it reads the account login shell (macOS `dscl . -read "$HOME" UserShell`, otherwise the passwd entry) and only then falls back to $HOME/.profile.
- For zsh the block goes into $HOME/.zshrc, created when missing.
- For bash the block goes into the first existing file of $HOME/.bash_profile, $HOME/.bash_login, $HOME/.profile; if none exists, $HOME/.bash_profile is created. The block is never written to $HOME/.bashrc alone, because a login bash shell does not read it.
- FORGEL_CODE_PROFILE still overrides the chosen file; FORGEL_CODE_NO_MODIFY_PATH and FORGEL_CODE_NO_PROFILE_EDIT still leave every profile file untouched, print the exact `export PATH="<bin>:$PATH"` line and exit 0.
- After writing the block the installer verifies it: it starts the detected login shell as a login interactive shell in a cleared environment (HOME, SHELL, TERM, minimal PATH) and resolves `command -v forgel-code`; the result must be the launcher just written.
- If verification fails, the installer exits non-zero and prints the edited profile file, the block written and the PATH seen in the fresh shell. It must not claim the change is active unless verification passed.
- On success the installer prints the detected shell, the profile file written and the fresh-shell check result.
- Re-running keeps exactly one marked block per edited file and leaves the rest of the file byte-identical.
- --uninstall removes the marked block from every profile file this installer can have written (.zshrc, .zprofile, .zshenv, .bash_profile, .bash_login, .profile), leaves the rest of each file unchanged, and still removes the prefix and the launcher.
- The documented `curl … | sh` shape keeps working: POSIX sh, passes `sh -n`, uses `set -eu`, never reads stdin.
- README documents which file is edited per shell, that the installer verifies the result in a fresh shell, how the opt-out line is printed, and what --uninstall removes.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

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

- Keep the script POSIX sh and safe to pipe into a shell; no bashisms, no stdin reads.
- Do not change the client package, the entry point, the build backend or the launcher format beyond what the PATH fix needs.
- Do not weaken existing installer tests; extend them.
- Tests must not need network, the real GitHub repository or the real user profile: temporary HOME and local source tree only.

## User Stories

- None stated.

## Tests

- None stated.
- Command: `python3 -m pytest -q`

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

- Keep the script POSIX sh and safe to pipe into a shell; no bashisms, no stdin reads.
- Do not change the client package, the entry point, the build backend or the launcher format beyond what the PATH fix needs.
- Do not weaken existing installer tests; extend them.
- Tests must not need network, the real GitHub repository or the real user profile: temporary HOME and local source tree only.

## Risks

- None stated.

## Open Questions

- None.

## Affected Files

- Not identified yet.

## Assumptions

- The fix belongs to the `code` repository, which holds install.sh, the launcher and the installer tests.
- The earlier install run used the opt-out switch, so no profile was edited at all; that path works as designed and the change focuses on the silent-ineffective-profile case.
- The default tag v0.1.0 stays; the release is published after this change is accepted so the tag contains the fixed script.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-22 — Initial request recorded.
