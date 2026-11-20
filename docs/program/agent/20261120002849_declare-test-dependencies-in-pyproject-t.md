# Agent Run: Declare test dependencies in pyproject.toml

- Task: `20261120002849_declare-test-dependencies-in-pyproject-t`
- Status: `done`
- Repository: `code`
- Steps: 30
- Finished: 2026-11-20T01:01:40+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The extra is named `test`; no `dev` extra with linters is added, since the user asked only for test dependencies.
- The pytest constraint is a lower bound (`pytest>=7`) with no upper cap, matching the request for a lower bound without a ceiling.
- The single source of the extras is `pyproject.toml`; the backend derives the metadata from it rather than repeating the version.
- The README's existing Tests section is the place to document the extra; the rest of the install documentation is not restructured.
- The existing offline-install test style (`--no-index --no-build-isolation --no-deps` into a temporary `--target`) is the pattern for the new extras test.
- The lower bound stays `pytest>=7` with no upper cap, matching the recorded intake assumption and the spec's binding shape.
- The README example installs the tagged source archive `https://github.com/forgel-dev/code/archive/refs/tags/v0.1.1.tar.gz[test]`, reusing the `v0.1.1` tag already shown in the update line.
- The acceptance selectors are satisfied by naming tests after their scenario (`drift`, `single_source`, `offline_install`, `pyproject`) rather than by weakening or duplicating tests.
- `tests/test_packaging.py` was left untouched because its `dependencies = []` assertion still holds against the extended `pyproject.toml`.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 30
- Estimated input tokens (all calls): 754914
- Provider input/output tokens: 791214 / 12966
- Estimated prompt at the end: 36941 tokens
- State: not needed

## Specification (`docs/program/specs/20261120002849_declare-test-dependencies-in-pyproject-t.md`)

# Task Spec: Declare test dependencies in pyproject.toml

## Document Information

| Field | Value |
|-------|-------|
| Feature | Declare test dependencies in pyproject.toml |
| Project | — |
| Task | `20261120002849_declare-test-dependencies-in-pyproject-t` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-20T00:30:28+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The repository has no declared way to obtain the tools its own test suite needs. `pyproject.toml` declares `dependencies = []`, `_build_backend.py` produces METADATA with no `Provides-Extra` and no `Requires-Dist`, and the README's `## Tests` section only shows `python -m unittest discover -s tests` from a checkout. A contributor who installs the client from a wheel or tag gets no way to install the test runner, and the test requirement has no single declared source: the backend would have to repeat a pytest literal to publish it. This task declares the `test` extra in the single source (`pyproject.toml`), makes the in-tree backend publish it into wheel METADATA and sdist PKG-INFO by reading that table, and documents the install-with-extra path in the README.

**Outcome:** `pyproject.toml` carries `[project.optional-dependencies]` with exactly one extra, `test`, whose only entry is a lower-bounded `pytest` requirement with no upper cap, while `[project] dependencies` stays `[]`. `_build_backend.py` reads that extra from `pyproject.toml` (with an in-tree TOML fallback for interpreters without `tomllib`) and emits `Provides-Extra: test` plus a `Requires-Dist: pytest...; extra == "test"` line into the same `_metadata()` text that feeds the wheel's `METADATA` and the sdist's `PKG-INFO`. The README `## Tests` section shows installing the client with the `test` extra and then `python -m pytest -q`, and keeps `python -m unittest discover -s tests` as the no-install path. New tests pin all of this, including a real offline `pip install` of the local tree with `[test]`. No file under `forgel_code/` changes, `install.sh` is untouched, and the existing suite still passes.

## Goals

- The `test` extra is declared once, in `pyproject.toml`, with a lower-bounded pytest requirement and no runtime dependency.
- The in-tree backend publishes that extra into wheel `METADATA` and sdist `PKG-INFO` by reading `pyproject.toml`, so the two cannot drift.
- The backend still builds on Python 3.9 and 3.10 without `tomllib` and without any new build dependency.
- The README documents installing with the `test` extra and running `python -m pytest -q`, alongside the unchanged no-install `unittest discover` path, and never proposes an editable install.
- Tests prove the declaration, the built metadata, the single source, the fallback and a real offline `pip install .[test]`.
- The client's code, the one-command installer and the existing suite are unaffected.

## Non-Goals

