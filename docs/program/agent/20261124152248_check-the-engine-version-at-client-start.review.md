# Task Review: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-25T04:52:15+00:00

## Summary

The attributed change adds a new module `forgel_code/compat.py` with version parsing, action messages and a `confirm` helper, but nothing wires it into the client: neither `forgel_code/cli.py` nor `forgel_code/interactive.py` imports it or calls `confirm`, so no engine version is ever requested and none of the missing/too-old/unconfirmed behaviours reach the user. The client's version report in `cli.py` still prints only `forgel-code <version>` and never the declared minimum engine version, and no test exercises the confirmation path. The file itself is reasonably written, but in the repository's current state the feature the task asks for is not implemented — only an unused helper exists.

## Requirements

- FR-1 / FR-13: the client declares exactly one minimum supported engine version as its own fixed value, not overridable by the user: pass — `MIN_ENGINE_VERSION = "0.1.0"` is declared once in `forgel_code/__init__.py` and read by `compat`; it is not a user setting.
- FR-2 / AC-1 / AC-12: the client's version report prints both the client version and the declared minimum engine version and succeeds without an engine: fail — `build_parser()` still registers `--version` as `"forgel-code %s" % __version__`; the minimum engine version is never printed.
- FR-3 / AC-2: usage help still works with no engine installed: pass — Help is produced by argparse before any engine call, so it is unaffected.
- FR-4 / FR-10 / AC-9: the engine is confirmed once before first use and the result carried through the invocation: fail — `compat.confirm` is never called by `cli.py` or `interactive.py` (their import blocks list only `.engine`, `.render`, `.session`, `.commands`); the engine is used with no confirmation at all, so `at most once` is vacuously true but the confirmation never happens.
- FR-5 / AC-3 / AC-13: a missing or unstartable engine fails with one message naming the engine and a runnable install instruction: fail — `missing_message` exists but is unreachable; without a caller the user still receives the raw engine error path in `Engine.run` (e.g. `executable not found`).
- FR-6 / AC-4: an engine below the minimum fails with the required version, the version found and an upgrade instruction, and the operation is not attempted: fail — `outdated_message`/`confirm` are dead code; no invocation checks the engine version before running the requested command.
- FR-7 / AC-5: an engine that answers without a usable version fails the same actionable way: fail — `unconfirmed_message` is unreachable for the same reason.
- FR-8 / AC-6: a compatible engine keeps identical requests, output and exit status: pass — No engine-backed request or rendering was altered by the diff, so behaviour with a compatible engine is unchanged (trivially, since nothing was hooked in).
- FR-9 / AC-7 / AC-8: numeric component-wise comparison, trailing zeros equal, non-numeric suffix ignored: pass — `numeric_version`/`supported` implement numeric tuples with trailing-zero trimming and stop at the first non-numeric character; 0.10.0 > 0.9.0 and '0.9.0+x' equals 0.9.0.
- FR-11 / AC-10: the machine-readable form carries these failures as one result with a non-zero exit: fail — The confirm failures never reach `main`, so the `--json` failure envelope is never produced for a missing or too-old engine.
- FR-12 / AC-11: the interactive session confirms the engine first and exits non-zero with the guidance instead of opening a prompt: fail — `interactive.py` does not import `compat` and performs no confirmation before opening the prompt.
- The change includes every file it needs and is internally consistent (no dead code): fail — The task requires edits to the command entry point, the interactive session entry point and the version report; the attributed diff adds only the helper module, leaving it unreferenced and the feature inert.
- Tests for the new behaviour are present and no test was weakened: fail — No test covers the confirmation, the install/upgrade messages, the version report change or the session startup; the spec's own listed risk that stand-in engines report and would be judged incompatible is unaddressed.

## Blocking

- `forgel_code/compat.py` is dead code: neither `forgel_code/cli.py` nor `forgel_code/interactive.py` imports or calls `compat.confirm`, so the engine version is never confirmed and no install/upgrade message is ever shown (FR-4 to FR-7, FR-10 to FR-12, AC-3 to AC-5, AC-9 to AC-11).
- The client's version report still prints only `forgel-code <version>`; the declared minimum engine version is not shown (FR-2, AC-1, AC-12).
- No test exercises the version confirmation, the actionable messages or the version report change, leaving the feature unproven.

## Test Removals

- none


