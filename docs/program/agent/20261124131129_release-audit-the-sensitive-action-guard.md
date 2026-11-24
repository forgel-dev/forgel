# Agent Run: Release audit: The sensitive-action guard is incomplete for required explicit actions. `SENSITI

- Task: `20261124131129_release-audit-the-sensitive-action-guard`
- Status: `done`
- Repository: `code`
- Steps: 49
- Finished: 2026-11-24T14:01:15+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The guard keys on an action verb plus the guarded object rather than on a lone noun, because the specification's Risks section forbids refusing a sentence that merely mentions a key, configuration or project; the Russian object is therefore matched by stem (inflected forms) and the English object by listed word.
- The existing single refusal message key `sensitive` was extended instead of adding per-category messages, because the Non-Goals rule out redesigning refusal wording and the message already carries the structure (statement + explicit command) the acceptance criteria ask for; one message names all guarded families and the explicit operation.
- The refusal names the client's own explicit command surface `forgel-code`, which is the operation surface the client exposes for these actions, so the user can act without guessing.
- The `CHANGELOG.md` entry is the release-notes part this change requires; no other documentation was touched.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 49
- Estimated input tokens (all calls): 2161547
- Provider input/output tokens: 2209297 / 130961
- Provider cache hit/miss tokens: 2085760 / 123537
- Estimated prompt at the end: 63471 tokens
- State: `docs/program/agent/20261124131129_release-audit-the-sensitive-action-guard.state.md`

## Specification (`docs/program/specs/20261124131129_release-audit-the-sensitive-action-guard.md`)

