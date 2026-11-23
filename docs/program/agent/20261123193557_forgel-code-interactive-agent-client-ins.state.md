# Session State: Forgel Code: interactive agent client instead of a command wrapper

- Task: `20261123193557_forgel-code-interactive-agent-client-ins`
- Session: 4
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- Starting the client with no arguments opens an interactive session, shows a prompt and keeps the session open until the owner leaves; usage or help text is never printed in its place.
- Text the owner writes in the session is sent to the engine's project agent as one free-form request, and the agent's reply is shown in the session.
- The session shows which project is currently selected; the owner can switch to another project from inside the session without leaving it, and every later request and displayed state concerns the newly selected project.
- When a request becomes a queued task, the session shows that task with its title and its state.
- When a request becomes a plan, the session shows the plan's tasks in their planned order together with each task's state.
- The session keeps the current state of the tasks and the current state of the release visible and refreshes them on its own, so the owner follows progress without asking for a status again.
- Accepting a finished task, sending a task back with remarks, retrying a failed task, pausing work and resuming work can each be asked for in plain language inside the session and are carried out, and the resulting state is shown in the session.
- When an operation fails, the session shows the concrete reason and the next possible step, and remains usable for the next request.
- Every reply shown in the session is in the language of the owner's message.
- When a plain-language request matches no available action or more than one, the session asks the owner to clarify instead of performing any action.
- Adopting a repository, creating a project, setting or changing a secret, and changing configuration are never carried out from a plain-language sentence alone; they remain explicit separate actions, and the session may at most point the owner to them.
- Leaving the session ends it immediately: the client stops acting on the owner's behalf, no request continues after the session ends, and the session ends the same way when the input ends.
- Every existing non-interactive usage keeps its previous behavior, output and exit status, including the machine-readable form.
- The client stays thin: it does not call a model, does not read project files and does not run checks itself; every answer and every piece of state comes from the engine.
- Secrets, tokens and key material never appear in the session, in any message the session shows, or in anything the client keeps for the session.

## Acceptance Criteria

- Starting the client with no arguments shows a prompt and keeps the session open; no usage or help text appears in its place.
- A phrase typed at the prompt is answered by the agent inside the session and the session stays open afterwards.
- A request that becomes a plan shows its tasks in plan order with their states in the session.
- A request that becomes a task shows the task, its title and its state in the session.
- Task and release state updates become visible in the session without the owner asking for a status.
- Accepting a finished task and sending a task back with remarks both work from plain language inside the session.
- Retrying a failed task, pausing work and resuming work all work from plain language inside the session.
- A failure is shown with a concrete cause and a next possible step, and the session accepts the next request without being restarted.
- Switching the selected project happens inside the session and later answers concern the newly selected project.
- Adopting a repository, creating a project, setting a secret and changing configuration cannot be triggered by a free-text sentence alone.
- A request that matches no available action or several produces a clarification and performs no action.
- One-shot usages still produce their previous output, exit status and machine-readable form.
- Leaving ends the session immediately and nothing half-started remains on the client's side.
- No secret appears in the session transcript or in any message the session shows.
- Replies follow the language of the owner's message.

## Constraints

- The client remains a thin client: the model, the sandbox, independent checks, review, acceptance and releases stay in the engine.
- Existing one-shot usage and its machine-readable output do not change.
- Sensitive state — adoption, project creation, secrets, configuration — stays under explicit owner action.
- The interactive session never displays secret or token material.
- The interactive session is available from the same one-command installation the client already has.
- Project artifacts are written in English; replies follow the owner's language.
- A published release tag is never rewritten.

## Assumptions

- The work belongs to the client repository, whose contents match this feature and the surrounding conversation.
- The requirements above follow the intent of the named feature document and the client's documented contract; the document itself remains the source of truth where it is more specific.
- The interactive session becomes the default surface, while the one-shot usages stay available unchanged.
- The reference product is Claude Code, as recorded in the project decisions.

## Files Changed

- forgel_code/cli.py
- forgel_code/commands.py
- forgel_code/interactive.py
- tests/test_interactive.py

## Actions

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

## Commands

- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 1
- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 0
- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 0
- `['python', '-m', 'unittest', 'tests.test_interactive']` -> exit 1
- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-p', 'test_interactive.py']` -> exit 5
- `['python', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 0
- `['python', '-m', 'unittest', 'tests.test_interactive']` -> exit 1

## Recent Observations

- write_file tests/test_interactive.py
- run python -m unittest tests.test_interactive -> exit 1
- write_file forgel_code/interactive.py

## Next Step

Continue from the current repository state and the changed files.
