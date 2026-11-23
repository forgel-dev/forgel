# Agent Run: Forgel Code: interactive agent client instead of a command wrapper

- Task: `20261123193557_forgel-code-interactive-agent-client-ins`
- Status: `done`
- Repository: `code`
- Steps: 177
- Finished: 2026-11-23T21:19:32+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The work belongs to the client repository, whose contents match this feature and the surrounding conversation.
- The requirements above follow the intent of the named feature document and the client's documented contract; the document itself remains the source of truth where it is more specific.
- The interactive session becomes the default surface, while the one-shot usages stay available unchanged.
- The reference product is Claude Code, as recorded in the project decisions.
- A bare invocation with no arguments is the interactive session; `--help`, `--version` and every subcommand keep their previous behavior.
- The session resolves one sentence to at most one engine action (say, plan, accept, rework, retry, pause, resume, project switch or leave) and sends everything else to the engine's project agent verbatim.
- Sensitive intents (adoption, project creation, secrets, configuration) are recognised and pointed to the explicit commands instead of being forwarded, so free text can never trigger them.
- State is re-read from the engine before each prompt rather than on a timer, so the session shows current state without the owner asking and without a background thread that could outlive the session.
- Secret-looking values are replaced before anything is written to the session, and no transcript is written to disk.
- Replies are shown exactly as the engine produced them; the client only chooses the message language for its own session text from the owner's message.

## Test Removals

- tests/test_interactive.py::SessionFlowTest::test_switching_project_applies_to_later_requests: wrong -> tests/test_interactive.py::SessionFlowTest::test_switching_project_applies_to_later_requests

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 5
- Handoffs: 4
- Model calls: 177
- Estimated input tokens (all calls): 8415754
- Provider input/output tokens: 8709646 / 421191
- Provider cache hit/miss tokens: 8307968 / 401678
- Estimated prompt at the end: 66035 tokens
- State: `docs/program/agent/20261123193557_forgel-code-interactive-agent-client-ins.state.md`

## Specification (`docs/program/specs/20261123193557_forgel-code-interactive-agent-client-ins.md`)

# Task Spec: Forgel Code: interactive agent client instead of a command wrapper

## Document Information

| Field | Value |
|-------|-------|
| Feature | Forgel Code: interactive agent client instead of a command wrapper |
| Project | — |
| Task | `20261123193557_forgel-code-interactive-agent-client-ins` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T20:19:44+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client can only be used as a non-interactive command wrapper: every invocation needs a subcommand, and starting it bare is a usage error. The owner therefore cannot hold a conversation with the project agent, cannot see plan, task or release state continuously, and has to translate every intent into one specific command of their own. The milestone wants Forgel Code to be the interactive agent client, so an owner can launch it and work by writing sentences while the engine keeps doing all model, sandbox, QA, review and release work.

**Outcome:** Launching the client with no arguments opens an interactive session with a prompt that stays open until the owner leaves. Text written there reaches the engine's project agent as a free-form request and the reply is shown in the session. The session shows the selected project and allows switching it. Results appear as the agent produced them: a queued task with title and state, or a plan with its ordered tasks and their states. Task and release state stays visible and keeps updating without the owner asking for status. Accepting a task, sending one back with remarks, retrying a failed task, pausing and resuming work all work from plain-language input. A failure is shown with its concrete reason and next step, and the session stays usable. Replies follow the language of the owner's message. Adopting a repository, creating a project, secrets and configuration stay explicit separate actions that free text cannot trigger. Leaving the session ends it immediately with nothing half-started. Every existing one-shot usage keeps its previous output, including the machine-readable form. The client stays thin and never shows secrets.

## Product Intent

Forgel Code should be the owner's seat at the studio rather than a wrapper around a command line: the owner writes what they want in their own words, the engine's project agent answers and acts, and progress is visible without asking. The engine remains the only place where a model is called, files are read, checks are run, and review and release approval happen.

## User Experience

The owner starts Forgel Code without arguments and gets a prompt instead of usage text. They type a sentence, the project agent answers in the same language, and when the sentence turns into a plan or a task the answer shows the plan's ordered tasks or the new task with its title and state. The project name stays visible and can be changed by writing in the session; later answers concern the new project. Tasks and the release keep their current state on screen, so the owner watches work move instead of asking for a status. Accepting a finished task, sending one back with remarks, retrying a failure, pausing and resuming are all ordinary sentences. When something fails, the reason and the next step are on screen and the owner simply continues. Anything that adopts a repository, creates a project, stores a secret or changes configuration is still a separate deliberate action the owner must take, never a side effect of a sentence. Leaving ends the session at once. Every old one-shot usage behaves exactly as before.

## Roadmap

—

## Goals

