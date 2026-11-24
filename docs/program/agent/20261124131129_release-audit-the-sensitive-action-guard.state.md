# Session State: Release audit: The sensitive-action guard is incomplete for required explicit actions. `SENSITI

- Task: `20261124131129_release-audit-the-sensitive-action-guard`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- A free-text request that asks to create, set or change key material is refused, including requests that use only the bare key wording rather than a credential term, in English and in Russian.
- A free-text request that asks to change configuration is refused, including requests that use only the bare configuration wording, in English and in Russian.
- A free-text request that asks to create or scaffold a project is refused, including requests phrased with the bare scaffolding wording, in English and in Russian.
- A refused request is not sent to the engine: the client makes no engine request for it and reports no action result.
- The refusal tells the user that the requested action needs the dedicated explicit operation, and names the operation to use, so the user can act without guessing.
- The refusal is presented in the language the rest of the interface uses for that user.
- Requests outside the guarded categories continue to be forwarded to the engine exactly as before, and no existing refusal is narrowed or lost.
- Automated tests assert, for every recognized form in each covered language and category, that the request is refused and that no engine request is made.
- The existing test suite passes unchanged in meaning: no test is weakened or deleted to accommodate the new behavior.

## Acceptance Criteria

- Typing a free-text request to change configuration, in English or in Russian, is refused in the client and no engine request is made.
- Typing a free-text request to create or set key material, including the bare key wording, in English or in Russian, is refused and no engine request is made.
- Typing a free-text project creation or scaffolding request, including the bare scaffolding wording, in English or in Russian, is refused and no engine request is made.
- Each refusal names the explicit operation the user should use to perform the action.
- The refusal appears in the interface language of the session.
- Ordinary conversational messages that are not requests of the guarded categories still reach the engine and are answered as before.
- Automated tests cover every listed form and assert both the refusal and the absence of an engine request.
- The full existing test suite passes.

## Constraints

- none

## Assumptions

- none

## Files Changed

- forgel_code/interactive.py

## Actions

- read_file: forgel_code/commands.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- read_file: tests/test_localization.py
- read_file: CHANGELOG.md
- read_file: forgel_code/cli.py
- read_file: README.md
- read_file: tests/test_extras.py
- run: ['python', '-c', 'print(1)']
- read_file: releases/0.1.1/release.md
- read_file: tests/stub_engine.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_idle_refresh.py
- write_file: forgel_code/interactive.py

## Commands

- `['python', '-c', 'print(1)']` -> exit 0

## Recent Observations

- read_file tests/test_cli_extra.py: tests/test_cli_extra.py: lines 1-120 of 216
- read_file tests/test_idle_refresh.py: tests/test_idle_refresh.py: lines 1-314 of 314
- write_file forgel_code/interactive.py

## Next Step

Continue from the current repository state and the changed files.
