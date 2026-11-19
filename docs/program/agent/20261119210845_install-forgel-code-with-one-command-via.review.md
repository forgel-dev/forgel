# Task Review: Install Forgel Code with one command via an installer script

- Task: `20261119210845_install-forgel-code-with-one-command-via`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-19T22:17:34+00:00

## Summary

The attributed commit delivers the one-command installer exactly as specified: a POSIX `sh` `install.sh` at the repository root (executable, syntax-clean), installing into `${FORGEL_CODE_HOME:-$HOME/.local/share/forgel-code}` with a self-contained launcher in `${FORGEL_CODE_BIN:-$HOME/.local/bin}`, one marked PATH block selected from `$SHELL`, an opt-out that prints the `export PATH=...` line, idempotent re-run, `--uninstall`, version reporting, and offline local-source install. The README install section leads with the required `curl -fsSL .../v0.1.0/install.sh | sh` command, keeps Python 3 and the `forgel` engine prerequisite, has exactly one update and one uninstall line, and a single non-main Windows `pip install --user` line. Guards in `tests/test_readme_install.py` pin the README ordering and forbid pip/venv/pipx as a main path, and `tests/test_install.py` runs the real installer offline into a temporary HOME. `forgel_code/` is untouched. The fifteen removed tests are all pip/venv/pipx-era README-documentation guards whose scenario the task itself retires (R11 forbids `pip install`/`python -m venv`/`pipx` on the main path); the spec explicitly sanctions replacing these test files' content, and equivalent installer-command guards are present and passing, so this is a legitimate replacement rather than a weakened or silently dropped coverage. Deterministic checks (A1-A8, R1, environment) all pass. No product, security, or architectural defect found.

## Requirements

- FR-1: install.sh exists at repo root, executable, valid POSIX sh: pass — install.sh present, mode 100755, `sh -n` clean (R1 pass), written POSIX sh.
- FR-2: relies only on sh utilities and Python 3, no pre-existing venv: pass — Uses sh builtins, grep/awk/mkdir/cp/mv, and python3; --target pip install needs no venv.
- FR-3: installs into FORGEL_CODE_HOME else ~/.local/share/forgel-code: pass — PREFIX=${FORGEL_CODE_HOME:-$HOME/.local/share/forgel-code}; 'pip install --target $PREFIX'.
- FR-4: launcher in FORGEL_CODE_BIN else ~/.local/bin, no activation needed: pass — write_launcher creates executable wrapper embedding PYTHONPATH=$PREFIX and runs 'python -m forgel_code'.
- FR-5: adds bin to PATH once in a marked block chosen from $SHELL: pass — profile_path maps zsh/bash/other to .zshrc/.bashrc/.profile; MARKER_START/END block; remove_profile_block guarantees one block.
- FR-6: opt-out writes no profile and prints the export PATH line: pass — no_profile_edit short-circuits add_path, which only prints 'export PATH="..."'; A5 passes.
- FR-7: success prints installed version and exits 0: pass — install_client runs the launcher --version, prints it, returns success; A2/A3 pass.
- FR-8: re-run replaces install, one PATH block, exit 0: pass — add_profile_block strips then re-adds the block; --upgrade; A4 passes.
- FR-9: --uninstall removes prefix, launcher, marked block, exit 0: pass — uninstall() rm -rf PREFIX, rm LAUNCHER, remove_profile_block; A6 passes.
- FR-10: accepts a local source tree for offline install: pass — FORGEL_CODE_SOURCE validated via is_forgel_code_source; used by install_client.
- FR-11: README leads with the installer command; no pip/venv/pipx main path: pass — Active README install section first block is the required curl|sh line; no pip/venv/pipx before it; A1 passes.
- FR-12: keep Python 3 and forgel-engine prerequisite, one update and one uninstall line: pass — Python 3.9+ and engine-on-PATH with --engine/$FORGEL_ENGINE present; single update and single uninstall lines.
- FR-13: one short Windows line, pip install --user, marked not main: pass — Single Windows line marked 'not the main installation method' using pip install --user.
- FR-14: a test guards README ordering: pass — tests/test_readme_install.py asserts installer-first ordering and forbids alternatives; A1 passes.
- FR-15: offline real-installer test asserts launcher, --version, re-run: pass — tests/test_install.py runs real install.sh into temp HOME; A2/A3/A4 pass.
- FR-16: opt-out test asserts no profile created/modified: pass — Test sets HOME/SHELL and asserts profiles untouched; A5 passes.
- FR-17 / AC-8: no file under forgel_code/ modified: pass — Not among attributed files; A8 passes.
- Technical: tests never write the developer's real HOME/profile: pass — Every installer test overrides HOME, SHELL, FORGEL_CODE_PYTHON and target vars to a temp tree.
- No test deletions without an allowed justification: pass — The 15 removed tests are pip/venv/pipx-era README guards that R11 makes obsolete; the spec sanctions replacing these files' content and equivalent installer-command guards (test_readme_install.py) are present and passing — legitimate replacement, not weakened coverage.

## Blocking

- none

## Test Removals

- line:def test_first_install_command_is_plain_pip(self) -> None:
- line:def test_first_install_command_is_pinned(self) -> None:
- line:def test_virtual_environment_install(self) -> None:
- line:def test_user_install(self) -> None:
- line:def test_executable_location_and_path_help(self) -> None:
- line:def test_module_fallback_with_version_check(self) -> None:
- line:def test_update_section_switches_pinned_revision(self) -> None:
- line:def test_pipx_is_optional_and_after_the_pip_instructions(self) -> None:
- line:def test_existing_constraints_are_kept(self) -> None:
- line:def test_rejects_pipx_as_the_first_install_command(self) -> None:
- line:def test_rejects_a_bare_pip_script(self) -> None:
- line:def test_rejects_a_floating_branch(self) -> None:
- line:def test_rejects_pipx_before_the_pip_instructions(self) -> None:
- line:def test_rejects_pipx_without_the_optional_marker(self) -> None:
- line:def test_rejects_two_pipx_mentions(self) -> None:

- tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command: replaced -> tests/test_readme_install.py::ReadmeInstallTest::test_first_install_command_is_the_installer_line
- tests/test_cli.py::ReadmeTest::test_readme_documents_the_update_path: replaced -> tests/test_readme_install.py::ReadmeInstallTest::test_one_update_line_and_one_uninstall_line
- tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_pip_install: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command
