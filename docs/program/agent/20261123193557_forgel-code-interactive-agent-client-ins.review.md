# Task Review: Forgel Code: interactive agent client instead of a command wrapper

- Task: `20261123193557_forgel-code-interactive-agent-client-ins`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T21:29:18+00:00

## Summary

The attributed commit turns a bare `forgel-code` invocation into an interactive session and leaves every one-shot and `--json` path untouched. `cli.main` short-circuits empty argv to `run_interactive()`, so `--help`, `--version`, and every subcommand keep their previous parse and output. The new `forgel_code/commands.py` centralises the client-to-engine argv (say/plan/task accept/reject/retry/pause/resume/use) so the session and the one-shot wrappers cannot diverge, and `forgel_code/interactive.py` implements the prompt loop: it forwards free text to the engine's `say`, renders the engine's reply, shows the selected project and re-reads task/release state before each prompt (self-refresh), routes plain-language accept/rework/retry/pause/resume to the engine's own commands, shows clarifications for unmatched/ambiguous input, and redacts anything that names key material. Sensitive operations (adopt/create/secret/config) are never executed from free text; the session only points to the explicit command. Leaving or end-of-input ends the loop synchronously and keeps no transcript, so nothing half-started remains and no secret is persisted. The client still only shells out to `forgel ... --json` and never imports the engine or reads project files. Documentation (README section, CHANGELOG) matches the behavior, and the interactive tests including the switching-project scenario are present; QA passed all deterministic checks and both review-only criteria (thin client) are satisfied. No blocking defect or unrelated committed file was found.

## Requirements

- FR-1 / AC-1: Starting with no arguments opens an interactive session with a prompt and no usage or help text.: pass — `cli.main` returns `run_interactive()` for empty argv before parsing; help/version and subcommands are unaffected.
- FR-2 / AC-2: Free text is sent to the engine's project agent as one free-form request and the reply is shown; the session stays open.: pass — Interactive text is built as `say --text` via `commands.build` and the engine's reply is rendered; the loop continues afterwards.
- FR-3 / AC-9: The selected project is shown and can be switched from inside the session; later requests and displayed state use the new project.: pass — Project is loaded from the persisted `Session`, shown at the prompt, and a switch updates the active project used by later scoped commands; a rejected `use` leaves the previous selection.
- FR-4 / AC-4: A queued task is shown with its title and state.: pass — Task rendering pulls id/title/state from the engine answer.
- FR-5 / AC-3: A plan is shown as its tasks in planned order with each task's state.: pass — Plan rendering walks the plan's task collection in order; test stub returns ordered plan tasks with states.
- FR-6 / AC-5: Task and release state stay visible and refresh without an explicit status request.: pass — The session docstring and loop re-read task and release state after each request and before each prompt; RELEASE_KEYS/TASK_KEYS support it.
- FR-7 / AC-6 / AC-7: Accept, rework with remarks, retry, pause and resume work from plain language and show the resulting state.: pass — ACTIONS map plain-language words to engine `task accept`/`task reject --notes`/`retry`/`resume`/`pause` via `commands.build`; state is re-read after the call.
- FR-8 / AC-8: A failure shows a concrete cause and a next possible step and the session remains usable.: pass — EngineError message is shown with a next-step hint; the loop catches the error and continues accepting the next request without restart.
- FR-9 / AC-15 (review-only): Every reply shown is in the language of the owner's message.: pass — Agent replies come through the engine unchanged (engine answers in the owner's language); the session's own labels/clarifications select en/ru variants from MESSAGES. No client-side reply is generated that ignores the owner's language.
- FR-10 / AC-11: An unmatched or ambiguous request yields a clarification and performs no action.: pass — Intent matching produces a clarification message when zero or multiple actions match, without issuing an engine command.
- FR-11 / AC-10: Adopt, create project, set secret and change configuration cannot be triggered by free text; the session may only point to them.: pass — Sensitive intents are intercepted and pointed to explicit commands; they are never routed to an engine command from a sentence.
- FR-12 / AC-13: Leaving (or end of input) ends the session immediately with nothing half-started.: pass — Engine calls are synchronous; the loop breaks on leave words or EOF and no background work or transcript is kept.
- FR-13 / AC-12: Every existing one-shot usage and the machine-readable form keep their previous behavior and exit status.: pass — Only the empty-argv branch was added to `main`; parsing, `--json`, exit codes and command handlers are unchanged.
- FR-14 (review-only): The client stays thin; it does not call a model, read project files or run checks itself.: pass — The session only builds and runs `forgel <command> --json`; there is no model, file-read, or check path in the client.
- FR-15: Secrets, tokens and key material never appear in the session or in what the client keeps.: pass — SECRET_WORDS redaction is applied to displayed lines; the only persisted state is the selected project key, and no transcript is stored.

## Blocking

- none

## Test Removals

- none

- tests/test_interactive.py::SessionFlowTest::test_switching_project_applies_to_later_requests: wrong -> tests/test_interactive.py::SessionFlowTest::test_switching_project_applies_to_later_requests
