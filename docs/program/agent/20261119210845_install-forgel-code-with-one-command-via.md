# Agent Run: Install Forgel Code with one command via an installer script

- Task: `20261119210845_install-forgel-code-with-one-command-via`
- Status: `done`
- Repository: `code`
- Steps: 6
- Finished: 2026-11-19T22:10:22+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The `code` repository is the target: its README carries the current pip/pipx installation instructions, `pyproject.toml` declares the `forgel-code` entry point, and the package lives under `forgel_code/`.
- Default installation directory is `~/.local/share/forgel-code`, overridable by an environment variable; the executable goes to `~/.local/bin`, the conventional per-user bin directory.
- The profile file is chosen per shell (`~/.profile` by default, `.bashrc`/`.zshrc` when detectable); the added block is delimited by a comment marker naming Forgel Code.
- The opt-out variable is named `FORGEL_CODE_NO_PROFILE_EDIT` and the install root override `FORGEL_CODE_HOME`.
- Uninstall is an explicit `--uninstall` flag on the same script, as 'one command' through the same entry point.
- Offline tests invoke the installer with the local source tree (a source override or `sh install.sh` run from the checkout) and a temporary HOME, so no network is used.
- The README example keeps the `v0.1.0` tag, matching the current released version.
- Windows fallback remains `pip install --user` as a single line outside the main path.
- Профиль выбирается по `$SHELL` (`~/.zshrc`, `~/.bashrc`/`~/.bash_profile`), иначе `$HOME/.profile`.
- Opt-out переменная называется `FORGEL_CODE_NO_PROFILE_EDIT`, офлайн-источник — `FORGEL_CODE_SOURCE`.
- Отсутствие pytest в интерпретаторе `python` — дефект окружения, а не репозитория; исправлено установкой pytest в это окружение, изменений в манифест зависимостей не вносилось.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 6
- Estimated input tokens (all calls): 53191
- Provider input/output tokens: 52808 / 1695
- Estimated prompt at the end: 9928 tokens
- State: not needed

## Specification (`docs/program/specs/20261119210845_install-forgel-code-with-one-command-via.md`)

# Task Spec: Install Forgel Code with one command via an installer script

## Document Information

| Field | Value |
|-------|-------|
| Feature | Install Forgel Code with one command via an installer script |
| Project | — |
| Task | `20261119210845_install-forgel-code-with-one-command-via` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-19T21:09:28+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

Forgel Code can currently only be obtained by cloning the repository and creating a virtual environment, which makes the first-run experience multi-step and error-prone. The milestone goal is a single-command installation, but no `install.sh` exists at the repository root, the README's installation path is not the one-command path, and there are no automated guards for either the installer behaviour or the README's installation section.

**Outcome:** A POSIX `sh` installer at the repository root installs the Forgel Code client into a per-user prefix, creates a `forgel-code` entry point on PATH via a single marked profile block, supports a profile opt-out, is safely re-runnable, can be uninstalled with a flag, and prints the installed version. The README's first and only main installation command is `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`, with one update line, one uninstall line, the Python 3 and `forgel` engine prerequisites, and a single Windows line outside the main path. Automated tests run the real installer offline in a temporary HOME and guard the README ordering.

## Goals

- Make Forgel Code installable and runnable with one documented command.
- Keep the installation self-contained, per-user, re-runnable and reversible.
- Make the single-command installation path the only documented main path, guarded by tests.

## Non-Goals

- Any change to client behaviour, rendering, session handling or engine calls under `forgel_code/`.
- Publishing to PyPI, pipx, Homebrew, apt or any other distribution channel.
- A Windows-native installer (PowerShell, `.bat`); Windows stays a documented `pip install --user` fallback line.
- Automatic update checking, self-update, or version pinning beyond the tag in the URL.
- Installing, bundling or managing the `forgel` engine itself.
- Shell profile support for shells other than the ones the installer detects from `$SHELL` (no new shell-detection framework).
- CI configuration changes beyond running the existing test command.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-001: The interactive client moves to a separate public repository in the same organization as the engine. | User, 2026-11-16 21:14 |
| — | D-004: The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-005: The second repository is public and lives in the same organization as the first (`forgel-dev`). | User, 2026-11-16 21:14 |
| — | D-003: The base parameterized command line (`forgel <command>`) stays in the engine; the separate client replaces the interactive chat mode. | User, 2026-11-16 18:31 |
| — | D-002: The client is a thin UI over the engine's parameterized commands and does not call the model, read project files or run checks itself. | User, 2026-11-16 18:31 |

## Functional Requirements

