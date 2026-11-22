# Feature: Make install.sh put forgel-code on PATH for a new terminal

## Document Information

| Field | Value |
|-------|-------|
| Feature | Make install.sh put forgel-code on PATH for a new terminal |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-22T06:29:11+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

The installer reports success while a new terminal cannot find forgel-code: the PATH block lands in a profile file the user's shell does not read on login and nothing verifies it. The change detects the real login shell, writes a duplicate-safe block into the files that shell reads, verifies the result in a fresh login shell with a loud failure message, and removes the block from every profile file on --uninstall.

## Product Intent

A user installs Forgel Code with one command, opens a new terminal and forgel-code just runs; the installer never claims success when the command is not reachable, and uninstalling leaves the profile files clean.

## User Experience

The owner runs the single documented install command (including via curl piped to sh), opens a new terminal and forgel-code runs. --uninstall removes the launcher, the prefix and the PATH block from every profile file the installer may have written, keeping unrelated lines intact.

## Roadmap

- Fix install.sh: correct profile selection, duplicate-safe block, post-install verification in a real login shell
- Make --uninstall remove the block from every profile file it may have written
- Extend tests/test_install.py for real shell cases, failed verification, idempotent re-run and --uninstall

## Goals

- Determine the login shell of the invoking user; when $SHELL is empty (for example in curl | sh) fall back to the shell of the parent/login process instead of assuming bash.
- For zsh write the PATH block into ~/.zshrc; for bash on macOS use ~/.bash_profile (creating it when absent) and never rely on ~/.bashrc alone, which login bash does not read. For an unknown shell write ~/.profile and print an explicit warning naming the edited file.
- The written block must be self-guarding against duplicates so that sourcing several profile files leaves exactly one occurrence of the prefix bin directory in PATH; use a POSIX-compatible case guard around the export.
- After writing, run the user's login shell as a clean non-interactive login shell with a bounded timeout and check that forgel-code resolves there. On failure exit non-zero and print the edited file, the exact block written, the shell checked and the PATH that shell sees.
- --uninstall must remove the marked block from every profile file the installer can write and must not alter other lines of those files.
- Preserve existing behaviour: offline installation of a local tree, no virtualenv, the opt-out environment variables, and idempotency on repeated install and uninstall.
- Tests must cover zsh without $SHELL, bash with an existing and a missing ~/.bash_profile, unknown shell, the duplicate-safe guard when several profiles are sourced, a failing verification, repeated install, --uninstall cleanup and installation through curl piped to sh.
- README installation instructions must match the resulting behaviour and must not describe steps the installer no longer needs.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- **FR-1**: Determine the login shell of the invoking user; when $SHELL is empty (for example in curl | sh) fall back to the shell of the parent/login process instead of assuming bash.
- **FR-2**: For zsh write the PATH block into ~/.zshrc; for bash on macOS use ~/.bash_profile (creating it when absent) and never rely on ~/.bashrc alone, which login bash does not read. For an unknown shell write ~/.profile and print an explicit warning naming the edited file.
- **FR-3**: The written block must be self-guarding against duplicates so that sourcing several profile files leaves exactly one occurrence of the prefix bin directory in PATH; use a POSIX-compatible case guard around the export.
- **FR-4**: After writing, run the user's login shell as a clean non-interactive login shell with a bounded timeout and check that forgel-code resolves there. On failure exit non-zero and print the edited file, the exact block written, the shell checked and the PATH that shell sees.
- **FR-5**: --uninstall must remove the marked block from every profile file the installer can write and must not alter other lines of those files.
- **FR-6**: Preserve existing behaviour: offline installation of a local tree, no virtualenv, the opt-out environment variables, and idempotency on repeated install and uninstall.
- **FR-7**: Tests must cover zsh without $SHELL, bash with an existing and a missing ~/.bash_profile, unknown shell, the duplicate-safe guard when several profiles are sourced, a failing verification, repeated install, --uninstall cleanup and installation through curl piped to sh.
- **FR-8**: README installation instructions must match the resulting behaviour and must not describe steps the installer no longer needs.

## Technical Requirements

- Work only in the code repository; the engine repository is not modified by this task.
- Installation stays a single offline command with no virtualenv and keeps the existing opt-out environment variables.
- Installation from a pinned tag keeps working; the installer must not assume the default branch.
- Committed artifacts are English; the chat reply follows the user's language.

## User Stories

- None stated.

## Tests

- None stated.
- Command: `python3 -m pytest -q`

## Acceptance Criteria

- **AC-1**: After a successful install a new login shell of the user's shell resolves forgel-code without any manual PATH edit.
- **AC-2**: An install that cannot make forgel-code resolvable exits non-zero and reports the edited file, the written block and the PATH seen by the checked shell.
- **AC-3**: Running the installer twice leaves exactly one marked block and one occurrence of the prefix bin directory in PATH.
- **AC-4**: --uninstall removes the marked block from every profile file the installer could have written and preserves unrelated lines.
- **AC-5**: tests/test_install.py passes with new cases for zsh without $SHELL, bash with and without ~/.bash_profile, unknown shell, failed verification, idempotent re-run and --uninstall.
- **AC-6**: The full test suite of the repository passes and no existing installer test is weakened.

## Scope Boundaries

- Work only in the code repository; the engine repository is not modified by this task.
- Installation stays a single offline command with no virtualenv and keeps the existing opt-out environment variables.
- Installation from a pinned tag keeps working; the installer must not assume the default branch.
- Committed artifacts are English; the chat reply follows the user's language.

## Risks

- None stated.

## Open Questions

- None.

## Affected Files

- Not identified yet.

## Assumptions

- The installer keeps the same prefix directory and the marked-block convention; only the target files and the block shape change.
- Verification uses a bounded, non-interactive login shell invocation so it cannot hang the installer.
- Tests isolate HOME into a temporary directory instead of touching the real profile files.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-22 — Initial request recorded.
