# Machine-readable client commands

Every operation of the local client is also a parameterized `forgel` subcommand
that needs no interactive prompt. With `--json` a command writes exactly one
JSON object to stdout and nothing else; without the flag the human-readable
text is unchanged, so `forgel`, `forgel chat`, `forgel telegram` and their
interactive commands keep working as before.

## Envelope

```json
{"ok": true, "kind": "status", "text": "project-1a2b: task review (...)",
 "error": "", "project": {"id": "project-1a2b", "state": "task review"}}
```

Flat top level:

| field | meaning |
|---|---|
| `ok` | success flag |
| `kind` | `answer`, `change_request`, `action`, `plan`, `status`, `tasks`, `task`, `projects`, `session`, `use`, `history`, `control`, `daemon` |
| `text` | the reply text a human would see |
| `error` | empty on success, a description otherwise |
| payload | one of `task` (+ `task_id`), `tasks`, `plan`, `project`, `projects`, `history`, `paused`, `cycles` |

A failed call exits non-zero and still writes one JSON object with
`"ok": false` and the reason in `error`; the same reason goes to stderr. The
payload never carries secrets.

## Commands

```text
forgel say --project <id> --text "..." [--session <key>] [--json]
forgel say "add a health endpoint" [--json]
forgel projects [--json]
forgel session [<project>] [--session <key>] [--json]
forgel use <project> [--session <key>] [--json]
forgel history [--session <key>] [--limit N] [--json]
forgel tasks [<project>] [--json]
forgel status <project> --json
forgel task accept|reject|retry|cancel|add --project <id> [--task <id>] [--json]
forgel plan <project> --goal "..." [--dry-run] [--json]
forgel plan <project> --status --json
forgel daemon [--once|--loop] [--interval S] [--max-cycles N] --json
forgel pause [--json]
forgel resume [--json]
```

`say` is the single free-text entry point. It calls the same `CommandRouter`
as the console and Telegram and reports what the message became: an answer, a
queued `change_request` task, a `plan` or a control `action`. The CLI never
reimplements routing.

## Sessions

The active project is a durable engine-side session, so the client keeps no
state between calls. The session key defaults to `local` (the console chat id
0) and is switched with `--session`. `forgel session <project>` and
`forgel use <project>` set it, `forgel session` reads it back,
`forgel projects` marks the selected one, and `forgel history` returns the
recent conversation of the session.
