# Feature: Install Forgel Code with one command via an installer script

## Document Information

| Field | Value |
|-------|-------|
| Feature | Install Forgel Code with one command via an installer script |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-19T21:08:45+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

Replace the multi-step pip, virtualenv and pipx installation instructions in the Forgel Code client repository with a single install line that downloads and runs an installer script from the repository at a pinned tag. The installer places the client in a per-user location under the home directory, creates an executable entry point, adds its directory to PATH once via a marked block in the shell profile (with an opt-out that prints the export line instead), prints the installed version, is safe to re-run, and supports update and uninstall through the same script. README keeps only the single command, a Python 3 prerequisite, the engine availability note, one update line, one uninstall line, and a separate Windows note outside the main path. Tests guard the README shape and verify a real offline installation into a temporary directory.

## Goals

- The repository contains an installer script `install.sh` at the repository root, executable, and self-contained (POSIX sh, no dependencies beyond Python 3 and standard shell utilities).
- The installer installs the Forgel Code client into a per-user location under the home directory (default `~/.local/share/forgel-code`), overridable through an environment variable, without requiring virtualenv activation.
- The installer creates an executable `forgel-code` entry point in a stable per-user bin directory and makes it runnable by adding that directory to PATH exactly once, inside a clearly marked block in the shell profile; it does not duplicate the block on re-run.
- The installer supports an opt-out of profile modification: when the opt-out environment variable is set, it does not touch any profile file and instead prints the exact `export PATH=...` line the user must add.
- At the end the installer prints the installed version, so success is immediately visible.
- Re-running the installer over an existing installation is safe: it replaces the installation, does not duplicate profile lines, and exits with code 0.
- Updating is the same command with a new tag in the URL; the README states this explicitly as one line.
- Uninstalling is one command through the same script (an explicit flag), which removes the installation and the PATH block it added.
- README shows exactly one installation command as the first installation step: `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`. No `pip install`, `python3 -m venv`, `pipx` or `--user` appears before it or as an alternative main path.
- README keeps: the Python 3 requirement, the requirement that the `forgel` engine is available in PATH (and how to point at a custom path), one update line, one uninstall line.
- Windows is a single short line outside the main path, using `pip install --user`, explicitly marked as not the main installation method.
- The client package code and its calls to the engine are not changed; only installation, packaging-adjacent files and documentation change.
- Automated tests guard that the README's first and only installation command is the installer line and that `venv`, `pip install` and `pipx` do not appear before it.
- An automated test runs the installer offline against a local source tree into a temporary directory and asserts that `forgel-code` appears, `forgel-code --version` prints the installed version with exit code 0, and a second run also exits with code 0 without breaking the first installation.
- An automated test asserts that the profile opt-out prevents any profile modification and that nothing is written outside the temporary target directory.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- **FR-1**: The repository contains an installer script `install.sh` at the repository root, executable, and self-contained (POSIX sh, no dependencies beyond Python 3 and standard shell utilities).
- **FR-2**: The installer installs the Forgel Code client into a per-user location under the home directory (default `~/.local/share/forgel-code`), overridable through an environment variable, without requiring virtualenv activation.
- **FR-3**: The installer creates an executable `forgel-code` entry point in a stable per-user bin directory and makes it runnable by adding that directory to PATH exactly once, inside a clearly marked block in the shell profile; it does not duplicate the block on re-run.
- **FR-4**: The installer supports an opt-out of profile modification: when the opt-out environment variable is set, it does not touch any profile file and instead prints the exact `export PATH=...` line the user must add.
- **FR-5**: At the end the installer prints the installed version, so success is immediately visible.
- **FR-6**: Re-running the installer over an existing installation is safe: it replaces the installation, does not duplicate profile lines, and exits with code 0.
- **FR-7**: Updating is the same command with a new tag in the URL; the README states this explicitly as one line.
- **FR-8**: Uninstalling is one command through the same script (an explicit flag), which removes the installation and the PATH block it added.
- **FR-9**: README shows exactly one installation command as the first installation step: `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`. No `pip install`, `python3 -m venv`, `pipx` or `--user` appears before it or as an alternative main path.
- **FR-10**: README keeps: the Python 3 requirement, the requirement that the `forgel` engine is available in PATH (and how to point at a custom path), one update line, one uninstall line.
- **FR-11**: Windows is a single short line outside the main path, using `pip install --user`, explicitly marked as not the main installation method.
- **FR-12**: The client package code and its calls to the engine are not changed; only installation, packaging-adjacent files and documentation change.
- **FR-13**: Automated tests guard that the README's first and only installation command is the installer line and that `venv`, `pip install` and `pipx` do not appear before it.
- **FR-14**: An automated test runs the installer offline against a local source tree into a temporary directory and asserts that `forgel-code` appears, `forgel-code --version` prints the installed version with exit code 0, and a second run also exits with code 0 without breaking the first installation.
- **FR-15**: An automated test asserts that the profile opt-out prevents any profile modification and that nothing is written outside the temporary target directory.