- Changing any file under `forgel_code/`: client behaviour and its engine calls stay byte-identical.
- Changing `install.sh`, its one-command install path, its flags or variables.
- Adding a `pipx` line, a virtualenv recipe, a `--user` recipe or any new main installation path to the README.
- Adding a runtime dependency: `[project] dependencies` stays empty.
- Implementing PEP 660 editable installs in the backend.
- Adding `setuptools`, `flit`, `hatchling`, `tomli` or any other third-party build dependency.
- Widening the extra set beyond the single `test` extra (no `dev`, `docs`, `lint` extras).
- Changing the version scheme, the `Metadata-Version` upgrade beyond what the emitted fields require, or the sdist/wheel layout.
- Changing how the existing tests are invoked by CI or by `make`.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code; it is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-002: The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | User, 2026-11-16 18:31 |
| — | D-006: The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: R1. `pyproject.toml` contains a `[project.optional-dependencies]` table with exactly one key, `test`, whose value is an array of exactly one string: a `pytest` requirement with a `>=` lower bound and no upper bound (`<`, `<=`, `==`, `~=` or a second clause after a comma must all be absent).
- **FR-2**: R2. `[project] dependencies` remains the literal empty array `dependencies = []` and no runtime requirement is added anywhere.
- **FR-3**: R3. `_build_backend.py` `_metadata()` emits the line `Provides-Extra: test` (exact extra name, no normalization drift) and, for each requirement declared under the `test` extra, one `Requires-Dist: <requirement>; extra == "test"` line, with the marker appended to the declared requirement string verbatim.
- **FR-4**: R4. The pytest requirement in the emitted metadata has exactly one source: the backend reads the `test` extra out of `pyproject.toml` at build time and must not contain a second literal of the pytest requirement (no `REQUIREMENT = "pytest..."` constant duplicating it).
- **FR-5**: R5. When `tomllib` cannot be imported (Python 3.9/3.10), the backend parses the extras from `pyproject.toml` with an in-tree parser limited to the shapes it needs — a `[project.optional-dependencies]` table of string arrays, including multi-line arrays, inline comments and both quote styles — and produces byte-identical metadata to the `tomllib` path; it must not add a build requirement or import a third-party TOML parser.
- **FR-6**: R6. `build_wheel(...)` writes a `METADATA` containing `Provides-Extra: test` and the pytest `Requires-Dist` line, and `build_sdist(...)` writes a `PKG-INFO` with the same extras, both from the same `_metadata()` text so the wheel and sdist cannot diverge.
- **FR-7**: R7. `prepare_metadata_for_build_wheel` writes the same `METADATA` text as the wheel, so `pip` sees the extra before building.
- **FR-8**: R8. `README.md`'s `## Tests` section shows, in a fenced block, an install line of the form `python3 -m pip install "<wheel path or git url with tag>[test]"` and then `python -m pytest -q`; it also keeps `python -m unittest discover -s tests` documented as the path that needs no installation.
- **FR-9**: R9. `README.md` contains no editable-install instruction: no `-e`, `--editable`, `pip install -e` or equivalent text; the existing sentence stating editable installs are unsupported is kept.
- **FR-10**: R10. `install.sh`, the one-command install line, the update line, the uninstall line, the Windows fallback line and the absence of a `pipx` line are unchanged.
- **FR-11**: R11. No file under `forgel_code/` is modified.
- **FR-12**: R12. New tests cover: (a) the `test` extra in `pyproject.toml` matches R1; (b) wheel `METADATA` carries `Provides-Extra: test` and the pytest `Requires-Dist` line with the `extra == "test"` marker; (c) the pytest requirement in the wheel `METADATA` equals the one declared in `pyproject.toml`; (d) sdist `PKG-INFO` carries the same two lines; (e) rewriting the extras table in a throw-away copy of the tree changes the emitted requirement, proving a single source; (f) the fallback parser produces the same result as `tomllib` for the real table; (g) an offline `pip install` of the local tree with `[test]` exits 0.
- **FR-13**: R13. `tests/test_readme_install.py` continues to forbid `pip install` outside the `## Tests` section, continues to forbid `pipx`, virtualenv recipes, `--user` outside the Windows line, and gains an assertion that no editable install appears anywhere in `README.md`.
- **FR-14**: R14. No existing test is deleted, skipped or weakened; `tests/test_packaging.py`'s `dependencies = []` assertion continues to hold against the extended `pyproject.toml`.
- **FR-15**: R15. The offline install test runs pip against the local tree with `--no-index`, `--no-build-isolation`, `--no-deps`, `--no-cache-dir` and a temporary `--target`, plus an environment that strips `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, `PIP_FIND_LINKS` and sets `PIP_NO_INDEX=1`, so it cannot reach the network and cannot install pytest as a side effect.

## Technical Requirements

- The build backend keeps `requires = []`; both build hooks keep returning `[]`, so an offline isolated build still needs no index.
- Python floor is unchanged: `requires-python = ">=3.9"`, so 3.9 and 3.10 (no `tomllib`) must build correctly through the fallback path.
- The build backend must import only the standard library.
- The metadata emitted must stay valid for the declared `Metadata-Version`; `Provides-Extra` and a `Requires-Dist` line with an environment marker are both legal there.
- New tests follow the existing suite's style: `unittest.TestCase`, module-level `ROOT = Path(__file__).resolve().parent.parent`, building from a `shutil.copytree` copy with the existing `IGNORED` patterns, never writing into the checked-out tree.
- Tests must not start external services or reach the network; the install test is explicitly offline.
- Commit message English, imperative mood, signed off (`git commit -s`), no tool attribution lines.
- The repository's spelling, heading levels and the existing `## Tests` heading title stay as they are so the section-based doc guard keeps finding the section.

