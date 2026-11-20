# Task Review: Declare test dependencies in pyproject.toml

- Task: `20261120002849_declare-test-dependencies-in-pyproject-t`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-20T01:05:18+00:00

## Summary

The change matches the specification: `pyproject.toml` carries exactly one `test` extra (`pytest>=7`) and keeps `dependencies = []`; `_build_backend.py` reads that table back (via `tomllib`, with a stdlib-only in-tree fallback for 3.9/3.10) and appends `Provides-Extra: test` plus the marked `Requires-Dist` line to the same `_metadata()` text used by the wheel, the sdist and `prepare_metadata_for_build_wheel`; the README `## Tests` section shows the `[test]` install plus `python -m pytest -q` and keeps the no-install `unittest discover` path with the existing editable-install-unsupported sentence intact. New tests cover the declaration, wheel METADATA, sdist PKG-INFO, single-source rewrite, fallback parity and an offline `pip install .[test]`, and all A1–A10 / environment checks pass with `forgel_code/` and `install.sh` untouched. The only reported test change with a real replacement (`test_accepts_the_good_shape` → `test_accepts_the_extra_install_inside_the_tests_section`) is justified; the other three reported removals are within-branch renames whose behaviours are still covered by the passing `-k pyproject`, `-k single_source` and `-k offline_install` tests. Minor, non-blocking: `_build_backend.py` imports `re` without using it.

## Requirements

- FR-1/FR-2: `pyproject.toml` declares exactly one extra `test` with a single lower-bounded pytest requirement and no upper cap, while `[project] dependencies` stays the literal `[]`.: pass — `[project.optional-dependencies]` contains only `test = ["pytest>=7"]`; `dependencies = []` is unchanged.
- FR-3/FR-4: `_metadata()` emits `Provides-Extra: test` and one `Requires-Dist: <requirement>; extra == "test"` line per declared requirement, read from `pyproject.toml` with no second literal of the pytest requirement.: pass — `_extra_lines()` formats both fields from `EXTRAS` parsed out of `pyproject.toml`; no pytest literal exists in the backend.
- FR-5: with `tomllib` unavailable the backend parses the extras table with a stdlib-only in-tree parser (multi-line arrays, inline comments, both quote styles) and adds no build requirement.: pass — `_parse_extras`/`_table_body`/`_parse_string_array` implement the limited shape; `requires = []` and both `get_requires_for_build_*` still return `[]`; covered by A6.
- FR-6/FR-7: wheel METADATA, sdist PKG-INFO and `prepare_metadata_for_build_wheel` all carry the same extras lines from the single `_metadata()` text.: pass — The extras lines were added inside `_metadata()`, which is shared by all three hooks; A2, A4 and A7 pass.
- FR-8/FR-9: README `## Tests` shows installing with `[test]` then `python -m pytest -q`, keeps `python -m unittest discover -s tests` as the no-install path, and contains no editable-install instruction while keeping the existing unsupported-editable sentence.: pass — Both fenced blocks are present with the `v0.1.1` tag tarball plus `[test]` (allowed by the recorded assumption); the `## Install` sentence 'Editable installs are not supported' is kept.
- FR-10/FR-11: `install.sh`, the one-command install/update/uninstall/Windows lines and the absence of `pipx` are unchanged, and no file under `forgel_code/` is modified.: pass — Neither path appears in the attributed diff; A9 confirms an empty `git status --porcelain -- forgel_code`.
- FR-12: new tests cover the pyproject declaration, wheel METADATA, drift against the declaration, sdist PKG-INFO, single-source rewrite, fallback parity and an offline `[test]` install.: pass — `tests/test_extras.py` adds these cases and A1–A7 pass; the rewrite test loads a fresh backend for the copied tree, so the module-level cache cannot mask a changed file.
- FR-13: `tests/test_readme_install.py` still forbids `pip install` outside `## Tests`, `pipx`, virtualenv recipes and `--user` outside the Windows line, and adds a no-editable-install assertion.: pass — A8 passes; the guard test was narrowed via the justified replacement `test_accepts_the_extra_install_inside_the_tests_section`, which is present in the attributed change.
- FR-14: no existing test is deleted, skipped or weakened, and `tests/test_packaging.py`'s `dependencies = []` assertion still holds.: pass — `tests/test_packaging.py` is not in the diff and A10 passes; the reported removed test lines are within-branch renames whose behaviours remain covered by the passing `-k pyproject`, `-k single_source` and `-k offline_install` tests.
- FR-15: the offline install test uses `--no-index`, `--no-build-isolation`, `--no-deps`, `--no-cache-dir` and a temporary `--target`, with index environment variables stripped.: pass — `_clean_environment()` drops `PIP_INDEX_URL`/`PIP_EXTRA_INDEX_URL`/`PIP_FIND_LINKS`/`PIP_CONFIG_FILE`, sets `PIP_NO_INDEX=1`, and picks a Python 3.9+ that owns pip; A7 passes.
- Commit hygiene: English, imperative, signed off, no tool attribution.: pass — Both attributed commits carry `Signed-off-by: Forgel <forgel@localhost>` and no attribution lines.

## Blocking

- none

## Test Removals

- line:def test_exactly_one_extra_named_test(self) -> None:
- line:def test_rewriting_the_table_changes_the_metadata(self) -> None:
- line:def test_the_installed_metadata_declares_the_extra(self) -> None:

- tests/test_readme_install.py::ChecksFailAsDesignedTest::test_accepts_the_good_shape: replaced -> tests/test_readme_install.py::ChecksFailAsDesignedTest::test_accepts_the_extra_install_inside_the_tests_section
