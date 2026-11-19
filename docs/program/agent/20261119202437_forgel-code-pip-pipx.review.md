# Task Review: Установка Forgel Code обычным pip, pipx — необязательный вариант

- Task: `20261119202437_forgel-code-pip-pipx`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-19T20:45:47+00:00

## Summary

The attributed change rewrites the README install section so plain pip (bundled with Python) is the documented primary path: the first command block is a virtual-environment install with `python3 -m pip install` pinned to `@v0.1.0`, followed by a `--user` variant, a pinned exact-version variant, a section explaining where the `forgel-code` script lands with PATH troubleshooting (`site --user-base`, `pip show -f`, `export PATH`), a `python3 -m forgel_code --version` fallback, and an update section using `--upgrade` and `--upgrade --force-reinstall` for the unchanged-version/new-commit case. pipx appears exactly once, marked "optional", and after the pip instructions; the existing constraints (dependency-free/offline build, no editable install, engine via PATH or --engine/$FORGEL_ENGINE) are preserved. tests/test_readme_install.py structurally enforces the first-command-is-plain-pip/pinned and pipx-optional-and-late rules (failing as designed), and tests/test_install.py performs an offline `--no-index --no-build-isolation --no-deps` install of the local tree into a temp `--target` and asserts both `forgel-code --version` and `python3 -m forgel_code --version` print the installed version with exit 0. No file under `forgel_code/` changes and no existing tests were removed or weakened. The extra root-level `pytest.py` shim is test scaffolding (it explicitly only forwards to real pytest when available and otherwise drives the unittest suite) that does not enter the installed package and does not alter client behaviour; the shipped package still contains only `forgel_code`.

## Requirements

- FR-1/AC-1: first install command block contains `python3 -m pip install` pinned to an exact revision, no floating branch: pass — First block runs `python3 -m venv .venv`, activates, then `python3 -m pip install "git+https://github.com/forgel-dev/code@v0.1.0"`; tag pin, not a branch.
- FR-2/FR-3: first install requires only Python+pip and shows a virtual-environment install: pass — Block creates and activates `.venv` and installs with plain pip; no pipx or other tool needed.
- FR-4: README shows a `--user` install for system Python without a venv: pass — `python3 -m pip install --user "git+...@v0.1.0"` shown under a heading saying no venv/root is required.
- FR-5: README states where the executable lands and how to add it to PATH, including locating it: pass — Covers `.venv/bin`, `.venv\Scripts`, and user scripts (`~/.local/bin`, `%APPDATA%\Python\Python3x\Scripts`); shows `site --user-base`, `pip show -f`, `export PATH`/`setx`.
- FR-6: `python3 -m forgel_code` fallback with a version check: pass — `python3 -m forgel_code --version` documented as the PATH fallback with interpreter guidance.
- FR-7: update section covers `--upgrade` and `--force-reinstall` including unchanged version with new commit: pass — `--upgrade @v0.1.1` plus `--upgrade --force-reinstall @<commit-sha>` and an explanatory paragraph about the unchanged-version case.
- FR-8/AC-4: pipx at most once, explicitly optional, after pip instructions: pass — Single pipx line, contains 'optional', follows all pip install instructions.
- FR-9: existing constraints preserved (dependency-free/offline build, no editable install, engine via PATH or --engine/$FORGEL_ENGINE): pass — All three constraints retained verbatim in the install section.
- FR-10/FR-11/AC-6: documentation test enforces plain-pip-first, pinned, and pipx-optional-and-late, failing as designed: pass — tests/test_readme_install.py parses headings and fences, asserts the first install command is plain pip and returns a non-branch pin, and raises when pipx appears more than once, not on one line, without 'optional', or before the first plain pip line.
- FR-12/13/14/AC-7: offline plain-pip install into temp target; `forgel-code --version` and `python3 -m forgel_code --version` print installed version, exit 0: pass — test_install.py uses `--target --no-index --no-build-isolation --no-deps` on a copied local tree, asserts exit 0, and checks both entry points against the installed METADATA version; QA reports pass.
- FR-15/AC-9: no file under `forgel_code/` changed: pass — Attributed files are README.md, pytest.py, tests/test_install.py, tests/test_readme_install.py; nothing under `forgel_code/`.
- FR-16/AC-8: existing tests continue to pass unchanged; no weakened/deleted tests: pass — No test removals; QA reports the full suite passing. The added README note about the pytest shim does not alter package behaviour.
- Scope: only documentation and test-support files change; package code untouched: pass — The root `pytest.py` is test scaffolding only (delegates to real pytest when present, otherwise runs the unittest suite), is not packaged into the wheel (only `forgel_code` is built), and does not change client behaviour.

## Blocking

- none

## Test Removals

- none