- Bare invocation gives an interactive session instead of usage text.
- The owner works by writing sentences and receives the project agent's replies in the session.
- The selected project is visible and switchable without leaving the session.
- Plans, tasks and task states appear in the session as the agent produces them.
- Task and release state stay current on screen without asking for a status.
- Accept, send back with remarks, retry, pause and resume are available as plain language in the session.
- Failures are explained with a cause and a next step, and the session continues.
- Replies follow the owner's language.
- Adoption, project creation, secrets and configuration stay explicit separate actions.
- Leaving ends the session immediately with nothing half-started.
- One-shot usages and their machine-readable output are unchanged.
- The client stays thin and never exposes secrets.

## Non-Goals

- Changing, extending or reimplementing any engine capability
- Moving engine-side model access, sandbox, QA, review or release approval into the client
- Removing the replaced chat mode from the engine (a later step of the milestone)
- Changing the engine's parameterized command line
- A graphical, web or mobile interface
- Persisting or exporting session transcripts
- Machine-readable output for the interactive session itself
- Voice input or any interpretation of the owner's intent done inside the client beyond choosing the action to ask the engine for

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-001: The interactive client moves to a separate public repository in the same organization as the engine. | User decision log, User 2026-11-16 21:14 |
| — | D-002: The client is a thin UI over the engine's parameterized commands. It does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | User decision log, User 2026-11-16 18:31 |
| — | D-003: The base parameterized command line stays in the engine. The separate client replaces the interactive chat mode. | User decision log, User 2026-11-16 18:31 |
| — | D-004: The client's working name is Forgel Code; it follows a Pareto 20/80 scope and is independent of the engine rather than importing it. | User decision log, User accepted the proposal 2026-11-16 18:34 |
| — | D-006: The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User decision log, User accepted the proposal 2026-11-16 18:34 |
| — | D-007: The single free-text engine entry point is the engine's own free-text operation; every client-facing operation is a parameterized command with an optional single machine-readable answer, and the active project is an engine-side session with the default key `local`. | User decision log, User accepted the proposal 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: Starting the client with no arguments opens an interactive session, shows a prompt and keeps the session open until the owner leaves; usage or help text is never printed in its place.
- **FR-2**: Text the owner writes in the session is sent to the engine's project agent as one free-form request, and the agent's reply is shown in the session.
- **FR-3**: The session shows which project is currently selected; the owner can switch to another project from inside the session without leaving it, and every later request and displayed state concerns the newly selected project.
- **FR-4**: When a request becomes a queued task, the session shows that task with its title and its state.
- **FR-5**: When a request becomes a plan, the session shows the plan's tasks in their planned order together with each task's state.
- **FR-6**: The session keeps the current state of the tasks and the current state of the release visible and refreshes them on its own, so the owner follows progress without asking for a status again.
- **FR-7**: Accepting a finished task, sending a task back with remarks, retrying a failed task, pausing work and resuming work can each be asked for in plain language inside the session and are carried out, and the resulting state is shown in the session.
- **FR-8**: When an operation fails, the session shows the concrete reason and the next possible step, and remains usable for the next request.
- **FR-9**: Every reply shown in the session is in the language of the owner's message.
- **FR-10**: When a plain-language request matches no available action or more than one, the session asks the owner to clarify instead of performing any action.
- **FR-11**: Adopting a repository, creating a project, setting or changing a secret, and changing configuration are never carried out from a plain-language sentence alone; they remain explicit separate actions, and the session may at most point the owner to them.
- **FR-12**: Leaving the session ends it immediately: the client stops acting on the owner's behalf, no request continues after the session ends, and the session ends the same way when the input ends.
- **FR-13**: Every existing non-interactive usage keeps its previous behavior, output and exit status, including the machine-readable form.
- **FR-14**: The client stays thin: it does not call a model, does not read project files and does not run checks itself; every answer and every piece of state comes from the engine.
- **FR-15**: Secrets, tokens and key material never appear in the session, in any message the session shows, or in anything the client keeps for the session.

## User Stories

- As the owner I want to start the client and land in a conversation, so that I can work without translating my intent into commands.
- As the owner I want the agent's reply in the language I wrote in, so that the session reads naturally to me.
- As the owner I want to see which project I am in and switch it while talking, so that I do not restart the client for another project.
- As the owner I want a plan shown with its ordered tasks and their states, so that I can see the shape of the work the agent proposed.
- As the owner I want task and release state to stay current on screen, so that I follow progress without asking for a status.
- As the owner I want to accept, send back with remarks, retry, pause and resume by writing a sentence, so that driving the work fits the conversation.
- As the owner I want a failure explained with a reason and a next step, so that I can continue in the same session.
- As the owner I want adopting a repository, creating a project, secrets and configuration to stay separate deliberate actions, so that a stray sentence cannot change my setup.
- As the owner I want leaving to end the session at once, so that nothing keeps running behind my back.
- As a scripter I want every existing one-shot usage, including the machine-readable one, to behave exactly as before, so that my automation keeps working.

