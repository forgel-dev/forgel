# Agent Run: Declare the minimum supported engine version in the client

- Task: `20261124152248_declare-the-minimum-supported-engine-ver`
- Status: `done`
- Repository: `code`
- Steps: 73
- Finished: 2026-11-25T15:09:08+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The minimum supported engine version keeps the value already declared and enforced by the installer (`0.1.0`); the engine has no released version yet, so the value is selected from the existing declaration rather than from a release.
- The machine-readable report is the client's own `--version --json` output, one JSON object on stdout with the keys `forgel_code_version` and `minimum_engine_version`, capturable by a script without entering the interactive session.
- `--version` is honoured when it appears before any command word, so the client's own version report takes precedence over command parsing; a `--version` appearing after a command word belongs to that command.
- The client version in the report is read from the single `__version__` declaration, which the build backend already packs into the distribution metadata.
- The startup check from the earlier task (which compares an installed engine against this declaration) is not part of this change; this change only declares the floor and reports it.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 73
- Estimated input tokens (all calls): 3198370
- Provider input/output tokens: 3349219 / 165215
- Provider cache hit/miss tokens: 3282688 / 66531
- Estimated prompt at the end: 63158 tokens
- State: not needed

## Specification (`docs/program/specs/20261124152248_declare-the-minimum-supported-engine-ver.md`)

# Task Spec: Declare the minimum supported engine version in the client

## Document Information

| Field | Value |
|-------|-------|
| Feature | Declare the minimum supported engine version in the client |
| Project | — |
| Task | `20261124152248_declare-the-minimum-supported-engine-ver` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

Forgel Code depends on the Forgel engine, but nothing in the client states which engine versions it supports. Without a declared floor, the installer and the startup check would each assume a threshold of their own, a too-old engine cannot be reliably recognised, and compatibility is implied rather than stated. The client also needs to be able to state that floor when no engine is present at all, because the installer must compare against it before anything is installed.

**Outcome:** The client declares one minimum supported engine version and reports it together with its own version in one stable machine-readable form that other tooling can consume. Producing that report succeeds when no engine is present and without contacting the network, so the installer and the startup check read the same declaration instead of restating it.

## Product Intent

Forgel and Forgel Code must install and run as one working pair: a compatibility floor declared by the client is what lets the pair be installed safely and lets a missing or too-old engine be reported with a clear, actionable message instead of a raw execution error.

## User Experience

A person or a script can ask the client which engine versions it supports at any moment, including on a machine where the engine was never installed, and gets one unambiguous answer that agrees with what the installer and the startup check enforce.

## Roadmap

—

## Goals

- State the client's minimum supported engine version once.
- Make the client's own version and that minimum readable together in a stable machine-readable form.
- Guarantee that reading them works with no engine installed and no network.

## Non-Goals

- Comparing an installed engine against the declared minimum or blocking startup on a mismatch; that is the startup check task.
- Installing, downloading or repairing anything.
- Changing how the client invokes the engine or restructuring existing operations.
- Explaining the floor in user-facing documentation; that is the documentation task.
- Negotiating version ranges or supporting several declared compatible ranges.
- Deciding or announcing engine release versions.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | D-002, user 2026-11-16 18:31 |
| — | The client's working name is Forgel Code, installed as forgel-code, following a Pareto 20/80 scope and importing nothing from the engine. | D-004, user accepted the proposal 2026-11-16 18:34 |
| — | Machine-readable engine commands come first, then the client work; client-facing operations are parameterized commands with optional single JSON object output. | D-006 and D-007, user accepted the proposal 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: The client declares exactly one minimum supported engine version value.
- **FR-2**: The declared minimum is a single concrete, well-formed version number that belongs to the client and is never inferred at run time from an installed engine, a remote service or the network.
- **FR-3**: The declared minimum is the earliest engine version that provides every engine operation the client relies on, and it is current with the engine versions that exist when the declaration is made.
- **FR-4**: The client produces one stable machine-readable report carrying both its own version and the declared minimum supported engine version, with each version unambiguous about which it is.
- **FR-5**: Producing the report completes with a normal success result when no engine is installed and without contacting the network.
- **FR-6**: Producing the report does not depend on any engine call, engine discovery or engine configuration being present or valid.
- **FR-7**: The client version in the report is the version of the installed client distribution, not a separately hand-maintained value.
- **FR-8**: The report is consumable by other tooling without interpreting human prose, and the client's human-readable version output still produces the same information as before.
- **FR-9**: The minimum supported engine version appears in exactly one place in the product; anything that needs it obtains it rather than restating the value.
- **FR-10**: The declaration and the report belong entirely to the client and require nothing from the engine to exist or run.