- **FR-1**: R1: `install.sh` exists at the repository root with the executable bit set and is valid POSIX `sh` (runs under `sh`, not only `bash`).
- **FR-2**: R2: `install.sh` depends only on `sh` standard utilities and Python 3; it does not require a pre-existing virtualenv, network access when given a local source, or any package manager other than the Python tool it detects.
- **FR-3**: R3: `install.sh` installs the client into `FORGEL_CODE_HOME` when set, otherwise `$HOME/.local/share/forgel-code`; installing must not require virtualenv activation.
- **FR-4**: R4: `install.sh` writes an executable `forgel-code` launcher into `FORGEL_CODE_BIN` when set, otherwise `$HOME/.local/bin`; running that launcher without activation must work.
- **FR-5**: R5: `install.sh` adds the bin directory to PATH exactly once, inside a block delimited by a clearly marked start and end comment, in the shell profile selected from `$SHELL` (falling back to `$HOME/.profile`); no second block is appended on re-run.
- **FR-6**: R6: When the opt-out environment variable is set, `install.sh` opens no profile file for writing and instead prints exactly the `export PATH=...` line the user must add.
- **FR-7**: R7: On success `install.sh` prints the installed version and exits with status 0.
- **FR-8**: R8: Re-running `install.sh` over an existing installation replaces the installation, leaves exactly one PATH block, and exits with status 0.
- **FR-9**: R9: `install.sh --uninstall` removes the installation directory, the `forgel-code` launcher, and the marked PATH block that the installer added, and exits with status 0.
- **FR-10**: R10: `install.sh` accepts a local source tree (offline mode, e.g. via an environment variable pointing at a checkout) so the installation path can be exercised without network access.
- **FR-11**: R11: `README.md`'s installation section starts with exactly the command `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh` as its first installation command, and no `pip install`, `python3 -m venv`, `pipx` or `--user` appears before it or as an alternative main path.
- **FR-12**: R12: `README.md` retains the Python 3 requirement, the requirement that the `forgel` engine is on PATH including how to point at a custom engine path, exactly one update line (same command with a new tag), and exactly one uninstall line.
- **FR-13**: R13: `README.md` mentions Windows in a single short line outside the main path, using `pip install --user`, explicitly marked as not the main installation method.
- **FR-14**: R14: A test guards R11 by parsing `README.md` for ordering, so a later regression fails the suite.
- **FR-15**: R15: A test runs the real `install.sh` offline against a local source tree into a temporary directory and asserts that the `forgel-code` launcher exists, that `forgel-code --version` prints the installed version with exit code 0, and that a second run exits 0 without breaking the first installation.
- **FR-16**: R16: A test asserts that with the opt-out variable set no profile file is created or modified and nothing is written outside the temporary target directory.
- **FR-17**: R17: No file under `forgel_code/` is modified.

## Technical Requirements

- `install.sh` must be POSIX `sh` compatible and pass shell parsing/warnings under `sh -n`.
- Tests must never write to the developer's real `$HOME`, real shell profile, or `~/.local`; every installer test sets `HOME` and the target/bin/profile variables to a temporary directory.
- No network access is required by the test suite; the offline test must exercise the real installer, not a stub.
- The client package, engine contract and console entry points under `forgel_code/` must stay byte-identical.
- Documentation changes stay within the installation section plus the lines the requirements name; unrelated README content is not rewritten.
- The installer must remain a single self-contained file so it can be piped through `curl ... | sh`.

## User Stories

- As a new user, I want one command that installs Forgel Code, so that I do not have to clone the repository or activate a virtualenv.
- As a user with a custom shell setup, I want to opt out of profile modification, so that the installer does not edit my dotfiles and can tell me the exact line to add.
- As a user upgrading to a new release, I want to re-run the same command with a new tag, so that updating is the same as installing.
- As a user who no longer wants the tool, I want one uninstall command, so that the installation and the PATH line it added are gone.
- As a maintainer, I want tests that fail when the README's installation path drifts back to pip/venv/pipx, so that the one-command promise is enforced.

## Tests

- A1: `python -m pytest tests/test_readme_install.py -q`
- A2: `python -m pytest tests/test_install.py -q -k install`
- A3: `python -m pytest tests/test_install.py -q -k version`
- A4: `python -m pytest tests/test_install.py -q -k rerun or twice or idempotent`
- A5: `python -m pytest tests/test_install.py -q -k opt_out or profile`
- A6: `python -m pytest tests/test_install.py -q -k uninstall`
- A7: `python -m pytest -q`
- A8: `git diff --name-only -- forgel_code`
- R1: `sh -n install.sh`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: A1: `README.md` contains the installer line as the first installation command, and its installation section contains no `pipx`, `python3 -m venv` or `pip install` instruction on the main path.
- **AC-2**: A2: Running `install.sh` in a clean temporary HOME installs the client, prints the installed version and exits with code 0.
- **AC-3**: A3: After installation, `forgel-code --version` prints the version and exits with code 0.
- **AC-4**: A4: Running `install.sh` twice in a row exits with code 0 both times and leaves exactly one PATH block in the shell profile.
- **AC-5**: A5: With the opt-out environment variable set, no profile file is created or modified and the script prints an `export PATH=...` line.
- **AC-6**: A6: `install.sh --uninstall` removes the installation directory, the launcher and the PATH block it added.
- **AC-7**: A7: The full test suite passes, including the new README guard and the offline installation tests.
- **AC-8**: A8: No file under `forgel_code/` is modified.