## User Stories

- As a contributor, I want to install the client with a single `[test]` extra so that `python -m pytest -q` works without hunting for the test runner.
- As a maintainer, I want the pytest requirement declared exactly once in `pyproject.toml` so that the wheel, the sdist and the source tree cannot disagree.
- As an offline installer, I want the build backend to read the extras without a TOML library or a new build requirement so that a pinned revision still builds on a machine with no package index.
- As a Python 3.9 user, I want the extra to be published even where `tomllib` is missing so that the supported floor really works.
- As a reader of the README, I want the test section to show the install-with-extra path and the no-install path, and never an editable install the backend does not support.

## Tests

- A1: `python3 -m pytest -q tests/test_extras.py -k pyproject`
- A2: `python3 -m pytest -q tests/test_extras.py -k wheel`
- A3: `python3 -m pytest -q tests/test_extras.py -k drift or single_source`
- A4: `python3 -m pytest -q tests/test_extras.py -k sdist`
- A5: `python3 -m pytest -q tests/test_extras.py -k single_source`
- A6: `python3 -m pytest -q tests/test_extras.py -k fallback`
- A7: `python3 -m pytest -q tests/test_extras.py -k offline_install`
- A8: `python3 -m pytest -q tests/test_readme_install.py`
- A9: `git status --porcelain -- forgel_code`
- A10: `python3 -m pytest -q`
- Command: `python3 -m pytest -q`

## Acceptance Criteria

- **AC-1**: A1. `pyproject.toml` declares exactly one extra, `test`, containing one lower-bounded `pytest` requirement with no upper cap, and `[project] dependencies` is still `[]`.
- **AC-2**: A2. Building a wheel from the tree yields a `METADATA` containing both `Provides-Extra: test` and `Requires-Dist: pytest...; extra == "test"`.
- **AC-3**: A3. A test asserts that the pytest requirement in the wheel `METADATA` equals the requirement declared in `pyproject.toml`, so the two cannot drift.
- **AC-4**: A4. The sdist `PKG-INFO` built from the same tree carries the same `Provides-Extra` and pytest `Requires-Dist` lines as the wheel `METADATA`.
- **AC-5**: A5. Changing the pytest requirement in a copied `pyproject.toml` changes the emitted metadata accordingly, proving the backend has a single source for the extra.
- **AC-6**: A6. With `tomllib` made unavailable, the backend still emits the same `Provides-Extra`/`Requires-Dist` lines and still declares no build requirement.
- **AC-7**: A7. An offline `pip install` of the local tree with the `test` extra and `--no-deps` exits 0 without network access.
- **AC-8**: A8. `README.md` shows installing with the `test` extra followed by `python -m pytest -q`, keeps `python -m unittest discover -s tests` as the no-install path, and contains no editable-install instruction.
- **AC-9**: A9. `git status --porcelain -- forgel_code` is empty for the change: no file under `forgel_code/` is touched.
- **AC-10**: A10. `python3 -m pytest -q` exits 0 from a clean checkout; no test is deleted, skipped or weakened.

