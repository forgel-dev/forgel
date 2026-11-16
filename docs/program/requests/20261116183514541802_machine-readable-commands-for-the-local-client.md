# Change Request: Machine-readable commands for the local client

- Status: `new`
- Project: `forgel-1d2bf685`
- Created: 2026-11-16T18:35:14+00:00
- Source: Telegram (local)

## Request

Да давай попробуем так как ты описал, начинай

## Summary

Turn every operation the local client needs into a parameterized `forgel` subcommand that can emit a single machine-readable JSON object, without changing the behaviour of the existing console, Telegram gateway or interactive chat. This is the prerequisite for moving the interactive client into its own repository: the client will only call commands and print results, never call the model, read project files or run checks itself.

## Requirements

- Every operation the local client shows must be reachable as a parameterized `forgel` subcommand that needs no interactive prompt: free text, project status, milestone status, task list, accept a task, reject a task, retry a task, run the daemon now, pause, resume, plan a milestone from a goal, list projects, select the active project.
- Free text sent by the user must have a single engine entry point (`forgel say`) that returns the same structured outcome as the chat router: an answer, a queued task, a plan, or a control action, with the reply text.
- Each of those subcommands must accept `--json` and then write exactly one JSON object to stdout and nothing else; without the flag the existing human-readable text stays the output.
- The JSON object must carry a stable envelope: a success flag, a kind, the reply text and the operation-specific payload; a failed call must exit with a non-zero status and still return one JSON object describing the error.
- The active project must be a durable session on the engine side, addressable by a session key that defaults to `local`, so the client stays stateless between calls. Commands to set and read the session are required.
- Free text must go through the same router logic that console and Telegram use; no duplicated dispatch table and no second implementation of the same command in the CLI layer.
- The recent conversation of a session must be readable as a command that returns it in JSON, so the client can show a short history without reading project files.
- Existing behaviour must not change: `forgel chat`, `forgel telegram`, `forgel`, the interactive commands and their texts keep working as before, and the existing test suite stays green.
- Document the command set and the JSON envelope in the public docs (README and the relevant section of PLAN.md) so the future client repository can rely on a written contract.
- Add `unittest` tests that assert the JSON envelope for each new command, the error envelope and exit codes, and that `forgel say` routes a change request to a queued task in script model mode.

## Acceptance Criteria

- `python3 -m unittest discover -s tests` passes and includes new tests for the command interface.
- Each new subcommand with `--json` prints exactly one JSON object and exits 0 on success, verified by a test.
- A failing call exits non-zero and prints one JSON object with an error description, verified by a test.
- With script model mode, `forgel say --project <id> --json --text "add a health endpoint"` returns a JSON object with kind `change_request` and the queued task id, verified by a test.
- `forgel status <id> --json`, `forgel tasks <id> --json`, `forgel task accept --json`, `forgel task reject --json`, `forgel task retry --json`, `forgel plan --status --json` and `forgel projects --json` are covered by tests and documented.
- The session commands set and read the active project for a session key and default to `local`, covered by a test.
- Existing console and Telegram tests still pass unchanged.

## Constraints

- Do not move the console yet and do not delete the chat mode in this task; that is the next step.
- Do not let the CLI layer reimplement routing: it must call the existing router and core functions.
- No new third-party dependencies.
- Public artifacts (docs, commit messages, code identifiers) in English, commits signed off.
- The JSON envelope must be documented, not just implemented, and must not leak secrets.

## Assumptions

- The session key defaults to `local`, matching the console's chat id 0, and is passed with `--session` when another value is needed.
- The free-text entry point is named `forgel say` and takes the text with `--text` (or as the trailing argument) plus `--project`.
- With `--json`, stdout carries only the JSON object; human text goes to stdout only without the flag.
- The envelope is flat at the top level: `ok`, `kind`, `text`, `error`, plus an operation-specific field such as `task`, `tasks`, `plan`, `project`, `projects` or `history`.
- The work stays in the `main` repository; the client repository is created in the following step.