## Acceptance Criteria

- **AC-1**: Starting the client with no arguments shows a prompt and keeps the session open; no usage or help text appears in its place.
- **AC-2**: A phrase typed at the prompt is answered by the agent inside the session and the session stays open afterwards.
- **AC-3**: A request that becomes a plan shows its tasks in plan order with their states in the session.
- **AC-4**: A request that becomes a task shows the task, its title and its state in the session.
- **AC-5**: Task and release state updates become visible in the session without the owner asking for a status.
- **AC-6**: Accepting a finished task and sending a task back with remarks both work from plain language inside the session.
- **AC-7**: Retrying a failed task, pausing work and resuming work all work from plain language inside the session.
- **AC-8**: A failure is shown with a concrete cause and a next possible step, and the session accepts the next request without being restarted.
- **AC-9**: Switching the selected project happens inside the session and later answers concern the newly selected project.
- **AC-10**: Adopting a repository, creating a project, setting a secret and changing configuration cannot be triggered by a free-text sentence alone.
- **AC-11**: A request that matches no available action or several produces a clarification and performs no action.
- **AC-12**: One-shot usages still produce their previous output, exit status and machine-readable form.
- **AC-13**: Leaving ends the session immediately and nothing half-started remains on the client's side.
- **AC-14**: No secret appears in the session transcript or in any message the session shows.
- **AC-15**: Replies follow the language of the owner's message.

## Scope Boundaries

- An interactive session when the client is started with no arguments
- Free-form requests forwarded to the engine's project agent and the agent's replies shown in the session
- Showing the selected project in the session and switching it from inside the session
- Showing a queued task with its title and state, and a plan with its ordered tasks and their states
- Continuously visible and self-updating task and release state in the session
- Plain-language accept, send back with remarks, retry of a failed task, pause and resume inside the session
- Failure presentation with a concrete reason and a next step, with the session staying usable
- Replies in the language of the owner's message
- Keeping adoption, project creation, secrets and configuration as explicit separate actions that free text cannot trigger
- Immediate end of the session on leaving, with nothing half-started in the client
- Unchanged behavior of every existing one-shot usage, including the machine-readable output
- A thin client that neither calls a model, nor reads project files, nor runs checks
- Never showing secrets, tokens or key material in the session
- Changing, extending or reimplementing any engine capability
- Moving engine-side model access, sandbox, QA, review or release approval into the client
- Removing the replaced chat mode from the engine (a later step of the milestone)
- Changing the engine's parameterized command line
- A graphical, web or mobile interface
- Persisting or exporting session transcripts
- Machine-readable output for the interactive session itself
- Voice input or any interpretation of the owner's intent done inside the client beyond choosing the action to ask the engine for

## Risks

- Reply language is produced by the engine, not by the client: if the engine answers in another language, the client can only pass the owner's text through, so the language criterion depends on the engine's behavior.
- A real engine may not be present during verification, so most behavior can only be proven against the engine behavior the project already records rather than against a live engine.
- Continuous refresh can keep the engine busy while the owner is not writing; refreshing too often adds load, refreshing too rarely leaves the screen stale.
- Free text must not be able to trigger adoption, project creation, secrets or configuration; a permissive reading of a sentence could silently widen what it can do.
- Making a bare start interactive can change how existing invocations are read and can break their machine-readable output if the interactive flow leaks into them.
- An engine call may outlive the session when the owner leaves, which would leave work half-started on the client's side.
- Choosing the action for a sentence inside the client can drift into interpreting intent the engine should own; overreach here would contradict the thin-client decision.
- A failure shown only as the engine's raw wording would not give the owner a concrete reason and a next step.

## Open Questions

- None.

## Assumptions

- Leaving the session means the owner asking to leave in plain language; the end of the input ends the session the same way.
- The engine produces the reply in the owner's language; the client displays it as received.
- State refresh happens without the owner asking; how often is a reversible detail.
- A plain-language request is matched to one available action; carrying it out and its outcome belong to the engine.
- A project switch takes effect only if the engine accepts the project; otherwise the previous selection stays and the refusal is reported as a failure.
- The engine keeps answering each operation in the machine-readable form the project already relies on, with a structured answer for a refused or failed operation, so the client reads results instead of human wording.
- Where the real engine is unavailable during verification, the engine behavior the project already records stands in for it.

## Related Documents

- README.md
- FORGEL.md
- AGENTS.md
- releases/0.1.1/plan.md
- releases/0.1.1/release.md