## Scope Boundaries

- `pyproject.toml`: add `[project.optional-dependencies]` with the single extra `test`.
- `_build_backend.py`: read the `test` extra from `pyproject.toml` and emit `Provides-Extra` and `Requires-Dist` lines in `_metadata()`.
- `_build_backend.py`: in-tree fallback parser for the `[project.optional-dependencies]` table shape when `tomllib` is unavailable (Python 3.9/3.10).
- `README.md`: rewrite the `## Tests` section to install with the `test` extra and run `python -m pytest -q`, keeping the no-install `unittest discover` path.
- New tests (e.g. `tests/test_extras.py`) for the pyproject declaration, wheel METADATA, sdist PKG-INFO, single-source behaviour, fallback parser and the offline `[test]` install.
- `tests/test_readme_install.py`: relax the doc guard exactly as far as the new README needs (a `pip install` line with `[test]` inside the `## Tests` section), keeping every other guard and adding an explicit no-editable-install assertion.
- `tests/test_packaging.py`: keep the `dependencies = []` assertion valid against the extended `pyproject.toml`.
- Changing any file under `forgel_code/`: client behaviour and its engine calls stay byte-identical.
- Changing `install.sh`, its one-command install path, its flags or variables.
- Adding a `pipx` line, a virtualenv recipe, a `--user` recipe or any new main installation path to the README.
- Adding a runtime dependency: `[project] dependencies` stays empty.
- Implementing PEP 660 editable installs in the backend.
- Adding `setuptools`, `flit`, `hatchling`, `tomli` or any other third-party build dependency.
- Widening the extra set beyond the single `test` extra (no `dev`, `docs`, `lint` extras).
- Changing the version scheme, the `Metadata-Version` upgrade beyond what the emitted fields require, or the sdist/wheel layout.
- Changing how the existing tests are invoked by CI or by `make`.

## Risks

- Conflict with the existing documentation guard: `tests/test_readme_install.py::assert_no_alternative_main_path` rejects any `pip install` line outside the Windows line, so the README change required here cannot land without editing that guard. The scope therefore includes relaxing exactly that rule for the `## Tests` section; a contributor who edits only `README.md` will see the suite go red and may be tempted to weaken the guard wholesale instead of narrowing it.
- Over-relaxing the guard would let a second main installation path into the README; the narrowing must be keyed to the `## Tests` section and to a line carrying `[test]`, and a fresh editable-install assertion must be added.
- Parsing `pyproject.toml` inside the build backend reintroduces a TOML parser on Python 3.9/3.10. A hand-written parser is easy to under-implement (multi-line arrays, inline comments, single quotes) and easy to over-implement; the fallback must be tested against the real file, not a toy fixture.
- If the fallback parser silently returns an empty extra, the wheel would still build but without `Provides-Extra: test`, and an offline `pip install .[test]` would fail with 'does not provide the extra'; the single-source and drift tests are what catch this, so they must run before the install test.
- Importing the backend module at test time executes it; caching the parsed extras in a module-level constant is fine, but a stale cache would hide a changed `pyproject.toml`. A test that rewrites a copied `pyproject.toml` must reload the backend for that copy.
- The offline install test shells out to pip; environment leakage (`PIP_INDEX_URL`, `PIP_FIND_LINKS`, a warm cache, a developer `PIP_CONFIG_FILE`) could make it pass with network access or fail without it. The clean-environment helper and `--no-index --no-cache-dir` are required, not optional.
- `pip install .[test] --no-deps` still prints a warning-free success only if the extra is declared; if the metadata declares it but the requirement string is malformed, pip errors instead, which would surface as a false negative. The test asserts the exit code and, on failure, includes stdout/stderr like the existing installer tests do.
- Running the new tests under `python3 -m pytest -q` requires pytest to be present in the runner environment; that is the point of the extra, but the pre-existing `unittest discover` path must keep working with the new test modules so the suite is not made dependent on pytest alone.
- Adding `[project.optional-dependencies]` below `dependencies = []` must not disturb `tests/test_packaging.py::test_pyproject_declares_the_in_tree_backend`, which greps for the literal `dependencies = []`.

## Open Questions

- None.