# Task Spec: Release audit: The sensitive-action guard is incomplete for required explicit actions. `SENSITI

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The sensitive-action guard is incomplete for required explicit actions. `SENSITI |
| Project | — |
| Task | `20261124131129_release-audit-the-sensitive-action-guard` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T13:35:34+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client lets the user type free text that is forwarded to the engine as an ordinary conversational request. Some free-text requests ask for actions the product reserves for explicit operations: setting or creating key material, changing configuration, and creating or scaffolding a project. The guard that should stop those requests does not recognize bare key/credential wording, bare configuration wording, or project-scaffolding wording, so such requests pass through to the engine as ordinary conversation. No automated test proves that these forms are refused and never reach the engine.

**Outcome:** Free-text requests to set or create key material, to change configuration, or to create/scaffold a project are recognized in both interface languages, including the bare wording forms. Such requests are refused in the client: the user is told the action needs the dedicated explicit operation and receives no action result, and nothing is sent to the engine for them. Requests outside those categories behave exactly as before. Automated tests assert both the refusal and the absence of any engine request for each of these forms.

## Product Intent

The client is a thin conversational front end over parameterized engine operations (D-002, D-007). Sensitive actions — key material, configuration changes, project creation/scaffolding — must never be triggered by free text alone; free text may only reach the conversational entry point. The guard is the product's enforcement of that boundary, so its coverage of the named actions must be complete.

## User Experience

A user who types something like 'change config', 'create a key', 'создай ключ' or 'scaffold a project' is stopped immediately with a short message explaining that this action requires the explicit operation, instead of receiving an unrelated conversational answer or a silent no-op. The user is not left believing the action happened. Everything else the user types continues to be answered as before.

## Roadmap

—

## Goals

- Close the guard coverage gap for key material, configuration change and project creation/scaffolding, including the bare wording forms, in both interface languages.
- Guarantee that these requests cannot reach the engine as ordinary conversation.
- Prove the guarantee with automated tests that assert refusal and no passthrough.
- Keep all existing behavior and tests intact.

## Non-Goals

- Changing which explicit operations exist, what they do, or how they are invoked.
- Implementing key setup, configuration editing or project scaffolding inside the client.
- Adding a confirmation prompt, a natural-language action interpreter, or any new conversational capability.
- Changing the client's rendering, session model, install path or packaging.
- Rewording or redesigning refusal messages for categories that are already guarded, beyond what the new wording needs to stay consistent.
- Documentation changes beyond what the release notes of this change require.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-002: The client is a thin UI over the engine's parameterized commands; it does not act on the project itself. | User decision log, D-002, 2026-11-16 18:31 |
| — | D-007: Free text is a single conversational entry point; every client-facing operation is a parameterized command of the engine. | User decision log, D-007, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: A free-text request that asks to create, set or change key material is refused, including requests that use only the bare key wording rather than a credential term, in English and in Russian.
- **FR-2**: A free-text request that asks to change configuration is refused, including requests that use only the bare configuration wording, in English and in Russian.
- **FR-3**: A free-text request that asks to create or scaffold a project is refused, including requests phrased with the bare scaffolding wording, in English and in Russian.
- **FR-4**: A refused request is not sent to the engine: the client makes no engine request for it and reports no action result.
- **FR-5**: The refusal tells the user that the requested action needs the dedicated explicit operation, and names the operation to use, so the user can act without guessing.
- **FR-6**: The refusal is presented in the language the rest of the interface uses for that user.
- **FR-7**: Requests outside the guarded categories continue to be forwarded to the engine exactly as before, and no existing refusal is narrowed or lost.
- **FR-8**: Automated tests assert, for every recognized form in each covered language and category, that the request is refused and that no engine request is made.
- **FR-9**: The existing test suite passes unchanged in meaning: no test is weakened or deleted to accommodate the new behavior.

## User Stories

- As a user, I want the client to stop me when I type an instruction that needs an explicit action, so that I am not misled into thinking a key was set, configuration was changed or a project was created.
- As a maintainer, I want automated proof that sensitive free-text requests are refused and never forwarded, so that this release-audit finding cannot recur unnoticed.

## Acceptance Criteria

- **AC-1**: Typing a free-text request to change configuration, in English or in Russian, is refused in the client and no engine request is made.
- **AC-2**: Typing a free-text request to create or set key material, including the bare key wording, in English or in Russian, is refused and no engine request is made.
- **AC-3**: Typing a free-text project creation or scaffolding request, including the bare scaffolding wording, in English or in Russian, is refused and no engine request is made.
- **AC-4**: Each refusal names the explicit operation the user should use to perform the action.
- **AC-5**: The refusal appears in the interface language of the session.
- **AC-6**: Ordinary conversational messages that are not requests of the guarded categories still reach the engine and are answered as before.
- **AC-7**: Automated tests cover every listed form and assert both the refusal and the absence of an engine request.
- **AC-8**: The full existing test suite passes.

## Scope Boundaries

- Recognizing free-text requests that ask to create or set key material, including the bare key wording form, in English and Russian.
- Recognizing free-text requests that ask to change configuration, including the bare configuration wording, in English and Russian.
- Recognizing free-text requests that ask to create or scaffold a project, including the bare scaffolding wording, in English and Russian.
- Refusing those requests in the client with a message that points to the explicit operation and produces no action result.
- Ensuring a refused request causes no request to the engine.
- Automated tests asserting refusal plus no passthrough for each recognized form.
- Keeping every existing guard behavior and every existing test passing.
- Changing which explicit operations exist, what they do, or how they are invoked.
- Implementing key setup, configuration editing or project scaffolding inside the client.
- Adding a confirmation prompt, a natural-language action interpreter, or any new conversational capability.
- Changing the client's rendering, session model, install path or packaging.
- Rewording or redesigning refusal messages for categories that are already guarded, beyond what the new wording needs to stay consistent.
- Documentation changes beyond what the release notes of this change require.

## Risks

- Over-broad matching could refuse ordinary conversation that mentions keys, configuration or projects, degrading normal use; the guard must key on the action wording, not on a lone noun.
- Under-broad matching of Russian morphology or word order could leave a phrasing unguarded and reproduced as an audit finding.
- Tests that assert only the refusal message but not the absence of an engine request would leave passthrough undetected and let the finding recur.
- Adding new wording inconsistently with existing refusal wording could produce duplicated or contradictory messages for overlapping requests.
- Refusal guidance could name an operation the user cannot actually reach from the client, making the message misleading.

## Open Questions

- None.

## Assumptions

- Equivalent Russian phrasings for configuration change and for project creation/scaffolding are covered by the same categories as their English counterparts, because the interface is bilingual.
- The guard remains aimed at action requests; a message that merely mentions key material, configuration or a project without asking to create or change it is not newly refused by this task.
- Where the client already localizes user-facing messages, the refusal follows the same localization mechanism rather than introducing a new one.
- The tests exercise the refusal through the same entry path a typed user request takes, so an assertion of no engine request is meaningful.
- Existing guarded wording keeps its current behavior; only the missing coverage is added.

## Related Documents

- FORGEL.md
- AGENTS.md
- README.md
- CHANGELOG.md
- releases/0.1.1/release.md

## Revision History

- v1 — initial specification for the release-audit finding on sensitive-action guard coverage.


## Summary

Completed the sensitive-action guard for the three explicit action families in English and Russian, and proved it with tests.

Product change in `forgel_code/interactive.py`: added a verb+object recognizer (`SENSITIVE_EN_RU_ACTIONS`, `CREATE_VERB_*`, `CHANGE_VERB_*`, `KEY_NOUNS`, `CONFIGURATION_NOUNS`, `SCAFFOLD_NOUNS` and their Russian stems) that `resolve()` consults after the existing marker and French/Spanish checks. It refuses a sentence that names both an action verb and the object it acts on: setting/changing a key (bare `key`/`ключ`, no credential term needed), changing configuration (bare `config`/`настройки`/`параметры`), and creating or scaffolding a project (including bare scaffolding words such as `scaffold`, `bootstrap`, `init`, `каркас`). A sentence naming only the noun stays ordinary conversation, so ordinary conversation is unaffected. The English and Russian `sensitive` refusal messages were updated so each names the action family and the explicit operation to use (`forgel-code`), in the session's language; the French and Spanish wording was left as it was and every previously guarded phrase still resolves to `sensitive`.

Tests: new `tests/test_sensitive_actions.py` drives a stand-in engine that logs every argv. Subtests assert, for every listed English and Russian form in each of the three categories, that the request is decided as `sensitive`, that the session shows the refusal without any action result (no `say` request at all, no collision with the engine's answer, one explicit-operation mention per refused phrase), that the refusal text matches the session language (`en` and `ru`), and that ordinary English and Russian messages still reach the engine and are answered. It also re-asserts the previously guarded phrases.

Verification: `python -m pytest tests -q` -> 390 passed, 643 subtests passed (existing 382 tests unchanged and passing). `CHANGELOG.md` gained one `Unreleased / Fixed` entry describing the behavior.

## Files Changed

- `CHANGELOG.md`
- `forgel_code/interactive.py`
- `tests/test_sensitive_actions.py`

## Commands

- `["python", "-c", "print(1)"]` → exit 0
- `["python", "-m", "pytest", "tests", "-x", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests/test_sensitive_actions.py", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests", "-q"]` → exit 0
- `["git", "diff", "--unified=3", "--", "CHANGELOG.md"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "diff", "--unified=2", "--", "forgel_code/interactive.py"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "tests", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests"]` → exit 0

## Final Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/okalistratov/Documents/sites/code
configfile: pyproject.toml
collected 390 items

tests/test_check_cleanup.py ..                                           [  0%]
tests/test_cli.py ...................................................... [ 14%]
.................                                                        [ 18%]
tests/test_cli_extra.py .........                                        [ 21%]
tests/test_cli_help_description.py ....                                  [ 22%]
tests/test_extras.py ......................                              [ 27%]
tests/test_idle_refresh.py ....                                          [ 28%]
tests/test_install.py .................................................. [ 41%]
......                                                                   [ 43%]
tests/test_install_timeout_verdict.py ....                               [ 44%]
tests/test_interactive.py .....................................          [ 53%]
tests/test_localization.py ..........................                    [ 60%]
tests/test_packaging.py ..............                                   [ 63%]
tests/test_packaging_types.py ..                                         [ 64%]
tests/test_readme_install.py ..................................          [ 73%]
tests/test_redact.py ..................................                  [ 81%]
tests/test_redact_descriptor.py ..........                               [ 84%]
tests/test_redact_french_joined.py .........                             [ 86%]
tests/test_redact_french_spanish.py ........................             [ 92%]
tests/test_redact_quoted_bare.py ..........                              [ 95%]
tests/test_retained_text.py ......                                       [ 96%]
tests/test_sensitive_actions.py ........                                 [ 98%]
tests/test_stub_contract.py ....                                         [100%]

======================= 390 passed in 222.86s (0:03:42) ========================

```

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
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- recall
- recall
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/cli.py
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- recall
- run: ['python', '-m', 'pytest', 'tests', '-x', '-q']
- read_file: CHANGELOG.md
- read_file: tests/test_idle_refresh.py
- write_file: tests/test_sensitive_actions.py
- run: ['python', '-m', 'pytest', 'tests/test_sensitive_actions.py', '-q']
- write_file: CHANGELOG.md
- run: ['python', '-m', 'pytest', 'tests', '-q']
- read_file: CHANGELOG.md
- run: ['git', 'diff', '--unified=3', '--', 'CHANGELOG.md']
- run: ['git', 'checkout', '--', 'CHANGELOG.md']
- write_file: CHANGELOG.md
- run: ['git', 'diff', '--stat']
- run: ['git', 'diff', '--unified=2', '--', 'forgel_code/interactive.py']
- run: ['git', 'status', '--porcelain']
- run: ['python', '-m', 'pytest', 'tests', '-q']