## User Stories

- As an operator installing Forgel Code, I want the client to state the oldest engine it supports, so that the installer can decide what to install without guessing a threshold.
- As a maintainer, I want that minimum declared once and reported in machine-readable form, so that the installer and the startup check can never disagree about it.
- As a user on a machine with no engine yet, I want to be able to read which engine versions the client supports, so that nothing about the declaration requires the engine to exist first.

## Acceptance Criteria

- **AC-1**: A machine-readable report produced by the client contains the client's own version and the declared minimum supported engine version at the same time.
- **AC-2**: The report is produced successfully on a machine with no engine installed and with the network unavailable.
- **AC-3**: The client version in the report equals the version of the installed client distribution.
- **AC-4**: The minimum supported engine version is a single well-formed version number and is the earliest engine version providing every engine operation the client relies on.
- **AC-5**: Review of the change confirms the minimum supported engine version is declared once, that no second copy of that value exists for any consumer, and that the installer and the startup check can both obtain it from the declaration.
- **AC-6**: The client's human-readable version output still produces the same information as before the change.
- **AC-7**: The client's full automated test suite passes with the change in place.

## Scope Boundaries

- Record the minimum supported engine version once, as part of the client.
- Expose the client's own version and the declared minimum supported engine version together in a stable machine-readable report.
- Make that report available when no engine is installed and without network access.
- Keep the declaration as the single value the installer and the startup check read.
- Preserve the client's existing human-readable version behaviour.
- Comparing an installed engine against the declared minimum or blocking startup on a mismatch; that is the startup check task.
- Installing, downloading or repairing anything.
- Changing how the client invokes the engine or restructuring existing operations.
- Explaining the floor in user-facing documentation; that is the documentation task.
- Negotiating version ranges or supporting several declared compatible ranges.
- Deciding or announcing engine release versions.

## Risks

- The engine has no release version yet, so the chosen minimum may need raising later; a wrong value either blocks working setups or lets unsuitable engines pass.
- A tempting shortcut is to ask the installed engine for its version to build the report, which would fail exactly in the no-engine situation this task must support.
- A second copy of the minimum could be introduced for the installer's convenience, re-creating the drift this task removes.
- Reworking the version output for machines could break the human-readable output that users and scripts already read.
- The startup check task may expect the declaration in a shape it cannot use; the report must expose both versions plainly so that task consumes it without redefining the value.
- The task borders the installer and startup check tasks; pulling either into this change would exceed one reviewable change.

## Open Questions

- None.

## Assumptions

- The machine-readable report is available without entering the client's interactive experience, so a script can obtain it directly.
- The report is machine-readable output a caller can capture and parse without prose.
- The declared minimum is chosen as the earliest engine version that provides every engine operation the client relies on; while the engine has no release version yet, the developer selects that value from the engine's documented operations and records it in the change report, and it is raised when the first engine release exists.
- The minimum is declared as part of the client's version information so that the report and the future startup check read it from the same declaration.
- Preserving the existing human-readable version behaviour is a preservation requirement, not a redesign opportunity.
- Both versions are reported as plain version numbers rather than as a comparison result, so the consumer decides how to compare them.

## Related Documents

- README.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md

## Revision History

- v1 — initial specification: declare the minimum supported engine version in the client and report it with the client version in a machine-readable form that works without an engine.
- v2 — removed process wording from the constraints and restated the declaration, the report and the preservation requirement as observable behaviour; acceptance otherwise unchanged.


## Summary

The client now exposes its own version together with one declared minimum supported engine version in a stable machine-readable report. `forgel_code/__init__.py` keeps the single `MIN_ENGINE_VERSION` declaration and gained `version_report()`, which returns both values from the client's own declaration. `forgel_code/cli.py` recognises the client's `--version` before any command is parsed and answers with either the unchanged human line (`forgel-code <version>`) or, with `--json`, one JSON object carrying `forgel_code_version` and `minimum_engine_version`; the report path touches no engine, no session, no timeout and no network. The human-readable output and every existing command path stay byte-identical. `CHANGELOG.md` records the new report under Unreleased/Added. A new test module `tests/test_version_report.py` checks both values in one report, distinct keys, the client version equalling the built distribution's version, a well-formed minimum, successful production with an unusable engine path and a PATH that resolves nothing, that no engine process is started, the unchanged human output, that only words before the command count as the version request, and that no other product module restates the minimum. The minimum `0.1.0` was chosen as the floor already declared and enforced by the shipped installer and startup check, since the engine has no released version yet. Full gate `python3 -m unittest discover -s tests` passes (378 tests, 0 failures); one earlier full run failed on two pre-existing installer timing tests that pass in isolation and in the following full run. `python -m pytest -q tests/test_version_report.py` passes (11 tests).