## Revision History

- v1 — initial specification for the interactive-session task
- v2 — removed implementation wording from constraints, risks and assumptions; every command check runs inside the client repository


## Summary

Completed the interactive agent client for Forgel Code, continuing from the previous attempt whose only unresolved failure was a wrong premise in one test. The changes: `forgel_code/commands.py` (single table translating a client intent into the engine's own argv, shared by the one-shot surface and the session), `forgel_code/interactive.py` (the interactive session: prompt that stays open, free-form requests forwarded to the engine's project agent, selected project shown and switchable inside the session, plans shown in plan order with states, tasks shown with title and state, self-refreshing task and release state, plain-language accept/rework/retry/pause/resume, failures shown with cause and next step while the session stays usable, clarification when a sentence matches no action or several, sensitive intents refused, secret redaction, immediate end on leave or end of input, replies following the owner's language, no model/project-file/check work in the client), `forgel_code/cli.py` (a bare invocation opens the session instead of printing usage; every one-shot command, its output, exit status and `--json` form unchanged), `tests/test_interactive.py` (coverage of every acceptance criterion against a stand-in engine that speaks the engine's machine-readable form), and documentation of the new default surface in `README.md` and `CHANGELOG.md`. The remaining failure was in the test itself: it asserted that the very first engine call of the session is the project switch, but the session re-reads task and release state before every prompt, so a state read legitimately precedes the switch. The assertion now locates the switch call and checks that every project-scoped call after it carries the new key, which is what the requirement actually says. No earlier work was repeated. Tested with `python -m unittest tests.test_interactive` (37 tests, OK), `python -m unittest discover -s tests -t .` (255 tests, OK) and the packaging tests (16 tests, OK).

## Files Changed

- `CHANGELOG.md`
- `README.md`
- `forgel_code/cli.py`
- `forgel_code/commands.py`
- `forgel_code/interactive.py`
- `tests/test_interactive.py`

## Commands

- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-p", "test_interactive.py"]` → exit 5
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python", "-m", "unittest", "tests.test_interactive"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python", "-m", "unittest", "tests.test_packaging", "tests.test_packaging_types"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
...............................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 255 tests in 189.105s

OK

```

## Actions

- read_file: forgel_code/session.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/render.py
- read_file: tests/stub_engine.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_extras.py
- read_file: README.md
- read_file: tests/test_stub_contract.py
- read_file: tests/test_packaging.py
- read_file: CHANGELOG.md
- read_file: forgel_code/__main__.py
- read_file: tests/test_readme_install.py
- read_file: tests/test_readme_install.py
- write_file: forgel_code/commands.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/commands.py
- write_file: forgel_code/commands.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/engine.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- recall
- read_file: tests/test_cli_extra.py
- read_file: forgel_code/session.py
- read_file: forgel_code/__main__.py
- read_file: README.md
- list_files
- read_file: CHANGELOG.md
- read_file: tests/test_extras.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- run: ['python', '-m', 'unittest', 'tests.test_interactive']
- read_file: tests/test_interactive.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-p', 'test_interactive.py']
- read_file: forgel_code/interactive.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/engine.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- list_files
- read_file: forgel_code/__main__.py
- read_file: forgel_code/session.py
- read_file: tests/stub_engine.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_stub_contract.py
- read_file: forgel_code/render.py
- read_file: tests/test_extras.py
- read_file: pyproject.toml
- read_file: tests/test_install.py
- read_file: README.md
- read_file: tests/test_readme_install.py
- list_files
- read_file: forgel_code/interactive.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/__main__.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/engine.py
- recall
- read_file: tests/stub_engine.py
- read_file: tests/test_cli_extra.py
- recall
- read_file: forgel_code/session.py
- read_file: forgel_code/render.py
- read_file: tests/test_packaging.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/cli.py
- write_file: tests/test_interactive.py
- run: ['python', '-m', 'unittest', 'tests.test_interactive']
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- run: ['python', '-m', 'unittest', 'tests.test_interactive']
- read_file: forgel_code/commands.py
- read_file: forgel_code/engine.py
- write_file: tests/test_interactive.py
- run: ['python', '-m', 'unittest', 'tests.test_interactive']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- read_file: forgel_code/cli.py
- read_file: README.md
- read_file: CHANGELOG.md
- run: ['git', 'status', '--porcelain']
- read_file: pyproject.toml
- read_file: _build_backend.py
- read_file: forgel_code/session.py
- read_file: tests/test_readme_install.py
- write_file: README.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- write_file: CHANGELOG.md
- run: ['python', '-m', 'unittest', 'tests.test_packaging', 'tests.test_packaging_types']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- run: ['git', 'status', '--porcelain']
