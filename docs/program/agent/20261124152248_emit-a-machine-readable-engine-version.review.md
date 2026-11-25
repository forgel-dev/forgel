# Task Review: Emit a machine-readable engine version

- Task: `20261124152248_emit-a-machine-readable-engine-version`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-25T14:16:38+00:00

## Summary

The change adds a program-facing engine version report and removes the second, editable statement of the version. `src/forgel/engine_version.py` reads `[project] version` from `pyproject.toml` (the release declaration, which the repository's own python release preset rewrites), falls back to distribution metadata only when the declaration is not shipped, requires a comparable major.minor.patch value and raises a typed error otherwise; `src/forgel/entry.py` dispatches `forgel version` before the client parser and the legacy CLI, so it never loads settings, opens the ledger or builds a model, and it reports success and failure in the engine's existing flat envelope (non-zero exit, `ok: false`, reason in `error` and on stderr). `src/forgel/__init__.py` no longer keeps a static `__version__` and delegates to the same resolver, so the package attribute cannot disagree with the release. Existing program-facing reports and human-readable outputs are not modified, `--json`/`--home` are accepted the same way the other program-facing commands accept them, and the new tests read the real declaration, cover the empty-machine case, the comparable shape, the failure path and entry dispatch; no test or check was removed or relaxed, and QA reports every gate passing unchanged. The only observations are minor and non-blocking: the command emits machine output even without `--json` (a new command, not an alteration of an existing output), and a malformed declared version falls through to installed metadata instead of failing, which the release train never produces.

## Requirements

- FR-1: On request, the engine states its own version in a form another program reads directly, without interpreting human-readable text.: pass — `forgel version` writes one JSON object through the existing `envelope`/`write` helpers; the value is in the `version` field and `kind` is `version`.
- FR-2: The stated version is the version the release declares; the engine keeps no second, independently editable statement that can disagree with it.: pass — `declared_version()` reads `[project] version` from `pyproject.toml`; the static `__version__ = "0.1.0"` was removed and now delegates, and the python release preset already rewrites the same field, so no second editable statement remains. Installed metadata is only the same value as built from that file and is used only when the declaration is not shipped.
- FR-3: The version is expressed so that two versions can be compared component by component.: pass — `COMPARABLE` requires `major.minor.patch` digits and the command refuses to state anything else; the test asserts three non-negative integer components.
- FR-4: The version is obtainable with no project, no stored configuration, no model credential, no pre-existing user data and no network, from any working directory, leaving no state behind.: pass — The path reads only a file next to the package (or distribution metadata); it never touches the working directory, settings, home or network, and the test runs it in an empty directory with HOME/FORGEL_HOME redirected and asserts the directory stays empty.
- FR-5: Obtaining the version neither starts model work nor reads or changes project, task or account records.: pass — Dispatch happens before `client.maybe_dispatch` and `cli.main`; only module imports occur, no ledger, task or account record is opened or written.
- FR-6: When the version cannot be stated, the failure is signalled as a failure and carries its reason where the engine's other program-facing reports carry it.: pass — `version_command` returns 1 with the usual envelope (`ok: false`, reason in `error`) and prints the reason to stderr; covered by `test_failure_is_a_failure_with_its_reason`.
- FR-7: The engine's other program-facing reports and its human-readable outputs keep their current behaviour.: pass — No existing command, envelope helper, locale string or legacy CLI output was edited; the new route sits before the client parser and the legacy CLI, and `cost` and the client commands are untouched. The new command emitting its machine form without `--json` is a property of a new report, not a change to an existing one.
- FR-8: No other check or test is removed, weakened or relaxed; the installer and client behaviour stay as they are.: pass — No test was removed or loosened; the change adds `tests/test_engine_version.py`, touches no installer or client code, and QA reports the environment gates passing unchanged.
- AC-1: A program obtains the engine's own version directly, without interpreting human-readable text, and the value equals the version the release declares.: pass — `forgel version --json` returns `{"version": ...}` equal to `[project] version`; the tests compare against a freshly parsed `pyproject.toml`.
- AC-2: The version is obtainable with no project, no stored configuration, no model access and no network, from any working directory, leaving nothing behind.: pass — `test_reads_with_nothing_set_up_and_leaves_nothing_behind` changes into an empty temporary directory with HOME/FORGEL_HOME pointing there and asserts no file is created.
- AC-3: All remaining checks pass unchanged.: pass — QA verdict pass with environment test and both e2e checks at exit 0; no test removal was detected.
- Constraint: the release-declared version is the single authority; the report must not add a second editable statement.: pass — The only writable declaration is `pyproject.toml`; the package attribute and the report both derive from it, so nothing in the repository can be edited independently to disagree.
- Constraint: the change adds a report and must not alter any existing program-facing report or human-readable output.: pass — The diff adds a route and a module; `client_cli.envelope`/`write` are reused unchanged and no existing command, envelope field or localized text is modified.
- Constraint: the report must be usable before the surrounding system is configured.: pass — It runs before settings loading, ledger access and model construction, so it works on an unconfigured machine.
- Constraint: no existing check or test may be removed, weakened or relaxed.: pass — Only additions in the test suite; no assertion or guard was touched.
- Assumption: the report follows the engine's existing program-facing conventions instead of inventing new ones.: pass — It is a `forgel` subcommand accepting `--json`/`--home` and reporting through the shared flat envelope; no new calling convention, transport or envelope shape is introduced.
- Assumption: everything that reports or compares a version takes it from the release declaration.: pass — `forgel.__version__` now resolves through the same function, so the package attribute and the command cannot disagree.
- Change composition: every file the task needs is present and no unrelated, temporary, debug or generated file is committed.: pass — The attributed files are exactly the new module, its tests and the two dispatch/attribute edits; no stray or generated file is part of the commit, and the uncommitted program artifacts are process bookkeeping, not product files.

## Blocking

- none

## Test Removals

- none