## Files Changed

- `CHANGELOG.md`
- `forgel_code/__init__.py`
- `forgel_code/cli.py`
- `tests/test_version_report.py`

## Commands

- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "forgel_code/cli.py"]` → exit 0
- `["git", "log", "--oneline", "-6"]` → exit 0
- `["git", "show", "--stat", "HEAD"]` → exit 0
- `["git", "log", "--oneline", "-S", "MIN_ENGINE_VERSION", "--", "forgel_code", "install.sh"]` → exit 0
- `["git", "log", "--oneline", "-S", "MIN_ENGINE_VERSION", "--", "forgel_code/__init__.py"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_version_report", "tests.test_cli", "tests.test_packaging"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_version_report", "tests.test_cli", "tests.test_cli_extra", "tests.test_packaging", "tests.test_cli_help_description"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_version_report", "tests.test_cli", "tests.test_cli_extra", "tests.test_packaging", "tests.test_cli_help_description"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_check_cleanup", "tests.test_install.InstallerBoundedCheckTest"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_version_report.py"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
..........................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 378 tests in 286.261s

OK

```

## Actions

- read_file: forgel_code/__init__.py
- read_file: forgel_code/cli.py
- read_file: pyproject.toml
- read_file: forgel_code/compat.py
- search_files: MIN_ENGINE_VERSION|min_engine_version|engine_min|--version @ .
- read_file: install.sh
- read_file: install.sh
- search_files: version @ tests/test_cli.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- search_files: 0\.0\.0|0\.1\.0|ENGINE = |compat @ tests
- search_files: requires engine|MIN_ENGINE|min_engine|engine_version|__version__ @ tests
- read_file: tests/test_packaging.py
- read_file: CHANGELOG.md
- search_files: compat @ .
- search_files: compat|confirm\(|outdated_message|MIN_ENGINE @ tests
- read_file: tests/test_install_engine.py
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', 'forgel_code/cli.py']
- run: ['git', 'log', '--oneline', '-6']
- run: ['git', 'show', '--stat', 'HEAD']
- search_files: version --json|\-\-version @ . *.py
- run: ['git', 'log', '--oneline', '-S', 'MIN_ENGINE_VERSION', '--', 'forgel_code', 'install.sh']
- recall
- read_file: tests/test_packaging.py
- read_file: tests/test_cli_help_description.py
- search_files: 0\.1\.0 @ .
- search_files: required: command|no command|arguments are required|usage @ tests
- read_file: forgel_code/__main__.py
- read_file: _build_backend.py
- search_files: required: command|add_argument\("--version|show_version|_ParserExit @ tests
- search_files: VERSION|DIST_INFO @ _build_backend.py
- run: ['git', 'log', '--oneline', '-S', 'MIN_ENGINE_VERSION', '--', 'forgel_code/__init__.py']
- read_file: tests/stub_engine.py
- write_file: forgel_code/__init__.py
- read_file: tests/test_install.py
- search_files: ^def run|^def default_engine @ forgel_code/interactive.py
- read_file: tests/test_cli_extra.py
- run: ['git', 'checkout', '--', 'forgel_code/cli.py']
- write_file: forgel_code/cli.py
- write_file: tests/test_version_report.py
- run: ['python3', '-m', 'unittest', 'tests.test_version_report', 'tests.test_cli', 'tests.test_packaging']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- search_files: def version_requested @ forgel_code/cli.py
- read_file: forgel_code/cli.py
- edit_file: tests/test_version_report.py
- read_file: tests/test_version_report.py
- edit_file: tests/test_version_report.py
- run: ['python3', '-m', 'unittest', 'tests.test_version_report', 'tests.test_cli', 'tests.test_cli_extra', 'tests.test_packaging', 'tests.test_cli_help_description']
- read_file: forgel_code/cli.py
- edit_file: forgel_code/cli.py
- run: ['python3', '-m', 'unittest', 'tests.test_version_report', 'tests.test_cli', 'tests.test_cli_extra', 'tests.test_packaging', 'tests.test_cli_help_description']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['python3', '-m', 'unittest', 'tests.test_check_cleanup', 'tests.test_install.InstallerBoundedCheckTest']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['git', 'status', '--porcelain']
- search_files: Report the client version @ .
- read_file: CHANGELOG.md
- edit_file: CHANGELOG.md
- read_file: forgel_code/__init__.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_version_report.py']
- read_file: forgel_code/cli.py
