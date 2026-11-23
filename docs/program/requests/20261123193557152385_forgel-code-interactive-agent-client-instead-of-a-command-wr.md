# Feature: Forgel Code: interactive agent client instead of a command wrapper

## Document Information

| Field | Value |
|-------|-------|
| Feature | Forgel Code: interactive agent client instead of a command wrapper |
| Project | `forgel-1d2bf685` |
| Task | — |
| Plan | — |
| Repository | — |
| Depends on | — |
| Status | New |
| Version | 1.0.0 |
| Created | 2026-11-23T19:35:57+00:00 |
| Source | Local console request (local) |
| Author | Forgel project agent |

## Overview

The Forgel Code client stops being only a set of one-shot, argument-driven wrappers. Opened without arguments it starts an interactive session in which the owner describes work in plain language, reads the agent's answers, follows the plan and the progress of tasks and releases, and accepts work or sends it back with remarks without leaving the session. Adopting a repository, creating a project, secrets and configuration stay explicit. One-shot scripted usage and its machine-readable output remain unchanged, and the client stays thin: the model, the sandbox, independent checks, review and releases stay in the engine. The requirements below follow the existing feature document named by the owner and the client's documented contract; they are behaviour, not implementation.

## Product Intent

Forgel Code should be the Forgel equivalent of Claude Code: one interactive session in which the owner talks to the agent, watches the work happen and decides, rather than a collection of one-shot command wrappers. The parameterized client commands are the transport, not the product.

## User Experience

The owner runs the client with no arguments and gets a prompt instead of help text. From that prompt they describe a change or ask what is happening, read the agent's answer, see the plan it produced and the state of its tasks and release, and watch that state move forward without retyping a status request. Saying they accept a task, or that it should go back with a remark, works from the same prompt, as do pausing and resuming work and switching the selected project. Adopting a repository, creating a new project, secrets and configuration remain explicit actions, never performed from free text alone. Leaving the session is one plain action. The one-shot, argument-driven usage and its machine-readable output keep working exactly as today. This replaces the current default surface, where the client only ever performs a single argument-driven operation per run.

## Roadmap

- None stated.

## Goals

- Starting the client with no arguments opens an interactive session and keeps it open until the owner leaves, instead of printing usage help.
- Text the owner writes in the session reaches the engine's project agent as a free-form request, and the agent's reply is shown in the session.
- The session shows which project is currently selected and lets the owner switch to another project without leaving the session.
- When a request becomes a queued task, the session shows the task, its title and its state.
- When a request becomes a plan, the session shows the ordered tasks of that plan and their states.
- The session keeps the current state of tasks and of the release on screen so the owner can follow progress without asking for a status again.
- The owner can accept a finished task, send a task back with remarks, retry a failed task, pause work and resume work by writing in plain language inside the session.
- A failure is presented with its concrete reason and the next possible step, and the session stays usable afterwards.
- Every reply follows the language of the owner's message.
- Adopting a repository, creating a project, secrets and configuration remain explicit, separate actions and are never carried out from free text alone.
- Leaving the session ends it immediately without leaving work half-started in the client.
- All existing one-shot usages continue to behave exactly as before, including their machine-readable output.
- The client stays thin: it does not call a model, does not read project files and does not run checks itself.
- Secrets, tokens and key material never appear in the session output.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- **FR-1**: Starting the client with no arguments opens an interactive session and keeps it open until the owner leaves, instead of printing usage help.
- **FR-2**: Text the owner writes in the session reaches the engine's project agent as a free-form request, and the agent's reply is shown in the session.
- **FR-3**: The session shows which project is currently selected and lets the owner switch to another project without leaving the session.
- **FR-4**: When a request becomes a queued task, the session shows the task, its title and its state.
- **FR-5**: When a request becomes a plan, the session shows the ordered tasks of that plan and their states.
- **FR-6**: The session keeps the current state of tasks and of the release on screen so the owner can follow progress without asking for a status again.
- **FR-7**: The owner can accept a finished task, send a task back with remarks, retry a failed task, pause work and resume work by writing in plain language inside the session.
- **FR-8**: A failure is presented with its concrete reason and the next possible step, and the session stays usable afterwards.
- **FR-9**: Every reply follows the language of the owner's message.
- **FR-10**: Adopting a repository, creating a project, secrets and configuration remain explicit, separate actions and are never carried out from free text alone.
- **FR-11**: Leaving the session ends it immediately without leaving work half-started in the client.
- **FR-12**: All existing one-shot usages continue to behave exactly as before, including their machine-readable output.
- **FR-13**: The client stays thin: it does not call a model, does not read project files and does not run checks itself.
- **FR-14**: Secrets, tokens and key material never appear in the session output.

## User Stories

- None stated.

## Acceptance Criteria

- **AC-1**: Running the client with no arguments yields a prompt, not usage text.
- **AC-2**: A phrase typed at the prompt is answered by the agent inside the session.
- **AC-3**: A request that becomes a plan shows its ordered tasks and their states in the session.
- **AC-4**: A request that becomes a task shows the task, its title and its state in the session.
- **AC-5**: Task and release state updates become visible in the session without the owner asking for status.
- **AC-6**: Accepting a task and sending one back with remarks both work from the session with plain language.
- **AC-7**: Retrying a failed task, pausing and resuming work all work from the session.
- **AC-8**: A failure is shown with a concrete cause and the session remains usable.
- **AC-9**: Switching the selected project happens inside the session and later answers concern the newly selected project.
- **AC-10**: Adopting a repository, creating a project, setting a secret and changing configuration cannot be triggered by a free-text sentence alone.
- **AC-11**: One-shot usages still produce their previous output, including the machine-readable form.
- **AC-12**: No secret appears in the session transcript or in any message.
- **AC-13**: Replies follow the language of the owner's message.

## Scope Boundaries

- The client remains a thin client: the model, the sandbox, independent checks, review, acceptance and releases stay in the engine.
- Existing one-shot usage and its machine-readable output do not change.
- Sensitive state — adoption, project creation, secrets, configuration — stays under explicit owner action.
- The interactive session never displays secret or token material.
- The interactive session is available from the same one-command installation the client already has.
- Project artifacts are written in English; replies follow the owner's language.
- A published release tag is never rewritten.

## Risks

- None stated.

## Open Questions

- None.

## Assumptions

- The work belongs to the client repository, whose contents match this feature and the surrounding conversation.
- The requirements above follow the intent of the named feature document and the client's documented contract; the document itself remains the source of truth where it is more specific.
- The interactive session becomes the default surface, while the one-shot usages stay available unchanged.
- The reference product is Claude Code, as recorded in the project decisions.

## Related Documents

- `docs/program/decisions.md`
- `docs/program/state.md`

## Revision History

- 1.0.0 — 2026-11-23 — Initial request recorded.
