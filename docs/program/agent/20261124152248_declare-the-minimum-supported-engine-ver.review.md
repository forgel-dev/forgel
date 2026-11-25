# Task Review: Declare the minimum supported engine version in the client

- Task: `20261124152248_declare-the-minimum-supported-engine-ver`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-25T15:20:00+00:00

## Summary

The change adds `version_report()` to `forgel_code/__init__.py`, returning the package's own `__version__` (the single source read by the build backend and packaging tests) together with the existing single declaration `MIN_ENGINE_VERSION`, and wires `forgel-code --version --json` in `cli.py` before any engine discovery, session, timeout or parser work, so the report is produced with no engine installed and without network access. The human-readable `--version` line is unchanged (`forgel-code <version>`), preserving the previous output, and `version_requested()` only recognises the option before a command name so command arguments are unaffected (e.g. `say --version` stays a phrase). The minimum remains declared exactly once and is still obtained from the declaration by the startup check (`compat.py` imports it), so no second copy is introduced; the new test file exercises the report, the no-engine case, the distribution-version equality and the single declaration. The CHANGELOG entry describes the behaviour accurately and no unrelated or generated files are committed. A minor weak point: `test_the_report_never_runs_the_engine` sets `FAKE_ENGINE_LOG`, which no stub writes, so that particular assertion can never fail; the no-engine test covers the same behaviour by making any engine invocation fail. This is not blocking.

## Requirements

- FR-1/FR-2: exactly one concrete minimum supported engine version, declared by the client and never inferred at run time.: pass — `MIN_ENGINE_VERSION = "0.1.0"` remains the single literal declaration in `forgel_code/__init__.py`; `version_report()` reads it, nothing infers it from an installed engine or the network.
- FR-4/AC-1: one stable machine-readable report carrying the client version and the minimum engine version, each unambiguous.: pass — `forgel-code --version --json` prints one JSON object with `forgel_code_version` and `minimum_engine_version`; `report_version()` uses `json.dumps` of `version_report()`.
- FR-5/FR-6/AC-2: the report succeeds with no engine installed and without contacting the network, depending on no engine call, discovery or configuration.: pass — `main()` handles the version request before `build_parser()`/engine construction; the report path imports only the client's own declaration. Tested with a nonexistent `FORGEL_ENGINE` and an emptied PATH.
- FR-7/AC-3: the client version in the report is the installed distribution's version.: pass — `_build_backend._read_version()` (unchanged) reads `__version__` from the same module, and `test_the_client_version_is_the_distribution_version` compares the report against that metadata.
- FR-8/AC-6: the report is machine-consumable and the human-readable version output is unchanged.: pass — `forgel-code --version` still prints `forgel-code <version>` only, asserted by `test_the_human_readable_version_output_is_unchanged`; the JSON form adds no prose.
- FR-9/AC-5: the minimum appears in exactly one place and consumers obtain it from the declaration.: pass — The report reuses `MIN_ENGINE_VERSION`; the startup check (`compat.py`) and packaging/packaging tests read the same declaration. `tests/test_version_report.py` additionally checks no other product module restates the value.
- FR-10: the declaration and report belong entirely to the client and need nothing from the engine.: pass — Both live in `forgel_code/__init__.py`; the CLI path executes no engine call.
- Preserve existing CLI behaviour; the `--version` option is only recognised where it belongs (before a command name).: pass — `version_requested()` stops at the first command name or `--`; `say --version` and `say -- --version` are not treated as version requests, which is covered by tests.
- AC-7: the client's full automated test suite passes with the change.: pass — QA verdict pass (environment test, e2e, repository test all exit 0).
- No unrelated, temporary, debug or generated files; only the change set committed.: pass — Attributed files are CHANGELOG.md, forgel_code/__init__.py, forgel_code/cli.py and the new tests/test_version_report.py; worktree clean, no escalated leftovers.
- No test removals without justification; no weakened tests.: pass — No test removals detected. `test_the_report_never_runs_the_engine` is effectively vacuous (no stub writes `FAKE_ENGINE_LOG`), but the same behaviour is genuinely covered by the missing-engine test, so it is a weak extra check rather than a weakened existing one; not blocking.

## Blocking

- none

## Test Removals

- none


