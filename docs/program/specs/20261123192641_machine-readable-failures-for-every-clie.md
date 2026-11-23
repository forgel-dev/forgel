<!-- forgel:cancelled -->

> **Cancelled.** This task was cancelled. The runtime does not accept this requirements document for work.

# Task Spec: Machine-readable failures for every client command and a consistent selected project

## Document Information

| Field | Value |
|-------|-------|
| Feature | Machine-readable failures for every client command and a consistent selected project |
| Project | — |
| Task | `20261123192641_machine-readable-failures-for-every-clie` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T19:27:25+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

Failed invocations of the client's commands reach the user in inconsistent ways: an invocation can end through an unhandled argument error, a malformed numeric value can surface an internal error trace, a refusal reported by the engine can be presented as success, and some failures carry no record of which command was requested or which project was in effect. At the same time, the project a command acts on is not always consistently the project reported back to the caller, so the caller cannot tell which project was actually used.

**Outcome:** Every failed invocation of a client command ends deterministically: a non-zero exit status and, when machine-readable output is requested, exactly one structured failure report with nothing else in that output; when human-readable output is requested, a message on the error output and no structured report. No failed invocation ends through an unhandled argument error and no failed invocation shows an internal error trace. The failure report names the requested command and the project in effect whenever the invocation determines them, and leaves a value empty only where the invocation cannot determine it. Commands that act on a project always send the selected project to the engine and report back exactly that project; commands that do not act on a project send none. Successful answers are unchanged.

## Product Intent

The client is a thin presentation layer over the engine's parameterized commands: model access, the sandbox, independent QA, review and release approval stay in the engine (D-002, D-007). Callers and automation driving the client need a dependable contract — a failure is always a failure, always readable, and always attributable to a command and a project — otherwise scripting the client is unreliable.

## User Experience

A person using the client sees a plain message on the error output when something goes wrong, together with a non-zero exit status, with no internal error trace and no machine-readable noise. A script or automation asking for machine-readable output receives exactly one structured failure report per invocation with a false success indication, the command it asked for, the project in effect and a readable message, so it can branch on the outcome without reading prose. In both modes the project reported is the project that was actually used.

## Roadmap

—

## Goals

- Make every failed invocation of a client command a single, attributable, machine-readable failure with a non-zero exit status.
- Guarantee that the project sent to the engine and the project reported to the caller are always the same, and that project-less commands send nothing.
- Remove unhandled argument errors and internal error traces from the user-visible failure path.
- Keep every successful answer exactly as it is today.

## Non-Goals

- Changing the shape or content of any command's successful answer
- Adding new commands or new engine-side capabilities
- Changing engine behavior, engine-side failure semantics or engine-side project session rules
- Reworking human-readable success output or progress reporting
- Moving the interactive client into a separate repository or removing chat mode from the engine
- Introducing retries, fallbacks or automatic recovery from failed invocations
- Localizing messages into other languages

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, user 2026-11-16 18:31 |
| — | The base parameterized command line stays in the engine; the separate client replaces the interactive chat mode. | D-003, user 2026-11-16 18:31 |
| — | The client's working name is Forgel Code, a Python client with Pareto 20/80 scope that depends on nothing from the engine. | D-004, user 2026-11-16 18:34 |
| — | Every client-facing operation is a parameterized command with an optional single structured report as its answer, and the active project is an engine-side session with the default key `local`. | D-007, user 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: Every client command that acts on a project sends the selected project to the engine, and the project reported to the caller is exactly the project that was sent.
- **FR-2**: Every client command that does not act on a project sends no project to the engine and reports none.
- **FR-3**: Every failed invocation exits with a non-zero status. Failures include at least: an unknown command, a missing required argument, a numeric limit given a non-numeric value, remarks for a returned task that contain no text, and a refusal reported by the engine.
- **FR-4**: In machine-readable mode every failed invocation produces exactly one structured failure report in the machine-readable output and nothing else in that output.
- **FR-5**: That failure report carries a success indication set to false and a readable message stating what went wrong.
- **FR-6**: That failure report names the command the user asked for and the project in effect at the time of the invocation whenever the invocation determines them; a value stays empty only when the invocation itself cannot determine it.
- **FR-7**: In human-readable mode a failed invocation prints the readable message on the error output and produces no structured report.
- **FR-8**: No failed invocation ends through an unhandled argument error, and no failed invocation shows an internal error trace in either output mode.
- **FR-9**: A refusal reported by the engine remains a failure even when the engine itself reports success, and the failure report keeps the engine's own error details unchanged.
- **FR-10**: The successful answer of every command keeps its current shape and content, and successful invocations continue to exit with success.
- **FR-11**: Asking for machine-readable output with a missing required argument produces one structured failure report with a false success indication, the requested command, the project in effect and a readable message, and a non-zero exit status.
- **FR-12**: Asking for machine-readable output with an unknown command produces the same structured failure report, naming the command exactly as the user typed it.
- **FR-13**: A non-numeric limit passed to a command produces the same structured failure report instead of an internal error trace.
- **FR-14**: Returning a task with remarks that carry no text is refused with the same structured failure report and no request reaches the engine.
- **FR-15**: In human-readable mode each of these same failures prints the message on the error output, produces no structured report, and exits with a non-zero status.

