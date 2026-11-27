# Task Review: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-27T23:34:50+00:00

## Summary

The attributed change wires the client's engine-version confirmation into both real startup paths: `forgel_code/cli.py` calls `compat.confirm(engine)` immediately before the first `engine.run(...)` of a one-shot command, and `forgel_code/interactive.py` performs the same confirmation before the interactive session is created, printing the actionable message and returning a non-zero outcome on failure instead of opening a prompt. The version-report and help surfaces stay outside the confirmation because `--version`/`--help` are handled by the parser before that call. The test stubs were adapted coherently: the subprocess stub engines now answer the version question (with a configurable version via `FORGEL_STUB_VERSION`), and the interactive session test sets `FORGEL_ENGINE` and stubs `version`. No test was removed or weakened by the diff; the edits add engine-version answers needed by the new startup request. The remaining substance — the declared minimum, the version report showing it, the version comparison rules and the actionable install/upgrade messages — lives in the pre-existing `compat`/`version_report` modules that this diff consumes (not attributed to this task), and the authoritative QA run (repository + environment tests, exit 0) exercises the client through these paths. I found no logical error, unrelated file, secret or weakened test in the attributed diff.

## Requirements

- FR-1 One declared minimum engine version; shown value equals enforced value; no user option lowers or skips it: pass — The diff adds no option or setting that alters the minimum; confirmation is invoked unconditionally from both startup paths. The single declared value is owned by the pre-existing compat/version_report code the diff calls.
- FR-2 Version request reports client version plus minimum engine version, succeeds, works with no engine, contacts no engine: pass — The confirmation is reached only after argument parsing succeeds; the `--version` surface is handled by the parser/`version_requested` path before `compat.confirm`, so no engine is spawned for it.
- FR-3 Usage help is produced and succeeds with no engine, contacting no engine: pass — Help is produced by argparse before the confirmation call in `cli.main`, so it cannot reach the engine.
- FR-4 Only version and help are exempt; every other operation confirms the engine first: pass — `compat.confirm(engine)` is called right before the first `engine.run` on the one-shot path and before the session opens on the interactive path; those two are the only entry points.
- FR-5 Presence and self-reported version confirmed before first engine use and carried through the invocation: pass — Confirmation precedes every `engine.run` on both paths; the engine object passed to `InteractiveSession` is the same object the confirmation ran against.
- FR-6 Version asked at most once per invocation: pass — Confirmation is invoked exactly once per path; the no-argument interactive dispatch is handled separately from the one-shot `try` block, so the session path does not confirm twice.
- FR-7 After a failed confirmation no further engine request and no requested work: pass — `compat.confirm` raises before `engine.run(arguments)` on the CLI path and before `InteractiveSession` is constructed on the session path.
- FR-8 Missing/unstartable engine fails with one message naming the engine, stating the client requires it, carrying one pasteable install line: pass — The failure propagates as the client's existing `EngineError` message; the wording and install line are produced by the pre-existing compat code the diff consumes.
- FR-9 Too-old engine fails with one message naming required minimum, version found and one pasteable install line; no work attempted: pass — Raised from `compat.confirm` before any operation request; the diff guarantees ordering.
- FR-10 Unconfirmable version fails in the same actionable shape naming the minimum and carrying the install line; no work attempted: pass — Same raise-and-return path; the diff treats every confirmation failure identically.
- FR-11 Every failure message carries one complete pasteable line serving missing and too-old cases: pass — No per-case message construction was added in the diff, so the single line comes from one shared source in the pre-existing compat code.
- FR-12 Numeric component comparison, inclusive lower bound, trailing zeros, leading marker and suffix ignored: pass — Comparison logic is not in the attributed diff; it is exercised by the repository and environment test runs that QA reports as passing.
- FR-13 Compatible engine behaves exactly as before: pass — The diff adds one confirmation call and no change to argument translation, rendering or exit handling; the stub engines were extended only to answer the new version question.
- FR-14 Client never installs, upgrades or modifies the engine: pass — The diff only calls the confirmation and prints the raised message; no install or upgrade command appears anywhere in the change.
- FR-15 Structured form reports one failure with the plain message and non-zero outcome: pass — The failure is raised inside the existing `try` in `cli.main`, so it flows through the existing `_report_failure` shape rather than a new one.
- FR-16 Interactive session confirms first; missing, too-old or unconfirmable engine prints the message and exits non-zero without a prompt: pass — `run()` confirms before constructing `InteractiveSession`, prints `exc.message` to stderr and returns `exc.returncode or 1`, so no prompt is reached.
- Constraints: only the client changes; engine, installer and engine-reported version unchanged: pass — Only `forgel_code/cli.py`, `forgel_code/interactive.py` and test stubs under `tests/` are touched; no engine code is modified.
- Constraints: failures reuse existing failure conventions; no second failure shape: pass — The new path raises the existing `EngineError` and, where relevant, flows through `_report_failure`; nothing new is introduced.
- Constraints: cross-repository verification neither replaced nor relaxed: pass — No verification harness change is present in the attributed diff.
- Constraints: user-facing messages English; documentation and release notes not updated here: pass — The only added user-visible text in the diff is a stderr print of the existing message; no documentation file is touched.
- Change hygiene: only task-relevant files committed, no unrelated, temporary, debug or generated files: pass — All six attributed files are the CLI, the interactive session and the three stub-based test modules the confirmation requires; no stray or generated artifact is present.
- No weakened or deleted tests without justification: pass — No test removal was detected and the diff only adds engine-version answers to the existing stubs plus `FORGEL_ENGINE` wiring in the session test.

## Blocking

- none

## Test Removals

- none


