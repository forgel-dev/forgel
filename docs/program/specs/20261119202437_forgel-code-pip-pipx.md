# Task Spec: Установка Forgel Code обычным pip, pipx — необязательный вариант

## Document Information

| Field | Value |
|-------|-------|
| Feature | Установка Forgel Code обычным pip, pipx — необязательный вариант |
| Project | — |
| Task | `20261119202437_forgel-code-pip-pipx` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-19T20:25:35+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

In the `code` repository the README's primary installation path is not a plain pip install: pipx is presented as the main way, the install command is not pinned to a fixed revision, the update section does not explain how to move to a new pinned revision when the version number is unchanged, nothing explains where pip puts the `forgel-code` executable or how to fix PATH, and no fallback `python3 -m forgel_code` launch is documented. There are also no tests guarding the installation documentation or proving that a plain, offline pip install from the local source tree yields a working `forgel-code` command and module entry point.

**Outcome:** The README in the `code` repository documents plain pip (bundled with Python) as the primary installation path, with the first install command being `python3 -m pip install` pinned to an exact revision, showing both virtual-environment and `--user` variants, explaining where the `forgel-code` script lands, how to fix PATH and the `python3 -m forgel_code` fallback. pipx appears exactly once, after the pip instructions, explicitly marked optional. The update section describes installing a newer pinned revision with `--upgrade`/`--force-reinstall`, including an unchanged version number with a different commit. Existing constraints (no build dependencies, no network at build time, no editable install, engine reachable via PATH or `--engine`/`$FORGEL_ENGINE`) are preserved. Two automated tests enforce this: a documentation test that fails if the first install command stops being plain pip or if pipx appears earlier or without an 'optional' marker, and an installation test that installs the client with plain pip into a temporary directory without network access and verifies that both `forgel-code --version` and `python3 -m forgel_code --version` print the installed version with exit code 0. No file under `forgel_code/` changes.

## Goals

- Make plain pip (bundled with Python) the documented primary installation path for Forgel Code, with a pinned revision as the first command.
- Cover virtual-environment and `--user` installs, executable location, PATH fixes and the `python3 -m forgel_code` fallback.
- Rewrite the update section around pip with a newer pinned revision, including unchanged version numbers.
- Demote pipx to a single optional line placed after the pip instructions.
- Add a documentation test and an offline pip installation test that enforce the above.
- Leave client package behaviour and `forgel_code/` files unchanged.

## Non-Goals

- Any change to files under `forgel_code/` (package code, CLI, engine invocation, session handling, rendering).
- Changing engine calls, the stub contract or client runtime behaviour.
- Adding new client features, flags or commands beyond the existing `--version`.
- Making pipx the primary or an equally presented installation path.
- Publishing a release, changing version numbers or changing package metadata/publish configuration beyond what the install docs and tests need.
- Introducing build-time dependencies, network fetching or editable installs.
- Documenting installation for other platforms' package managers (apt/brew/etc.).
- Modifying the engine repository or the `forgel` engine itself.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The interactive client moves to a separate public repository in the same organization as the engine. | D-001, User, 2026-11-16 21:14 |
| — | The second repository is public and lives in the same organization as the first (`forgel-dev`). | D-005, User, 2026-11-16 21:14 |
| — | The client is a thin UI over the engine's parameterized commands; model access, sandbox, QA, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |

## Functional Requirements