## User Stories

- As a script author driving the client, I want every failure to be one machine-readable report with a false success indication and a non-zero exit status, so that I can branch on the outcome without reading prose.
- As a person using the client, I want a plain message on the error output and no internal error trace, so that I understand what went wrong.
- As a caller, I want the project reported back to be the project that was actually used, so that I never attribute work to the wrong project.
- As a maintainer, I want all commands to share one failure path, so that a new command cannot leak an unhandled argument error or an uncaught internal error.

## Acceptance Criteria

- **AC-1**: With machine-readable output requested and a required argument missing, the invocation exits non-zero and produces exactly one structured failure report carrying a false success indication, the requested command, the project in effect and a readable message.
- **AC-2**: With machine-readable output requested and an unknown command, the invocation exits non-zero and produces the same structured failure report, naming the command exactly as the user typed it.
- **AC-3**: A numeric limit given a non-numeric value produces the same structured failure report instead of an internal error trace.
- **AC-4**: Returning a task whose remarks contain no text produces the same structured failure report and no request reaches the engine.
- **AC-5**: In human-readable mode each of the above failures prints the message on the error output, produces no structured report, and exits non-zero.
- **AC-6**: Every command that acts on a project sends the selected project to the engine and reports exactly that project; every command that does not act on a project sends none.
- **AC-7**: A refusal reported by the engine whose own success indication is true is still reported as a failure, with the engine's own error details preserved.
- **AC-8**: Successful answers of every command keep their current shape and content and exit with success.
- **AC-9**: The failure message is readable and states what went wrong.
- **AC-10**: The whole test suite passes.

## Scope Boundaries

- Failure handling of every client command invocation in machine-readable mode
- Failure handling of every client command invocation in human-readable mode
- Exit status of failed invocations
- Failure report content: success indication, requested command, project in effect, readable message, engine refusal details
- Consistency between the project sent to the engine and the project reported to the caller
- Commands that do not act on a project refraining from sending any project
- Refusal of task returns whose remarks carry no text
- Validation of numeric limits before any engine interaction
- Changing the shape or content of any command's successful answer
- Adding new commands or new engine-side capabilities
- Changing engine behavior, engine-side failure semantics or engine-side project session rules
- Reworking human-readable success output or progress reporting
- Moving the interactive client into a separate repository or removing chat mode from the engine
- Introducing retries, fallbacks or automatic recovery from failed invocations
- Localizing messages into other languages

## Risks

- A change in the engine's own error details could make the machine-readable failure report less predictable for callers.
- The engine's refusal details vary between failures, so the failure report content varies while keeping a common core.
- If the requested command is not recoverable at the moment of failure, the failure report would lose it.
- Remarks containing only whitespace could still be accepted if the refusal covers only empty remarks.
- Changes to shared failure handling could alter behavior on which existing consumers rely.
- An invocation that fails validation could still reach the engine, changing engine-side state despite the failure.

## Open Questions

- None.

## Assumptions

- The project in effect is the project the invocation would have acted on, taken from the client's own selected project.
- For an unknown command the requested command name is known and is reported as typed; the project in effect is still reported, because it is determined without knowing the command.
- A value the invocation cannot determine is left empty rather than omitted.
- Exit statuses only need to be non-zero for failure; no specific non-zero value is prescribed.
- Human-readable output is the default, and machine-readable output is used only when the user requests it.
- The engine's own error details are carried into the failure report verbatim rather than re-worded.
- Remarks that consist only of whitespace carry no text and are refused like empty remarks.

## Related Documents

- README.md
- CHANGELOG.md
- releases/0.1.1/release.md

## Revision History

- 1.0 — initial specification of uniform machine-readable failures and consistent project selection.
- 1.1 — removed process and implementation detail from constraints, risks and assumptions; restated them as observable behavior.