## Affected Files

- pyproject.toml
- _build_backend.py
- README.md
- tests/test_extras.py (new)
- tests/test_readme_install.py
- tests/test_packaging.py

## Assumptions

- The lower bound is `pytest>=7` unless the contributor picks another `>=` value; the exact number is reversible and only the shape (lower bound, no cap) is binding.
- The extra requirement marker is spelled `extra == "test"` with double quotes and one space after the requirement and before the `;`, matching the acceptance text quoted from the intent.
- `Metadata-Version` stays `2.1`; no upgrade is needed because both new field names exist there.
- The README examples reference a wheel path or the tagged git URL; either literal satisfies R8, and the task picks one consistent with the existing `v0.1.0`/`v0.1.1` tags already used in the file.
- There is no `pipx` line in today's README and the doc guard forbids one, so 'the optional `pipx` line is left unchanged' means: do not add one.
- The offline install test reuses the interpreter-selection and clean-environment helpers already present in `tests/test_install.py` (or copies the same shape) instead of assuming the runner interpreter owns pip.
- `pip` is available in the test environment, as `tests/test_install.py` already relies on it.

## Related Documents

- FORGEL.md
- AGENTS.md
- README.md
- pyproject.toml
- _build_backend.py
- install.sh
- tests/test_packaging.py
- tests/test_readme_install.py
- tests/test_install.py

## Revision History

- v1: initial specification for declaring the `test` extra in `pyproject.toml`, publishing it from the in-tree backend and documenting it in the README.

## External Dependencies

- **pytest** — mode `direct`; interface: Run the repository test suite with `python3 -m pytest -q`; the `test` extra declares pytest with a lower-bound requirement, and the backend republishes that same requirement in wheel metadata.; docs: https://docs.pytest.org/en/stable/ ; https://peps.python.org/pep-0440/#version-specifiers; evidence: Repository `environment.yaml` is the build/commands/env contract; `README.md` documents the `## Tests` path; `tests/` is the local test suite; the acceptance command is `python3 -m pytest -q`.
- **pip** — mode `direct`; interface: Drive the real pip CLI for the offline install test: `python3 -m pip install --no-index --no-build-isolation --no-deps "<local tree>[test]"`; the build/wheel path also uses pip to exercise the local backend.; docs: https://pip.pypa.io/en/stable/cli/pip_install/ ; https://pip.pypa.io/en/stable/topics/dependency-resolution/; evidence: `environment.yaml` supplies the local Python/pip toolchain; the repository tests invoke `python3 -m pip` directly with network-disabling and no-build-isolation flags; pip reads the backend-prepared metadata to decide whether the `test` extra exists.
- **PEP 621 `[project.optional-dependencies]` and core metadata fields `Provides-Extra` / `Requires-Dist`** — mode `direct`; interface: `pyproject.toml` records `[project.optional-dependencies].test`; `_build_backend.py` parses that table and emits `Provides-Extra: test` plus `Requires-Dist: pytest...; extra == "test"` into METADATA/PKG-INFO.; docs: https://peps.python.org/pep-0621/#optional-dependencies ; https://packaging.python.org/en/latest/specifications/core-metadata/#provides-extra-multiple-use ; https://packaging.python.org/en/latest/specifications/core-metadata/#requires-dist-multiple-use; evidence: `pyproject.toml` is the declared source for project metadata, including the empty `[project] dependencies` and the new `test` extra; `_build_backend.py` is the local metadata emitter used to build the wheel and sdist.
- **TOML (and the `tomllib` module)** — mode `direct`; interface: Use stdlib `tomllib.load` on Python 3.11+; on Python 3.9/3.10, use an in-tree fallback parser for the limited `[project.optional-dependencies]` table shape (`dict[str, list[str]]`) rather than adding a build dependency.; docs: https://docs.python.org/3/library/tomllib.html ; https://toml.io/en/v1.0.0; evidence: `pyproject.toml` is TOML and declares `requires-python = ">=3.9"`, so Python 3.9/3.10 may lack `tomllib`; `_build_backend.py` must therefore carry the limited in-tree fallback. Python 3.11+ provides `tomllib` as a standard-library module.
- **PEP 517 build-backend hooks (`prepare_metadata_for_build_wheel`, `build_wheel`, `build_sdist`)** — mode `direct`; interface: pip invokes the in-tree `_build_backend.py` hooks in-process; `prepare_metadata_for_build_wheel` must advertise the `test` extra before installation, and `build_wheel`/`build_sdist` must emit consistent metadata.; docs: https://peps.python.org/pep-0517/#prepare-metadata-for-build-wheel; evidence: `pyproject.toml` uses the local build backend; `_build_backend.py` implements the wheel/sdist metadata generation; the tests build a wheel from the tree and inspect its METADATA for `Provides-Extra: test` and the pytest `Requires-Dist` line.


