# Feature: Declare test dependencies in pyproject.toml

## Document Information

| Field | Value |
|-------|-------|
| Feature | Declare test dependencies in pyproject.toml |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-20T00:28:49+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

Declare the client's test dependencies as a `test` extra in pyproject.toml and make the in-tree build backend emit them into the wheel metadata, so `pip install "forgel-code[test]"` plus `python -m pytest -q` works without installing packages by hand. Runtime dependencies stay empty, client code and engine calls are untouched, and the README's test section tells the user to install the extra instead of a bare pytest.

## Goals

- `pyproject.toml` gains a `[project.optional-dependencies]` table with a single extra named `test` whose only entry is `pytest` with a lower-bound version constraint and no upper cap.
- `[project] dependencies` stays empty: an ordinary install of the client still pulls nothing at runtime.
- `_build_backend.py` must emit into the built wheel's METADATA both `Provides-Extra: test` and a `Requires-Dist` line for pytest carrying the `extra == "test"` marker.
- The extra requirements must have a single source: the backend reads the `test` extra from `pyproject.toml` instead of repeating the pytest version as a second literal. When `tomllib` is unavailable (Python 3.9/3.10, which `requires-python = ">=3.9"` still allows) the backend must fall back to an in-tree parser for the limited table shape rather than adding a build dependency.
- The extra is also declared in the generated sdist/wheel metadata consistently with the wheel path, so an sdist build of the same tree produces the same extras.
- README's test section is updated to: install the client with the `test` extra (`python3 -m pip install "<wheel path or git url with tag>[test]"`), then run `python -m pytest -q`; running `python -m unittest discover -s tests` from a checkout without installation remains documented as the no-install path.
- README must not propose an editable install (`pip install -e`); editable installs are unsupported in this repository.
- The one-command installer and the optional `pipx` line are left unchanged; test dependencies are unrelated to installing the client.
- No file under `forgel_code/` changes: the client's behaviour and its calls to the engine stay identical.
- New tests cover: the `test` extra is present in `pyproject.toml`; the built wheel METADATA contains `Provides-Extra: test` and the pytest `Requires-Dist` line with the extra marker; the pytest requirement recorded in METADATA matches the one declared in `pyproject.toml`; an offline install of the local tree with `[test]` (`--no-index --no-build-isolation --no-deps`) succeeds.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- **FR-1**: `pyproject.toml` gains a `[project.optional-dependencies]` table with a single extra named `test` whose only entry is `pytest` with a lower-bound version constraint and no upper cap.
- **FR-2**: `[project] dependencies` stays empty: an ordinary install of the client still pulls nothing at runtime.
- **FR-3**: `_build_backend.py` must emit into the built wheel's METADATA both `Provides-Extra: test` and a `Requires-Dist` line for pytest carrying the `extra == "test"` marker.
- **FR-4**: The extra requirements must have a single source: the backend reads the `test` extra from `pyproject.toml` instead of repeating the pytest version as a second literal. When `tomllib` is unavailable (Python 3.9/3.10, which `requires-python = ">=3.9"` still allows) the backend must fall back to an in-tree parser for the limited table shape rather than adding a build dependency.
- **FR-5**: The extra is also declared in the generated sdist/wheel metadata consistently with the wheel path, so an sdist build of the same tree produces the same extras.
- **FR-6**: README's test section is updated to: install the client with the `test` extra (`python3 -m pip install "<wheel path or git url with tag>[test]"`), then run `python -m pytest -q`; running `python -m unittest discover -s tests` from a checkout without installation remains documented as the no-install path.
- **FR-7**: README must not propose an editable install (`pip install -e`); editable installs are unsupported in this repository.
- **FR-8**: The one-command installer and the optional `pipx` line are left unchanged; test dependencies are unrelated to installing the client.
- **FR-9**: No file under `forgel_code/` changes: the client's behaviour and its calls to the engine stay identical.
- **FR-10**: New tests cover: the `test` extra is present in `pyproject.toml`; the built wheel METADATA contains `Provides-Extra: test` and the pytest `Requires-Dist` line with the extra marker; the pytest requirement recorded in METADATA matches the one declared in `pyproject.toml`; an offline install of the local tree with `[test]` (`--no-index --no-build-isolation --no-deps`) succeeds.

## Technical Requirements

- Python >=3.9 must remain installable: the backend cannot assume `tomllib` exists.
- The build backend keeps `requires = []`: no setuptools, no tomli, no network access during a build.
- Test runs must not require network access.
- Do not weaken or remove existing tests to make the new ones pass.
- Committed artifacts, commit messages and documentation are in English; commits are signed off with `-s`.
- No tool attribution lines or session references in commits or pull requests.

## User Stories

- None stated.

## Tests

- None stated.
- Command: `python3 -m pytest -q`

## Acceptance Criteria

- **AC-1**: `python3 -m pytest -q` exits 0 from a clean checkout with the existing test runner.
- **AC-2**: Building a wheel from the tree yields a METADATA file containing `Provides-Extra: test` and `Requires-Dist: pytest…` with `extra == "test"`.
- **AC-3**: A test asserts that the pytest requirement in the wheel METADATA equals the requirement declared in `pyproject.toml`, so the two cannot drift.
- **AC-4**: An offline pip install of the local tree with the `test` extra and `--no-deps` exits 0 without network access.
- **AC-5**: README shows installing with the `test` extra followed by `python -m pytest -q`, and contains no editable-install instruction.
- **AC-6**: `git diff --name-only` for the change touches no file under `forgel_code/`.
- **AC-7**: Existing tests continue to pass; no test is deleted, skipped or weakened.

## Scope Boundaries

- Python >=3.9 must remain installable: the backend cannot assume `tomllib` exists.
- The build backend keeps `requires = []`: no setuptools, no tomli, no network access during a build.
- Test runs must not require network access.
- Do not weaken or remove existing tests to make the new ones pass.
- Committed artifacts, commit messages and documentation are in English; commits are signed off with `-s`.
- No tool attribution lines or session references in commits or pull requests.

## Risks

- None stated.

## Open Questions

- None.

## Affected Files

- Not identified yet.

## Assumptions

- The extra is named `test`; no `dev` extra with linters is added, since the user asked only for test dependencies.
- The pytest constraint is a lower bound (`pytest>=7`) with no upper cap, matching the request for a lower bound without a ceiling.
- The single source of the extras is `pyproject.toml`; the backend derives the metadata from it rather than repeating the version.
- The README's existing Tests section is the place to document the extra; the rest of the install documentation is not restructured.
- The existing offline-install test style (`--no-index --no-build-isolation --no-deps` into a temporary `--target`) is the pattern for the new extras test.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-20 — Initial request recorded.