## Scope Boundaries

- A new `install.sh` at the repository root (POSIX `sh`, executable bit set).
- `install.sh` install logic: install the client into `${FORGEL_CODE_HOME:-$HOME/.local/share/forgel-code}`, create the `forgel-code` executable in `${FORGEL_CODE_BIN:-$HOME/.local/bin}`.
- `install.sh` PATH handling: one clearly marked block in the user's shell profile, opt-out via environment variable, printed `export PATH=...` line on opt-out.
- `install.sh` re-run idempotency and `install.sh --uninstall`.
- `install.sh` version reporting at the end of a successful install.
- README installation section rewrite: one installer command first, prerequisites, update line, uninstall line, one Windows line.
- Automated tests: README guard and offline real-installer tests in `tests/test_readme_install.py` and `tests/test_install.py`.
- Any packaging-adjacent metadata the installer needs (e.g. exposing the version through the existing build backend) without changing client package behaviour.
- Any change to client behaviour, rendering, session handling or engine calls under `forgel_code/`.
- Publishing to PyPI, pipx, Homebrew, apt or any other distribution channel.
- A Windows-native installer (PowerShell, `.bat`); Windows stays a documented `pip install --user` fallback line.
- Automatic update checking, self-update, or version pinning beyond the tag in the URL.
- Installing, bundling or managing the `forgel` engine itself.
- Shell profile support for shells other than the ones the installer detects from `$SHELL` (no new shell-detection framework).
- CI configuration changes beyond running the existing test command.

## Risks

- The installer may modify the developer's real shell profile if tests fail to override `HOME` and the profile-path variables, breaking the host machine and the 'nothing outside the temporary directory' criterion.
- Idempotency is easy to get wrong: a second run that re-appends the marked block, or an uninstall whose block marker does not match character-for-character, fails A4/A6.
- `curl ... | sh` piping means the script cannot read from stdin or rely on `$0`; an implementation that does so passes local runs but breaks the documented command.
- Offline installation from a local source tree may tempt an implementation to bypass the real installer or stub `pip`; the test must exercise `install.sh` end-to-end for the criteria to be honest.
- The README guard can be satisfied by vague wording, so it must pin ordering (installer line first) and forbid the named alternatives above it.
- The launcher must not depend on an activated virtualenv; a `forgel-code` wrapper that relies on the invoking shell's environment passes manual checks but not A3 after profile reload in a fresh shell.
- Recording a `pip install --user` Windows line while forbidding `pip install` in the main path risks a naive guard test failing on the legitimate Windows line; the guard must scope to the main installation path.

## Open Questions

- Should the installer's offline source mode be an environment variable pointing at a checkout, or a positional argument? (Reversible: the tests can expose either, but the README must not change.)

## Affected Files

- install.sh (new, repository root)
- README.md (installation section and prerequisites)
- tests/test_install.py
- tests/test_readme_install.py
- pyproject.toml (only if installer metadata or version exposure requires it)
- _build_backend.py (only if version exposure requires it)

## Assumptions

- The shell profile is chosen from `$SHELL` (`zsh` -> `~/.zshrc`, `bash` -> `~/.bashrc` or `~/.bash_profile`), with `$HOME/.profile` as the fallback when it cannot be determined.
- Environment variables are named `FORGEL_CODE_HOME` (install prefix), `FORGEL_CODE_BIN` (launcher dir), `FORGEL_CODE_NO_MODIFY_PATH` (opt-out), consistent with the note that each is an 'environment variable'.
- Offline installation uses `FORGEL_CODE_SOURCE` pointing at a local checkout, defaulting to the repository containing the script.
- `tests/test_install.py` and `tests/test_readme_install.py` already exist in the tree; the task extends/replaces their content rather than adding new filenames.
- The version string is the one already produced by the package (`forgel_code --version`); the installer does not invent a new version scheme.
- The one-command install assumes the tag `v0.1.0` exists in the `forgel-dev/code` repository, matching the URL in the required README line.

## Related Documents

- AGENTS.md
- FORGEL.md
- README.md
- pyproject.toml

## Revision History

- v1: Initial specification for the one-command installer task.

## External Dependencies

