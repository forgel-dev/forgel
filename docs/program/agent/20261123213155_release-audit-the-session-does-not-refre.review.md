# Task Review: Release audit: The session does not refresh task and release state on its own while the owner i

- Task: `20261123213155_release-audit-the-session-does-not-refre`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T00:32:14+00:00

## Summary

The change makes the interactive client refresh the project's task and release state on its own while the owner waits: `InteractiveSession.wait_for_line` runs the blocking `readline` in a daemon thread and, every `IDLE_REFRESH_SECONDS`, calls `idle_refresh`, which re-reads `tasks` and `status` through the existing engine commands and renders them with the same `read_state`/`show_state` path used today. Unchanged state prints nothing because `show_state` compares against `last_state`; repeated changes keep printing because the comparison is against the last displayed text. Failures during an idle refresh are caught, reported once per distinct message in the existing `show_failure` cause-and-next-step form, and leave the session running so the next sentence still works. Text typed by the owner is never touched by the client (it only reads a line), end of input still returns an empty string and ends the session with the closing notice and success outcome, and the new test `tests/test_idle_refresh.py` proves the refresh with a silent pipe input (no empty sentences) for two successive engine-side changes, an unchanged period, mid-typing refresh, a failure during the wait, and end-of-input. The only adjustment to a pre-existing test is adding `threading` to the stdlib allowlist, which is required by the new import and does not weaken the check. I found no requirement gap; a minor observation is that the refreshed block is written directly after the already-printed prompt, so the first line of the state appears on the prompt line rather than below it — harmless to the state content and to what reaches the engine, and not a requirement violation.

## Requirements

- While the owner is idle and has submitted nothing, the client re-reads the project's task list and the current release state from the engine on its own (FR-1).: pass — `wait_for_line` polls `idle_refresh` on a timer while the input thread is blocked, and `idle_refresh` calls `read_state`, which issues the existing `tasks` and `status` engine commands; no new command or state kind is introduced.
- A task or release change while the owner waits becomes visible without any submitted sentence, including an empty one (FR-2, AC-1).: pass — `idle_refresh` renders the freshly read state via `show_state`; the new test changes the stub's `tasks`/`status` payload while the pipe input stays silent and asserts the new release/task lines appear, and also asserts no `say` call happened.
- The refresh repeats for as long as the owner waits, so a second change after the first is also shown (FR-3, AC-2).: pass — The polling loop iterates until input or stop, and the test changes the state a second time and asserts the second change is rendered after the first, checking ordering.
- A refresh that finds the state unchanged adds no state text (FR-4, AC-3).: pass — `show_state` only writes when the rendered text differs from `last_state`; the quiet-wait test asserts no repeated state text is emitted while the payload is stable.
- The refreshed state is shown in the same form the session already uses, indistinguishable from a prompted update except that no prompt was answered (FR-5).: pass — Both prompted and idle updates go through the same `read_state`/`show_state` rendering, so lines, wording and language are identical; only placement relative to the pending prompt differs, which does not change the state's content or form.
- A refresh while the owner is part-way through a sentence does not remove, repeat, reorder or alter the typed characters, and the submitted sentence reaches the engine as typed (FR-6, AC-4).: pass — The client only calls `readline` in a helper thread and never edits or buffers the line; the test writes `sta`, triggers a refresh, finishes with `tus\n`, and asserts the engine received the full sentence and the existing answer rendering plus success outcome.
- When the owner's input ends, the session ends cleanly with the closing notice and the same success outcome, without hanging or needing an extra sentence (FR-7, AC-5).: pass — An empty read yields an empty string, the `run` loop breaks as before, and the existing closing notice and return code path are unchanged; the new test closes the pipe and asserts exit code 0 with the closing notice, and the pre-existing end-of-input tests still pass.
- An engine failure during an idle refresh keeps the session running, is shown in the existing cause-and-next-step failure form, and the next sentence still works (FR-8, AC-6).: pass — `idle_refresh` catches `EngineError` and calls the existing `show_failure`, returning without ending the session; the failure test makes `tasks`/`status` fail, asserts the message appears, then submits a working sentence.
- Idle waiting stays quiet and cheap with no engine-side changes (FR-9).: pass — No output is produced when the state is equal, failures are de-duplicated through `idle_failure`, and the cadence is a fixed interval rather than a busy loop; the cadence value is explicitly the developer's choice per the recorded assumption.
- The behavior is the same for an interactive terminal and a supplied stream of sentences (FR-10).: pass — The implementation goes through the same `self.input.readline()` call for both cases, and the new test drives the session through an `os.pipe` while the existing interactive tests keep using in-memory streams.
- The idle refresh is demonstrated by a session whose input provides no further sentences for the observation window (FR-11, AC-7).: pass — Review-only check verified by reading `tests/test_idle_refresh.py`: the observation window relies on a pipe with no writes, the two engine-side changes are shown before anything is typed, and the test additionally asserts that no `say` command was issued, so empty sentences are not the trigger.
- No new engine commands, panels, status commands, refreshed state kinds, wording changes, model calls or version/tag manipulation are introduced (non-goals).: pass — Only `tasks` and `status` are read, the prompt text and messages are untouched, no model/file/check access is added, and no release version handling is touched.
- All tests that existed before the change still pass, and no test is weakened or removed without justification (AC-8).: pass — The only edit to an existing test adds `threading` to the stdlib allowlist of `NoEngineImportTest`, which the new import requires and which does not relax the assertion; QA reports the full pre-existing suite passing.
- The change is internally consistent and contains only files the task needs.: pass — The module docstring, the new constant, the helpers and the call site agree; the new test file is self-contained with its own stub, and the diff contains no unrelated, temporary or generated files.

## Blocking

- none

## Test Removals

- none

- tests/test_cli.py::NoEngineImportTest::test_client_sources_import_only_stdlib: replaced -> tests/test_cli.py::NoEngineImportTest::test_client_sources_import_only_stdlib
