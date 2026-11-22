# Feature: Forgel Code interactive agent client

## Document Information

| Field | Value |
|-------|-------|
| Feature | Forgel Code interactive agent client |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | `code` |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-22T00:00:00+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

Forgel Code is a simplified Claude Code: an interactive terminal agent client
that replaces the engine's chat mode. The engine remains the runtime — it owns
the model, the sandbox, QA, review, release and deploy gates. The client owns
the interactive surface: the conversation, the rendered answers and actions,
task and release progress, and the user's decisions.

The parameterized `forgel` commands are the transport between the client and
the engine. A command-wrapper CLI is a transport layer, not this product.

## Product Intent

The owner wants an interactive agent client modeled on Claude Code, scoped to
the 20% of the experience that does 80% of the work. The client should feel
like a conversation with an agent that performs the work through Forgel:
describe the task, watch the agent act, see the result, accept or send work
back, and follow the release. The engine stays the runtime; the client is the
UI.

## User Experience

- `forgel-code` with no arguments opens an interactive chat in the terminal.
- A free-text message goes to the active engine session; the reply, the
  actions taken and the resulting task or release are rendered in the chat.
- Status, tasks, acceptance, rework, pause and resume are available from the
  chat without a second parameterized command surface.
- Long work shows progress: the active task, its stage, its checks and the
  release state. The user is never left with a silent prompt.
- A release ends the conversation with the released version, the repository
  and the publication state.
- Scripted subcommands remain available for automation, but they are not the
  default product surface.

## Goals

- Add an interactive chat/REPL mode as the default `forgel-code` surface.
- Define the engine session/stream the client uses: send a message, receive
  the reply and the action/task/release events, and read the session state.
- Render the agent's actions, task progress and release outcome in the chat.
- Expose status, tasks, accept, rework, pause and resume as chat commands.
- Keep the scripted subcommands working for automation.
- Test the chat flow with a stub engine and keep the existing tests green.

## Non-Goals

- The client does not call a model directly, run project checks or edit code.
- The client is not a second engine and does not own the sandbox or the task
  pipeline.
- The client does not deploy or approve production; those remain human gates
  in the engine.
- The parameterized command set is not expanded as a product surface.

## Functional Requirements

- **FR-1**: `forgel-code` with no arguments opens an interactive chat.
- **FR-2**: A free-text message is sent to the active engine session; the
  client renders the engine's reply, the resulting kind (answer, task, plan or
  release) and the identifiers the engine returns.
- **FR-3**: While a task or release is active, the client shows its state and
  updates it until the user continues or the work reaches a human gate.
- **FR-4**: The chat exposes status, tasks, accept, rework, pause, resume,
  project selection and quit without requiring a second CLI surface.
- **FR-5**: The engine session is durable and selected by project; the client
  keeps no project state of its own.
- **FR-6**: Scripted subcommands remain available and keep their machine
  output for automation.
- **FR-7**: The client never imports the engine, calls a model, reads project
  files or runs checks.

## Technical Requirements

- The client talks to the engine only through its machine-readable commands.
- The engine exposes a session/stream suitable for an interactive client; if
  the first slice cannot stream, it polls `say`, `history` and `status` with
  an explicit progress interval, and the follow-up replaces polling with a
  stream without changing the client's surface.
- The chat has no third-party dependencies beyond the standard library.
- Rendering is terminal-oriented: plain text, stable line handling, no raw
  JSON dumps.
- Public artifacts are in English; chat replies follow the user's language.

## User Stories

- As the owner, I run `forgel-code` and land in a chat, describe a change, and
  see the agent's work and the result without remembering engine commands.
- As the owner, I can accept or send back a task from the chat and follow the
  release that follows.
- As an automation author, I can still call the scripted subcommands and parse
  their JSON.

## Tests

- A stub engine drives the chat: a message produces a rendered reply and a
  task; status and rework are reachable from the chat.
- `forgel-code` with no arguments enters the chat and exits cleanly.
- The existing scripted-command tests still pass.

## Acceptance Criteria

- **AC-1**: `forgel-code` with no arguments opens the chat prompt.
- **AC-2**: Sending a free-text message reaches the engine session and renders
  the reply, the kind and the task or plan identifier.
- **AC-3**: An active task's state is shown and refreshed until it reaches a
  human gate or a release.
- **AC-4**: Status, tasks, accept, rework, pause, resume, project selection and
  quit work from the chat.
- **AC-5**: The scripted subcommands and their JSON output are unchanged.
- **AC-6**: The client imports nothing from the engine and calls no model.

## Scope Boundaries

- The engine owns the model, sandbox, QA, review, release train and deploy
  gates.
- The client owns the terminal conversation and rendering.
- Production approval and deploy remain human gates in the engine.
- The transport subcommands stay; the interactive chat is the product.

## Risks

- The engine session may not stream in the first slice; polling must still
  show progress and end at a human gate.
- A chat that hides engine actions would be a status reader, not an agent
  client; the rendering must show what the runtime actually did.

## Open Questions

- Whether the engine session/stream should be a new command or an extension
  of `say`, `history` and `status`.

## Affected Files

- `forgel_code/cli.py` (default chat entry)
- `forgel_code/chat.py` (new)
- `forgel_code/engine.py`
- `forgel_code/render.py`
- `tests/` for the chat flow
- engine: session/stream command when the first slice needs it

## Assumptions

- The engine's machine-readable commands remain the only transport.
- The client's first release may poll for progress; streaming is a follow-up.
- The scripted subcommands stay for automation and compatibility.

## Related Documents

- `docs/program/decisions.md` (D-001, D-002, D-003, D-103)
- `docs/program/commands.md`
- `PLAN.md` §7.18

## Revision History

- 1.0.0 — 2026-11-22 — Product definition corrected: interactive agent client
  over the engine; the command wrapper is the transport, not the product.
