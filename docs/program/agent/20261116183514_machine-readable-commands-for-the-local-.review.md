# Task Review: Machine-readable commands for the local client

- Task: `20261116183514_machine-readable-commands-for-the-local-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-16T20:02:22+00:00

## Summary

The change adds a machine-readable client command surface (src/forgel/client.py + client_cli.py) wired into entry.main before the legacy CLI, sharing CommandRouter through the new outcome.handle_outcome so `forgel say` reports answer/change_request/plan/action with the router's reply text, plus a durable engine-side session with default key `local` (session.py), JSON envelope (ok/kind/text/error + payload), a history command backed by the project conversation store, and documentation in README, docs/program/commands.md and PLAN.md. Existing commands (chat, telegram, bare forgel, task/status/plan/pause/resume/daemon without --json) keep the legacy path, no third-party dependencies were added, and the attributed tests plus reported acceptance checks (environment test/e2e, unittest discover) pass. No test removals were detected and no secrets are exposed in the documented payload.

## Requirements

- Every local-client operation is reachable as a parameterized non-interactive `forgel` subcommand (free text, project status, milestone status, task list, accept/reject/retry a task, run the daemon, pause, resume, plan a milestone, list projects, select the active project).: pass — client.py builds say/tasks/status/task accept|reject|retry/plan/projects/pause/resume/daemon/session/use/history; plan --status and project status are covered; core functions (accept_task, reject_task, plan_project, plan_status, run_daemon, set_paused) are called rather than duplicated.
- Free text has a single engine entry point (`forgel say`) that returns the same structured outcome as the chat router: answer, queued task, plan or control action, with the reply text.: pass — client_cli.say delegates to outcome.handle_outcome, which calls CommandRouter.handle and classifies via _Recorder into answer/change_request/action/plan, carrying reply.text.
- Each new subcommand accepts `--json` and writes exactly one JSON object to stdout and nothing else; without the flag the human-readable text remains the output.: pass — emit() prints json.dumps(dict) only with --json and otherwise prints the text; fail() writes one envelope; tests strip lines and assert a single JSON line via _call().
- Stable JSON envelope with success flag, kind, reply text and operation-specific payload; a failed call exits non-zero and still returns one JSON object describing the error.: pass — envelope(ok, kind, text, error, **payload) is flat; fail() prints 'error: ...' to stderr, writes one ok:false object when --json and returns 1. A usage parse error also emits one JSON object with --json.
- The active project is a durable engine-side session addressable by a session key defaulting to `local`, with commands to set and read it.: pass — session.py stores the selection in the ledger, DEFAULT_SESSION = 'local' mapping to chat id 0, with get/set/clear, session_view and conversation; client_cli exposes `session` (read/set) and `use` (set), and `--session` switches the key.
- Free text goes through the same router logic as console and Telegram; no duplicated dispatch table and no second implementation in the CLI layer.: pass — say constructs a CommandRouter (with the model-built ProjectAgent when available) and calls outcome.handle_outcome; no CLI-side re-implementation of routing exists, only core function calls for reporting/control commands.
- Recent conversation of a session is readable as a JSON command without reading project files directly.: pass — `forgel history` calls session.conversation, which loads the project history via agent.load_history and returns role/text/at rows through the envelope's `history` payload.
- Existing behaviour is unchanged: `forgel chat`, `forgel telegram`, `forgel`, the interactive commands and their texts keep working, and the existing test suite stays green.: pass — maybe_dispatch only intercepts the six new names unconditionally and the other commands only when `--json` is present; otherwise entry.main falls through to cli.main. Reported acceptance checks (environment test/e2e, task test command) pass and no tests were removed.
- Document the command set and JSON envelope in the public docs (README and the relevant PLAN.md section), with the contract not leaking secrets.: pass — README gained a 'Scripted Client' section with the command list and envelope table; docs/program/commands.md records the full contract; PLAN.md is among the attributed files. The documented payload fields (task/tasks/plan/project/projects/history/paused/cycles) carry no secrets.
- Add unittest tests asserting the JSON envelope for each new command, the error envelope and exit codes, and that `forgel say` routes a change request to a queued task in script model mode.: pass — tests/test_client.py drives entry.main under FORGEL_MODEL_MODE=script, asserts a single JSON line and envelope fields (status, tasks, task accept, etc.) and uses accept/reject/retry/plan/projects/session helpers; the reported task test command passes, satisfying the acceptance tests.
- Acceptance: `python3 -m unittest discover -s tests` passes; each new subcommand with --json prints one object and exits 0; a failing call exits non-zero with one error object; say returns kind change_request with queued task id; status/tasks/task accept|reject|retry/plan --status/projects covered and documented; session set/read defaults to `local`.: pass — The environment/task test command and e2e checks passed (exit 0), and the attributed test file provides the envelope helper and per-command coverage for the required operations and the default-`local` session.
- Constraints: do not move the console or delete chat mode; do not reimplement routing; no new third-party dependencies; public artifacts in English; commits signed off.: pass — console.py/chat.py stay intact and entry.main still falls back to cli.main; no new pip dependencies were introduced; docs and identifiers are English; both attributed commits carry the Signed-off-by trailer.

## Blocking

- none

## Test Removals

- none


