# Release plan 20261123192641618630_machine-readable-failures-for-every-client-comma

- Project: `forgel-1d2bf685`
- Request: Machine-readable failures for every client command and a consistent selected project
- Class: minor
- Status: cancelled
- Created: 2026-11-23T19:26:41+00:00


## Request

Every client command failure, including an argument-parse error, must end in a non-zero exit and, in machine-readable mode, exactly one structured report with a false success flag, the command the user asked for and the project in effect; human-readable mode prints the message on the error channel only. The selected project must be passed to the engine by every command that acts on a project and must not be passed by a command that does not, and the reported project must equal the project actually sent.

## Repositories

- `code` — pending, preset python, base 0.1.1, planned 0.2.0

## Tasks

- `20261123192641_machine-readable-failures-for-every-clie` — Machine-readable failures for every client command and a consistent selected project (code, cancelled)

## Audit

- Rounds: 0
- Verdict: not run
- Report: `—`
