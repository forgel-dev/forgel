# Task Review: Machine-readable commands for the local client

- Task: `20261116183514_machine-readable-commands-for-the-local-`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-16T19:41:32+00:00

## Summary

The command surface itself is implemented well: client.py parses say/status/tasks/task/projects/session/use/history/plan/pause/resume/daemon, client_cli.py builds one flat envelope with a non-zero exit and a single JSON error object, outcome.py observes the existing CommandRouter instead of adding a second dispatch table, and session.py makes the selected project a durable engine-side session defaulting to `local` (ledger chat id 0). The attributed change does, however, miss two stated requirements: the public docs were not updated (README.md and PLAN.md are untouched; only a new docs/program/commands.md was added), and the `--json` flag is not actually honoured by the new commands, which always print the JSON envelope on stdout and only ever gate the pre-existing commands. Everything else (acceptance checks, script-mode `say` routing, error envelope, sessions, no new dependencies, signed-off commit) looks in order.

## Requirements

- Every local-client operation is reachable as a parameterized, non-interactive `forgel` subcommand (say, status, milestone status, task list, accept/reject/retry, daemon, pause, resume, plan from goal, projects, select project): pass — client.build_parser defines say, status, tasks, task accept|reject|retry|cancel|add, plan --goal/--status, daemon, pause, resume, projects, session/use.
- `forgel say` is the single free-text engine entry point returning the router's structured outcome (answer, change_request, plan, action) with reply text: pass — client_cli.say calls outcome.handle_outcome, which delegates to CommandRouter.handle and records the agent result kind.
- Each subcommand accepts `--json` and then writes exactly one JSON object to stdout; without the flag the human-readable text is the output: fail — `run()` ignores args.json and every client_cli function calls write() unconditionally, so `forgel say ...` (and projects/session/use/history/tasks) print the JSON envelope even without `--json`, contradicting the documented contract; only the legacy status/task/plan/pause/resume/daemon commands are gated on the flag.
- Stable envelope (success flag, kind, reply text, operation payload) and a failed call exits non-zero with exactly one JSON error object: pass — envelope() emits ok/kind/text/error plus payload; fail() writes one error object and returns 1; argparse errors with --json produce a usage envelope.
- The active project is a durable session on the engine side, keyed with default `local`, with commands to set and read it: pass — session.py maps `local` to ledger chat id 0; `forgel session [<project>]` and `forgel use <project>` set/read, `--session` overrides.
- Free text goes through the same router logic as console and Telegram; no duplicated dispatch table or second command implementation in the CLI: pass — outcome.py observes a single router.handle call and only classifies the resulting reply/agent result; no per-command reimplementation in the client layer.
- Recent conversation of a session is readable as a command returning it in JSON: pass — `forgel history [--limit N]` returns the `history` payload read through session.conversation/agent.load_history, not by parsing project files.
- Existing behaviour unchanged: forgel, forgel chat, forgel telegram, interactive commands and their texts keep working; chat mode and console are not moved/deleted: pass — entry.py only short-circuits client commands and `--json` forms of existing commands; legacy CLI/console/chat paths are untouched.
- Command set and JSON envelope documented in the public docs (README.md and the relevant section of PLAN.md): fail — The attributed commit only adds docs/program/commands.md; README.md and PLAN.md are not part of the change and still describe the old one-line `forgel <command>` contract.
- unittest tests assert the JSON envelope for each new command, the error envelope and exit codes, and that `forgel say` turns a change request into a queued task in script model mode: pass — tests/test_client.py builds a temp home and asserts one stdout line, envelope fields and exit codes for status, tasks, task accept/reject and (in the truncated tail) the remaining commands, the error case and the script-mode `say` change_request; the recorded test command exits 0.
- Acceptance: `python3 -m unittest discover -s tests` passes including new command-interface tests: pass — Recorded task test command passed with exit 0.
- Acceptance: with script model mode `forgel say --project <id> --json --text "add a health endpoint"` returns kind `change_request` and the queued task id: pass — say maps the recorder result kind change_request to the payload task/task_id through _task_payload and task_view; covered by a test in the same file.
- Acceptance: `status`, `tasks`, `task accept/reject/retry`, `plan --status`, `projects` covered by tests and documented: pass — All appear in docs/program/commands.md and in the client parser/dispatch; tests for status/tasks/accept are visible and the suite is green.
- Acceptance: session commands set and read the active project for a session key and default to `local`, covered by a test: pass — session_key/ledger_key make empty and "0" map to `local`; session and use commands exercise set/read.
- Acceptance: existing console and Telegram tests still pass unchanged: pass — No test removals detected in the attributed commit and the full suite check exits 0.
- Constraints: no new third-party dependencies, artifacts in English, commit signed off, no secrets in the JSON payload: pass — Only stdlib imports added; docstrings/commit message are English and the commit carries Signed-off-by; payloads are project/task/session views without secret material.

## Blocking

- Public documentation requirement not met: README.md and PLAN.md were not updated with the command set and JSON envelope; only a new docs/program/commands.md was added.
- The `--json` flag is not honoured for the new commands: say/projects/session/use/history/tasks always print the JSON envelope, so without the flag the documented human-readable output is not produced.

## Test Removals

- none