- **POSIX shell (`/bin/sh`)** — mode `direct`; interface: `install.sh` is executed by `sh`, both directly (`sh install.sh`) and via the documented `curl ... | sh` pipeline; the offline installer tests invoke `sh install.sh`.; docs: POSIX.1-2017 Shell Command Language, https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html; evidence: Repository contains an executable `install.sh` at its root written as a POSIX sh script (per the task summary), and the test harness runs it with `sh install.sh`; `/bin/sh` is a locally installed executable available to the test environment.
- **Python 3 interpreter with `pip` module** — mode `direct`; interface: The installer uses `python3` (and, when needed, `python3 -m pip install --target <prefix> .`) to place the client package into the per-user target prefix under `~/.local/share/forgel-code`; the installed `forgel-code` launcher runs the client with `python3 --version`-style invocation. Tests assert `forgel-code --version` exits 0.; docs: https://pip.pypa.io/en/stable/cli/pip_install/ ; https://docs.python.org/3/library/; evidence: The offline installation tests are required to run the installer against a local source tree into a temporary directory and then execute `forgel-code --version`, which requires a locally installed `python3` (and the `pip` module used by the installer); both are standard locally installed executables in the project's environment contract.
- **curl** — mode `direct`; interface: Used by the single documented installation command `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`; it is not executed by the offline test suite (tests stream the local `install.sh` directly).; docs: https://curl.se/docs/manpage.html; evidence: README.md contains exactly one installation command, `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`, as the first installation step; `curl` is a locally installed executable, and the offline tests substitute the local `install.sh` for the network fetch.
- **GitHub raw content hosting (`raw.githubusercontent.com`)** — mode `stub`; interface: The README's one-line install command targets `https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh`. Tests never fetch this URL; the offline tests read the identical `install.sh` from the local repository root, so the network endpoint is emulated by sourcing the vendored script.; docs: README.md installation command referencing `https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh`; evidence: `install.sh` is present at the repository root (per the task summary and README install command), and the README documents the raw URL as the source of that same script; therefore the raw-hosted artifact can be reproduced deterministically from the local repository check-out.
  ```
  #!/bin/sh
  # Offline stub for raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh
  # The repository already contains the same installer at its root.
  set -eu
  REPO_ROOT=${REPO_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
  exec sh "$REPO_ROOT/install.sh" "$@"
  ```
- **pytest** — mode `direct`; interface: Runs the existing project test suite, including the new README guard test and the real offline installation tests (`sh install.sh` into a temporary HOME, `forgel-code --version`, second run, opt-out, and `--uninstall`).; docs: https://docs.pytest.org/en/stable/; evidence: The project's test configuration (pyproject.toml / requirements-dev / tests directory) declares `pytest` as the test runner, and the required README guard and offline installer tests are described as part of the existing pytest suite; `pytest` is a locally installed executable in the project environment.


## Summary

Продуктовая часть задачи уже была реализована в предыдущих попытках; в этой попытке код репозитория не менялся. Единственная причина падения приёмки была в окружении: интерпретатор `python` (`/Users/okalistratov/.forgel-cli/bin/python3.13`) не содержал pytest. Я установил pytest в это окружение (`python -m pip install pytest` → pytest 9.2.0), после чего финальная команда `python -m pytest -q` прошла: `134 passed, 137 subtests passed in 45.04s`, exit 0. Реализованное и подтверждённое: POSIX `install.sh` в корне (поддержка `FORGEL_CODE_HOME`, `FORGEL_CODE_BIN`, `FORGEL_CODE_NO_PROFILE_EDIT`, `FORGEL_CODE_SOURCE`, один маркированный блок PATH, идемпотентный повторный запуск, `--uninstall`, печать установленной версии); README с единственной командой установки `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh | sh`, предпосылками (Python 3 и `forgel` в PATH, включая указание кастомного пути движка), строкой обновления, строкой удаления и одной строкой Windows через `pip install --user`; тесты `tests/test_readme_install.py` (порядок команд и запрет pip/venv/pipx в основном пути) и `tests/test_install.py` (реальный офлайн-прогон установщика во временном HOME, `forgel-code --version`, повторный запуск, opt-out без изменения профиля, `--uninstall`). Файлы под `forgel_code/` не изменялись.

## Files Changed

- `README.md`
- `install.sh`
- `tests/test_cli.py`
- `tests/test_install.py`
- `tests/test_readme_install.py`

## Commands

- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pip", "install", "pytest"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
...................................................... [ 40%]
................................................. [ 76%]
...............................                  [100%]
134 passed, 137 subtests passed in 46.07s

```

## Actions

- run: ['python', '-m', 'pytest', '-q']
- run: ['python', '-m', 'pip', 'install', 'pytest']
- run: ['python', '-m', 'pytest', '-q']
- run: ['sh', '-n', 'install.sh']
