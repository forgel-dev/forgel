# Feature: Machine-readable commands for the local client

## Document Information

| Field | Value |
|-------|-------|
| Feature | Machine-readable commands for the local client |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-16T18:35:14+00:00 |
| Source | Local console request (`local`) |
| Author | Forgel project agent |

## Overview

The interactive client will become a separate public repository (D-001, D-005).
Before it can move, every operation the client shows must exist as a
parameterized `forgel` command that returns a stable machine-readable result.
This feature adds that engine contract. It does not move the console, remove the
chat mode, or let the client call the model, read project files or run checks
itself (D-002, D-003, D-006).

## Goals

- Give the future client one stable engine entry point for every operation it
  shows, with no interactive prompt.
- Make success and failure machine-readable: one JSON object with a stable
  envelope, and a non-zero exit status on failure.
- Keep the active project on the engine side as a durable session, so the
  client stays stateless between calls.
- Reuse the existing command router; the command-line layer must not grow a
  second dispatch table or a second implementation of the same operation.
- Keep the current console, Telegram gateway, `forgel chat` and interactive
  command texts working unchanged.
- Document the contract in the public documentation so the separate client can
  depend on it.

## Non-Goals

- Moving the interactive console to the client repository. That is the next
  step under D-006.
- Removing the engine's chat mode. That happens after the console moves.
- Letting the client call the model, read project files, run tests, deploy, or
  approve staging or production.
- Changing the Telegram gateway or its command surface.
- Adding third-party dependencies.
- Producing a JSON object for a command that was not asked to use `--json`.
- Letting a JSON response carry secrets or raw environment values.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| D-001 | The interactive client moves to a separate public repository in the same organization as the engine. | User, 2026-11-16 21:14 |
| D-002 | The client is a thin UI over the engine's parameterized commands; the model, sandbox, QA, review and release approval stay in the engine. | User, 2026-11-16 18:31 |
| D-003 | The base parameterized command line stays in the engine; the separate client replaces the chat mode. | User, 2026-11-16 18:31 |
| D-004 | The client's working name is Forgel Code; it is a Python client installed as `forgel-code`, scoped by Pareto 20/80, and imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| D-005 | The second repository is public and lives in the same organization as the first (`forgel-dev`). | User, 2026-11-16 21:14 |
| D-006 | Order: machine-readable commands first, then the client repository and console move, then removal of the replaced chat mode. | User accepted the proposal, 2026-11-16 18:34 |
| D-007 | `forgel say` is the single free-text entry point; client-facing commands accept `--json` and print one JSON object; the active project is an engine-side session with default key `local`. | User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: Every operation the local client shows must be reachable as a
  parameterized `forgel` subcommand that needs no interactive prompt: free
  text, project status, milestone status, task list, accept a task, reject a
  task, retry a task, run the daemon now, pause, resume, plan a milestone from
  a goal, list projects and select the active project.
- **FR-2**: Free text must have one engine entry point, `forgel say`, that
  returns the same structured outcome as the chat router: an answer, a queued
  task, a plan or a control action, with the reply text.
- **FR-3**: Each of those subcommands must accept `--json`. With the flag,
  standard output carries exactly one JSON object and nothing else; without
  the flag, the existing human-readable text remains the output.
- **FR-4**: The JSON object must carry a stable envelope: a success flag, a
  kind, the reply text and the operation-specific payload. A failed call must
  exit non-zero and still return one JSON object describing the error.
- **FR-5**: The active project must be a durable engine-side session,
  addressable by a session key that defaults to `local`. Commands to set and
  read the session are required.
- **FR-6**: Free text must go through the same router logic the console and
  Telegram use. The command-line layer must not duplicate the dispatch table
  or reimplement an operation.
- **FR-7**: The recent conversation of a session must be readable as a command
  that returns it in JSON, so the client can show a short history without
  reading project files.
- **FR-8**: Existing behaviour must not change: `forgel chat`, `forgel
  telegram`, bare `forgel`, the interactive commands and their texts keep
  working, and the existing test suite stays green.
- **FR-9**: The command set and JSON envelope must be documented in the public
  README and in the relevant section of `PLAN.md`, so the future client
  repository can rely on a written contract.
- **FR-10**: The `unittest` suite must cover the JSON envelope for each new
  command, the error envelope and exit codes, and the `forgel say` path that
  queues a change request in script model mode.

## Technical Requirements

- One flat, stable JSON envelope at the top level: `ok`, `kind`, `text`,
  `error`, plus one operation-specific field such as `task`, `tasks`, `plan`,
  `project`, `projects` or `history`.
- With `--json`, stdout contains only the JSON object; human text goes to
  stdout only without the flag. An error message also goes to stderr.
- The command-line layer calls the existing router and core functions; it must
  not hold a second dispatch table.