## Summary

Fixed the retry's only remaining failure: the task's acceptance commands filter with `-k 'drift or single_source'`, `-k single_source` and `-k offline_install`, but the tests added in the previous attempt were named without those tokens, so pytest deselected all 20 tests and exited 5. Renamed the affected tests (`test_no_drift_between_pyproject_and_wheel_metadata`, `test_single_source_rewriting_the_table_changes_the_metadata`, `test_single_source_rewriting_the_table_changes_the_sdist`, `test_offline_install_exits_zero`, `test_offline_install_metadata_declares_the_extra`, `test_pyproject_declares_exactly_one_extra_named_test`) so every acceptance selector matches, and added a second single-source test that proves the sdist PKG-INFO follows a rewritten extras table as well. The already-finished work is unchanged: `pyproject.toml` declares exactly one `test` extra (`pytest>=7`, no cap) with `[project] dependencies = []`; `_build_backend.py` reads that table from `pyproject.toml` (stdlib `tomllib`, plus an in-tree parser for the extras-table shape on Python 3.9/3.10) and emits `Provides-Extra: test` and `Requires-Dist: pytest>=7; extra == "test"` from the one `_metadata()` text that feeds the wheel METADATA, the sdist PKG-INFO and `prepare_metadata_for_build_wheel`; `README.md` shows the `[test]` install plus `python -m pytest -q` and keeps the no-install `unittest discover` path; `tests/test_readme_install.py` narrows the pip-install guard to one `[test]` line inside `## Tests` and adds a no-editable-install assertion. Verified: `python3 -m pytest -q tests/test_extras.py -k 'drift or single_source'` (3 passed), `-k single_source` (2 passed), `-k offline_install` (2 passed), `-k 'pyproject or wheel or sdist or fallback or single_source'` (20 passed), `python3 -m pytest -q` (165 passed, 137 subtests), `python3 -m unittest discover -s tests` (165 tests OK), and `git status --porcelain -- forgel_code` is empty.

## Files Changed

- `README.md`
- `_build_backend.py`
- `pyproject.toml`
- `tests/test_extras.py`
- `tests/test_readme_install.py`

## Commands

- `["python3", "-m", "pytest", "-q", "tests/test_extras.py", "-k", "drift or single_source"]` → exit 0
- `["python3", "-m", "pytest", "-q", "tests/test_extras.py", "-k", "offline_install"]` → exit 0
- `["python3", "-m", "pytest", "-q"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "pytest", "-q", "tests/test_extras.py", "-k", "pyproject or wheel or sdist or fallback or single_source"]` → exit 0
- `["git", "status", "--porcelain", "--", "forgel_code"]` → exit 0
- `["python3", "-m", "pytest", "-q", "tests/test_readme_install.py", "tests/test_packaging.py"]` → exit 0
- `["python3", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
...................................................... [ 32%]
................................................. [ 62%]
............................................................ [ 98%]
..                                                           [100%]
165 passed, 137 subtests passed in 45.22s

```

## Actions

- read_file: tests/test_extras.py
- write_file: tests/test_extras.py
- read_file: _build_backend.py
- run: ['python3', '-m', 'pytest', '-q', 'tests/test_extras.py', '-k', 'drift or single_source']
- run: ['python3', '-m', 'pytest', '-q', 'tests/test_extras.py', '-k', 'offline_install']
- run: ['python3', '-m', 'pytest', '-q']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: README.md
- run: ['python3', '-m', 'pytest', '-q', 'tests/test_extras.py', '-k', 'pyproject or wheel or sdist or fallback or single_source']
- run: ['git', 'status', '--porcelain', '--', 'forgel_code']
- run: ['python3', '-m', 'pytest', '-q', 'tests/test_readme_install.py', 'tests/test_packaging.py']
- read_file: tests/test_readme_install.py