- **FR-1**: `README.md` install section's first command block contains a `python3 -m pip install` command pinned to an exact revision (tag, commit hash or exact version); no floating branch is used as the default.
- **FR-2**: The first install command block does not require pipx and can be executed with only Python and pip.
- **FR-3**: README shows installing inside a virtual environment (create/activate plus `python3 -m pip install`).
- **FR-4**: README shows a `--user` install for a system Python where no virtual environment is created.
- **FR-5**: README states where the `forgel-code` executable is placed (virtual environment `bin`/`Scripts` directory or pip's user scripts directory) and how to add that directory to PATH, including how to locate it if unknown.
- **FR-6**: README documents the fallback launch `python3 -m forgel_code` and includes a version check example (e.g. `python3 -m forgel_code --version`).
- **FR-7**: README's update section describes upgrading by installing a newer pinned revision with `python3 -m pip install --upgrade` and/or `--force-reinstall`, and explicitly covers the case where the version number is unchanged but the commit differs (forcing reinstall of the pinned commit).
- **FR-8**: `pipx` appears at most once in `README.md`, is explicitly marked as optional (an isolation alternative), and appears after the pip installation instructions.
- **FR-9**: README keeps the existing stated constraints: build needs no dependencies and no network, editable installation is not supported, and the `forgel` engine must be available via PATH or `--engine`/`$FORGEL_ENGINE`.
- **FR-10**: A documentation test checks that the first install command in the README install section is a plain `python3 -m pip install` (or `python -m pip install`) command and fails if it is not.
- **FR-11**: The documentation test checks that if `pipx` appears in `README.md`, it appears after the pip instructions and within an explicitly optional-marked line, failing otherwise.
- **FR-12**: An installation test creates a temporary target directory, installs the local source tree with plain pip in a no-network configuration (e.g. `--no-index`/`--no-build-isolation` as appropriate to the existing build backend), and asserts exit code 0.
- **FR-13**: The installation test asserts that the installed `forgel-code --version` prints the installed version and exits 0.
- **FR-14**: The installation test asserts that `python3 -m forgel_code --version` (run against the installed target) prints the installed version and exits 0.
- **FR-15**: No file under `forgel_code/` is modified by this task.
- **FR-16**: The existing test suite in `tests/` continues to pass unchanged.

## Technical Requirements

- Only documentation (`README.md`) and test files may change; `forgel_code/` is untouched.
- New tests must run under the project's existing test runner and environment without extra third-party dependencies.
- The installation test must not access the network: it installs from the local source tree with no index and without fetching build requirements.
- The build backend `_build_backend.py` must keep working offline; tests must not introduce build isolation that requires downloads unless the backend already supports it offline.
- Python 3 with the bundled pip and `venv`/`--user` are the only prerequisites assumed for the documented path.
- Existing README constraints (dependency-free build, no network, no editable install, engine via PATH/`--engine`/`$FORGEL_ENGINE`) must not be removed or contradicted.
- The `forgel-code` behaviour and CLI surface are unchanged.

## User Stories

- As a Python user with only the bundled pip, I want a plain `python3 -m pip install` command pinned to a known revision so that I can install Forgel Code without extra tools.
- As a user installing into a virtual environment, I want the README to show venv creation and activation so that I keep my system Python clean.
- As a user on a system Python without a venv, I want a `--user` install variant so that I can install without root or a virtual environment.
- As a user whose shell cannot find `forgel-code`, I want to know where pip put the script and how to fix PATH so that I can run the client.
- As a user with a broken PATH, I want the `python3 -m forgel_code` fallback so that I can still run the client.
- As a user upgrading, I want pip-based update instructions covering an unchanged version number with a new commit so that I actually get the new code.
- As a maintainer, I want tests that fail if the README regresses to pipx-first or if a plain offline pip install stops working so that installation stays reliable.

## Tests

- The first command block in the README installation section contains `python3 -m pip install` with a pinned revision and does not require pipx.: `python3 -m pytest tests/test_readme_install.py -q`
- README shows both a virtual-environment install and a `--user` install.: `python3 -m pytest tests/test_readme_install.py -q`
- README explains where to find the `forgel-code` executable, how to fix PATH, and how to run the client via `python3 -m forgel_code`.: `python3 -m pytest tests/test_readme_install.py -q`
- pipx is mentioned at most once, marked optional, and positioned after the pip instructions.: `python3 -m pytest tests/test_readme_install.py -q`
- The update section describes moving to a newer pinned revision via pip, including the unchanged-version-number case.: `python3 -m pytest tests/test_readme_install.py -q`
- The documentation test passes and fails as designed if the first install command stops being plain pip or if pipx appears earlier or without an optional marker.: review
- The installation test passes: in a temporary directory without network, the client installs with plain pip, and `forgel-code --version` and `python3 -m forgel_code --version` print the installed version with exit code 0.: `python3 -m pytest tests/test_install.py -q`
- The existing client test suite passes with no behaviour change.: `python3 -m pytest tests -q`
- The diff contains no changes to files under `forgel_code/`.: `git diff --name-only HEAD~1 -- forgel_code`
- Command: `python3 -m pytest -q`

## Acceptance Criteria

- **AC-1**: The first command block in the README installation section contains `python3 -m pip install` with a pinned revision and does not require pipx.
- **AC-2**: README shows both a virtual-environment install and a `--user` install.
- **AC-3**: README explains where to find the `forgel-code` executable, how to fix PATH, and how to run the client via `python3 -m forgel_code`.
- **AC-4**: pipx is mentioned at most once, marked optional, and positioned after the pip instructions.
- **AC-5**: The update section describes moving to a newer pinned revision via pip, including the unchanged-version-number case.
- **AC-6**: The documentation test passes and fails as designed if the first install command stops being plain pip or if pipx appears earlier or without an optional marker.
- **AC-7**: The installation test passes: in a temporary directory without network, the client installs with plain pip, and `forgel-code --version` and `python3 -m forgel_code --version` print the installed version with exit code 0.
- **AC-8**: The existing client test suite passes with no behaviour change.
- **AC-9**: The diff contains no changes to files under `forgel_code/`.

## Scope Boundaries

- Rewrite the installation section of `README.md` in the `code` repository so plain pip is the primary path.
- First install command must be a `python3 -m pip install ...` form pinned to an exact revision (tag, commit or exact version), not a floating branch.
- Show a virtual-environment install variant and a `--user` variant for a system Python without a venv.
- Explain where pip writes the `forgel-code` executable (venv `bin`/`Scripts` directory or the pip user scripts directory) and how to add it to PATH.
- Document the fallback `python3 -m forgel_code` invocation, including a version check example.
- Rewrite the update section around `python3 -m pip install --upgrade` / `--force-reinstall` with a newer pinned revision, including the same-version-different-commit case.
- Reduce pipx to at most one line, marked optional for isolation, placed after the pip instructions.
- Preserve the README's existing constraints: dependency-free and network-free build, no editable install, engine `forgel` reachable via PATH or `--engine`/`$FORGEL_ENGINE`.
- Add a documentation test asserting that the first install command in the install section is plain pip and that pipx appears only later and marked optional.
- Add an installation test that, offline, installs the client with plain pip from the local source tree into a temporary directory and checks `forgel-code --version` and `python3 -m forgel_code --version`.
- Any change to files under `forgel_code/` (package code, CLI, engine invocation, session handling, rendering).
- Changing engine calls, the stub contract or client runtime behaviour.
- Adding new client features, flags or commands beyond the existing `--version`.
- Making pipx the primary or an equally presented installation path.
- Publishing a release, changing version numbers or changing package metadata/publish configuration beyond what the install docs and tests need.
- Introducing build-time dependencies, network fetching or editable installs.
- Documenting installation for other platforms' package managers (apt/brew/etc.).
- Modifying the engine repository or the `forgel` engine itself.

## Risks

- The offline installation test may fail if pip attempts build isolation and tries to download build requirements; mitigation is `--no-build-isolation`/`--no-index` matching the dependency-free backend, but an incorrect flag choice could still break it.
- Asserting the README's pinned revision in a test could make the test brittle; the documentation test must assert the shape (plain pip first, pinned, pipx after/optional) rather than an exact URL.
- The `pipx` 'appears at most once' check may conflict with an explicit `pipx` mention inside a comparison table or an existing mention elsewhere in the README; placement and counting rules must be defined precisely in the test.
- `--user` installs cannot be safely executed in all CI environments, so that acceptance criterion is verified by review only, leaving a documentation-only guarantee.
- `python3 -m forgel_code --version` depends on `__main__.py` forwarding arguments; if it does not, the requirement conflicts with 'no changes under `forgel_code/`', which would force a redesign or an open question.
- The milestone goal says pipx is optional while the current README may lead with pipx; if upstream docs or links elsewhere still lead with pipx, the change is incomplete.

## Open Questions

- None.

## Affected Files

- README.md
- tests/ (new documentation test file, e.g. tests/test_readme_install.py)
- tests/ (new installation test file, e.g. tests/test_install.py)
- pyproject.toml (only if test configuration or markers need registering; no packaging behaviour change)

## Assumptions

- The `forgel_code/__main__.py` module entry point exists and supports `--version`, so `python3 -m forgel_code --version` works (to be confirmed by the test).
- A pinned revision in README can be expressed as an exact VCS URL/ref (e.g. `git+https://...@<tag-or-commit>`) or an exact version from an index; the chosen form is the one the installation test can exercise offline from the local tree.
- The offline installation test installs from the local source path (`.`/source directory) while the README shows the pinned remote form; the test verifies the pip mechanism, not the remote revision.
- The documentation test parses `README.md` structurally (headings/fenced code blocks) rather than human judgement.
- `--user` installs are testable by review of the README only, not executed in CI, to avoid mutating the runner user environment.

## Related Documents

- README.md
- pyproject.toml
- _build_backend.py
- forgel_code/__main__.py
- tests/test_packaging.py
- AGENTS.md

## Revision History

- v1 — initial specification for the plain-pip installation milestone task.

## External Dependencies

- **pip (plain pip bundled with Python)** — mode `direct`; interface: `python3 -m pip install` for normal installs, plus `--user`, `--upgrade`, `--force-reinstall`, `--target`, `--no-index`, and `--no-build-isolation`; the install test uses local-source, offline pip installation into a temporary target.; docs: https://pip.pypa.io/en/stable/cli/pip_install/; evidence: The repository environment provides Python 3 with its bundled pip, invoked as `python3 -m pip`. The README install/update sections and the installation test use that local pip CLI with a pinned revision and with `--target`, `--no-index`, and `--no-build-isolation` for an offline local-source install.
- **Python standard library `venv`** — mode `direct`; interface: `python3 -m venv <dir>` creates the documented isolated environment; the installed client is then at `<dir>/bin/forgel-code`, with activation via `<dir>/bin/activate`.; docs: https://docs.python.org/3/library/venv.html; evidence: `venv` is part of the Python 3 standard library used by the project. The README’s primary installation path can therefore show `python3 -m venv .venv` and use `.venv/bin/forgel-code`, without any external package or service.
- **PEP 517/518 build backend interface** — mode `direct`; interface: pip builds the local source tree through the project’s in-tree backend declared by `pyproject.toml`; tests call pip with `--no-build-isolation --no-index`, so the repository’s `_build_backend.py` is driven directly and no network or extra build dependency is needed.; docs: https://peps.python.org/pep-0517/; evidence: `pyproject.toml` declares the project build backend and `_build_backend.py` implements the PEP 517 hooks used by pip. The dependency specification explicitly identifies this local backend as the path pip uses to build the wheel offline.
- **`forgel` engine binary (external program)** — mode `stub`; interface: The client resolves the engine from `PATH`, or from `--engine <path>` / `FORGEL_ENGINE`. Install tests use `forgel-code --version` and `python3 -m forgel_code --version`, so a deterministic fake `forgel` executable is sufficient for PATH/option-resolution tests; tests must not require real engine semantics.; docs: README.md, install/engine requirements section; evidence: README.md documents the existing constraint that the `forgel` engine must be available through `PATH` or supplied via `--engine`/`$FORGEL_ENGINE`. The engine is not vendored in the repository and no real engine binary is declared by the environment contract, so tests must use a fake executable rather than the real engine.
  ```
  #!/usr/bin/env python3
  import json
  import sys
  
  
  def main(argv):
      if "--version" in argv or "-V" in argv:
          print("forgel 0.0.0-stub")
          return 0
      if "--help" in argv or "-h" in argv:
          print("forgel stub")
          return 0
      print(json.dumps({"diagnostics": [], "status": "ok"}, sort_keys=True))
      return 0
  
  
  if __name__ == "__main__":
      raise SystemExit(main(sys.argv[1:]))
  ```