## Technical Requirements

- Public artifacts are in English (D-025); the chat reply may be Russian.
- The client is a thin UI over the engine's parameterized commands (D-002); installation changes must not add model access, project file reads or checks to the client.
- The installer must not require network access at run time beyond fetching the script itself, and must work when the source tree is local (used by tests).
- Do not weaken or delete existing tests to make the suite pass.
- Keep the existing built-in build backend usable; no new third-party runtime dependency.

## User Stories

- None stated.

## Tests

- None stated.
- Command: `python3 -m unittest discover -s tests -q`

## Acceptance Criteria

- **AC-1**: `README.md` contains the installer line as the first installation command and contains no `pipx`, `python3 -m venv` or `pip install` instruction in the main installation path.
- **AC-2**: Running `install.sh` in a clean temporary HOME installs the client, prints the installed version and exits with code 0.
- **AC-3**: After installation, `forgel-code --version` prints the version and exits with code 0.
- **AC-4**: Running `install.sh` twice in a row exits with code 0 both times and leaves exactly one PATH block in the shell profile.
- **AC-5**: With the opt-out environment variable set, no profile file is created or modified and the script prints an `export PATH=...` line.
- **AC-6**: `install.sh --uninstall` removes the installation and the PATH block it added.
- **AC-7**: The full test suite passes, including the new README guard and the real offline installation tests.
- **AC-8**: No file under `forgel_code/` is modified.

## Scope Boundaries

- Public artifacts are in English (D-025); the chat reply may be Russian.
- The client is a thin UI over the engine's parameterized commands (D-002); installation changes must not add model access, project file reads or checks to the client.
- The installer must not require network access at run time beyond fetching the script itself, and must work when the source tree is local (used by tests).
- Do not weaken or delete existing tests to make the suite pass.
- Keep the existing built-in build backend usable; no new third-party runtime dependency.

## Risks

- None stated.

## Open Questions

- None.

## Affected Files

- Not identified yet.

## Assumptions

- The `code` repository is the target: its README carries the current pip/pipx installation instructions, `pyproject.toml` declares the `forgel-code` entry point, and the package lives under `forgel_code/`.
- Default installation directory is `~/.local/share/forgel-code`, overridable by an environment variable; the executable goes to `~/.local/bin`, the conventional per-user bin directory.
- The profile file is chosen per shell (`~/.profile` by default, `.bashrc`/`.zshrc` when detectable); the added block is delimited by a comment marker naming Forgel Code.
- The opt-out variable is named `FORGEL_CODE_NO_PROFILE_EDIT` and the install root override `FORGEL_CODE_HOME`.
- Uninstall is an explicit `--uninstall` flag on the same script, as 'one command' through the same entry point.
- Offline tests invoke the installer with the local source tree (a source override or `sh install.sh` run from the checkout) and a temporary HOME, so no network is used.
- The README example keeps the `v0.1.0` tag, matching the current released version.
- Windows fallback remains `pip install --user` as a single line outside the main path.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-19 — Initial request recorded.
