# Feature: Machine-readable failures for every client command and a consistent selected project

## Document Information

| Field | Value |
|-------|-------|
| Feature | Machine-readable failures for every client command and a consistent selected project |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-23T19:26:41+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

Every client command failure, including an argument-parse error, must end in a non-zero exit and, in machine-readable mode, exactly one structured report with a false success flag, the command the user asked for and the project in effect; human-readable mode prints the message on the error channel only. The selected project must be passed to the engine by every command that acts on a project and must not be passed by a command that does not, and the reported project must equal the project actually sent.

## Product Intent

Forgel Code is a thin console client for Forgel: it turns plain phrases into engine commands and reports what the engine answered. The owner wants its failures to be as predictable as its successes — a script that calls the client must always be able to read one structured failure object, know which command failed and which project was in effect, and never see a bare parser exit or a traceback.

## User Experience

The user runs a client command, for example accepting a task or sending one back, with a selected project. On success nothing changes. When the invocation is wrong — an unknown command, a missing task identifier, a non-numeric limit — the human-readable run prints a single clear message on the error channel and exits non-zero; a run asking for machine-readable output prints exactly one structured failure report that names the requested command and the project in effect, and exits non-zero. This replaces the current behaviour where those two facts are empty for argument errors.

## Roadmap

- Report every client failure, including argument errors, as one structured report naming the requested command and the project in effect
- Pass the selected project to the engine from every command that acts on a project, and only from those
- Verify the whole set of changes and release it in the code repository

## Goals

- A client command that acts on a project always sends the selected project to the engine, and the project reported to the caller is the same one that was sent.
- A client command that does not act on a project never sends a project.
- Any failed invocation — unknown command, missing required argument, malformed numeric limit, remarks that contain no text — exits with a non-zero code.
- In machine-readable mode every failed invocation prints exactly one structured report with a false success flag and a readable message, and nothing else on the standard output stream.
- That failure report names the command the user asked for and the project in effect at the time of the invocation, whenever the invocation determines them; a value stays empty only when the invocation itself cannot determine it.
- In human-readable mode a failed invocation prints the message on the error stream and no structured report.
- No failed invocation ends through an unhandled parser exit or prints a language traceback.
- A structured refusal from the engine remains a failure even when the engine itself reports success, and keeps the engine's own error fields.
- The successful answer of every command keeps its current shape and content.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- **FR-1**: A client command that acts on a project always sends the selected project to the engine, and the project reported to the caller is the same one that was sent.
- **FR-2**: A client command that does not act on a project never sends a project.
- **FR-3**: Any failed invocation — unknown command, missing required argument, malformed numeric limit, remarks that contain no text — exits with a non-zero code.
- **FR-4**: In machine-readable mode every failed invocation prints exactly one structured report with a false success flag and a readable message, and nothing else on the standard output stream.
- **FR-5**: That failure report names the command the user asked for and the project in effect at the time of the invocation, whenever the invocation determines them; a value stays empty only when the invocation itself cannot determine it.
- **FR-6**: In human-readable mode a failed invocation prints the message on the error stream and no structured report.
- **FR-7**: No failed invocation ends through an unhandled parser exit or prints a language traceback.
- **FR-8**: A structured refusal from the engine remains a failure even when the engine itself reports success, and keeps the engine's own error fields.
- **FR-9**: The successful answer of every command keeps its current shape and content.

## User Stories

- None stated.

## Acceptance Criteria

- **AC-1**: Asking for machine-readable output with a missing required argument produces one structured object with a false success flag, the requested command, the project in effect, a message, and a non-zero exit code.
- **AC-2**: Asking for machine-readable output with an unknown command produces the same structured failure with the command the user typed.
- **AC-3**: A non-numeric limit passed to a command produces the same structured failure instead of a traceback.
- **AC-4**: In human-readable mode the same failures print the message on the error stream and print no structured object.
- **AC-5**: Every command that acts on a project sends the selected project to the engine, and the reported project equals the sent one; a command that does not act on a project sends none.
- **AC-6**: Sending a task back with remarks that carry no text is refused with the same structured failure.
- **AC-7**: The whole test suite passes.

## Scope Boundaries

- The client stays a thin wrapper: it never invents engine behaviour and never reads project files itself.
- Only the failure report changes; successful answers keep their current shape.
- All committed artifacts are in English.

## Risks

- None stated.

## Open Questions

- None.

## Assumptions

- The next requirement is the first item of the recorded priority list: the project in all commands together with machine-readable argument errors.
- The project in effect for a failed invocation is the project stored in the client session, which is written only after the engine accepted it.
- The failure report keeps the field names the client already uses for a failed command, adding only the values that were previously empty.
- A command that lists projects is treated as not acting on a project.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-23 — Initial request recorded.