- The session key defaults to `local`, matching the console's chat id 0, and
  is passed with `--session` when another value is needed.
- The commands must not leak secrets in JSON payloads or error messages.
- No new third-party dependencies.
- Public artifacts, code identifiers and this document are in English; commits
  are signed off.

## User Stories

- As the Forgel Code client, I call `forgel status --json` and receive one
  object that I can render without parsing human text.
- As the Forgel Code client, I send a free-text request through `forgel say`
  and receive either an answer, a queued task or a plan with a stable kind.
- As a client author, I read the public command contract and know the exact
  envelope, exit codes and session semantics before writing any code.
- As a console or Telegram user, I keep the same commands and texts I use
  today while the machine-readable contract grows underneath.

## Tests

- The full `python3 -m unittest discover -s tests` suite passes.
- Each new subcommand with `--json` prints exactly one JSON object and exits 0
  on success.
- A failing call exits non-zero and prints one JSON object with an error
  description.
- In script model mode, `forgel say --project <id> --json --text "add a health
  endpoint"` returns a JSON object with kind `change_request` and the queued
  task id.
- `forgel status <id> --json`, `forgel tasks <id> --json`, `forgel task accept
  --json`, `forgel task reject --json`, `forgel task retry --json`, `forgel
  plan --status --json` and `forgel projects --json` are covered and
  documented.
- Session commands set and read the active project for a session key and
  default to `local`.
- The existing console and Telegram tests pass unchanged.

## Acceptance Criteria

- **AC-1**: `python3 -m unittest discover -s tests` passes and includes new
  tests for the command interface.
- **AC-2**: Each new subcommand with `--json` prints exactly one JSON object
  and exits 0 on success, verified by a test.
- **AC-3**: A failing call exits non-zero and prints one JSON object with an
  error description, verified by a test.
- **AC-4**: With script model mode, `forgel say --project <id> --json --text
  "add a health endpoint"` returns a JSON object with kind `change_request`
  and the queued task id, verified by a test.
- **AC-5**: `forgel status <id> --json`, `forgel tasks <id> --json`, `forgel
  task accept --json`, `forgel task reject --json`, `forgel task retry
  --json`, `forgel plan --status --json` and `forgel projects --json` are
  covered by tests and documented.
- **AC-6**: The session commands set and read the active project for a session
  key and default to `local`, covered by a test.
- **AC-7**: Existing console and Telegram tests still pass unchanged.

## Scope Boundaries

This feature is the engine-side contract only. Moving the console to the
separate public client repository, removing the engine chat mode, and building
the Forgel Code UI are the following steps under D-006. The engine keeps model
access, the sandbox, independent QA, review and release approval. The client
never calls the model, reads project files or runs checks itself.

## Risks

- **R-1**: A second dispatch table appears in the command-line layer and drifts
  from the router. Mitigation: FR-6 and a test that `forgel say` uses the
  shared router.
- **R-2**: `--json` leaks human text or multiple objects to stdout, breaking
  clients. Mitigation: FR-3, AC-2 and a test for exactly one object.
- **R-3**: An error path exits zero or prints no JSON object. Mitigation:
  FR-4, AC-3 and one error object with a non-zero exit.
- **R-4**: The session key semantics differ from the console's chat id and the
  client loses its selected project. Mitigation: FR-5, `local` = chat id 0,
  AC-6.
- **R-5**: Public documentation drifts from the implemented contract.
  Mitigation: FR-9 and the README/PLAN sections updated in the same change.

## Open Questions

- None. The repository location is decided by D-001 and D-005; the client
  naming and install command by D-004; the work order by D-006.

## Affected Files

- `src/forgel/cli.py`
- `src/forgel/client.py`
- `src/forgel/client_cli.py`
- `src/forgel/outcome.py`
- `src/forgel/session.py`
- `src/forgel/console.py` (only shared helpers, no console move)
- `tests/` (new command-interface tests)
- `README.md`
- `PLAN.md`
- `docs/program/commands.md`

## Assumptions

- The session key defaults to `local`, matching the console's chat id 0, and is
  passed with `--session` when another value is needed.
- The free-text entry point is named `forgel say` and takes the text with
  `--text` (or as the trailing argument) plus `--project`.
- The envelope is flat at the top level: `ok`, `kind`, `text`, `error`, plus
  one operation-specific field.
- The work stays in the `main` repository; the client repository is created in
  the following step under D-006.

## Related Documents

- `docs/program/decisions.md` — binding user decisions D-001–D-007.
- `PLAN.md` §7.18 — machine-readable client commands.
- `docs/program/commands.md` — command contract.
- `README.md` — public client section.

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-11-16 | Initial feature request recorded. |
| 1.1.0 | 2026-11-17 | Expanded to the full requirements model; added binding user decisions; removed the raw request message; added goals, non-goals, stories, tests, risks, open questions, affected files and revision history. |
