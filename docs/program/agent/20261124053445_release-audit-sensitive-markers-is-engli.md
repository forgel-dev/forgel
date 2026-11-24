# Agent Run: Release audit: `SENSITIVE_MARKERS` is English/Russian only. French/Spanish phrases such as `cré

- Task: `20261124053445_release-audit-sensitive-markers-is-engli`
- Status: `done`
- Repository: `code`
- Steps: 111
- Finished: 2026-11-24T11:41:38+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The explicit command surface named in the refusal is the client's own `forgel-code` command line, which is the only explicit surface that exists for project creation, credentials and configuration; no per-action command was invented or added.
- The refusal keeps the language and voice the session already uses; the redirect was added to the French and Spanish sentences only, so the English and Russian refusals stay byte-identical.
- The action verbs of a French or Spanish sensitive phrase are counted as a language signal, which is what makes those phrases get the refusal in French or Spanish rather than in English.

## Test Removals

- tests/test_localization.py::SensitiveRefusalTest::test_a_french_refusal_reads_in_the_existing_style: replaced -> tests/test_localization.py::SensitiveRefusalTest::test_a_french_refusal_names_the_explicit_commands
- tests/test_localization.py::SensitiveRefusalTest::test_a_spanish_refusal_reads_in_the_existing_style: replaced -> tests/test_localization.py::SensitiveRefusalTest::test_a_spanish_refusal_names_the_explicit_commands

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 4
- Handoffs: 3
- Model calls: 111
- Estimated input tokens (all calls): 5181220
- Provider input/output tokens: 5317953 / 221165
- Provider cache hit/miss tokens: 5054464 / 263489
- Estimated prompt at the end: 55943 tokens
- State: `docs/program/agent/20261124053445_release-audit-sensitive-markers-is-engli.state.md`

## Specification (`docs/program/specs/20261124053445_release-audit-sensitive-markers-is-engli.md`)

# Task Spec: Release audit: `SENSITIVE_MARKERS` is English/Russian only. French/Spanish phrases such as `cré

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `SENSITIVE_MARKERS` is English/Russian only. French/Spanish phrases such as `cré |
| Project | — |
| Task | `20261124053445_release-audit-sensitive-markers-is-engli` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T10:00:49+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The interactive session only recognizes sensitive explicit-action requests phrased in English or Russian. When a user asks in French or Spanish to create a project, set a password or change configuration, the request is treated as ordinary conversation, handed to the engine's free-text entry and passed on to the engine's project agent. The user receives no refusal and no direction to the explicit commands that actually perform those actions, so the guarantee that such actions never happen implicitly from free text does not hold for languages the session already accepts.

**Outcome:** In every language the interactive session accepts — at minimum English, Russian, French and Spanish — a free-text request expressing a sensitive explicit action (creating a project, setting or defining credentials, changing configuration) is not passed to the engine. The user is told the action is not performed from free text and is pointed to the explicit commands that perform it. English and Russian behavior is unchanged, ordinary conversation in all four languages still reaches the engine as before, and the existing test suite passes.

## Product Intent

The client is a thin UI over the engine's explicit commands and stays out of actions the engine owns; free text is conversation, never an implicit command. Accepting a conversation language must not create a hole in that boundary, or the user believes a project, credential or configuration change happened while the project agent acts on a request the client never meant to pass through.

## User Experience

A user typing 'crée un projet', 'crear un proyecto', 'définir le mot de passe' or 'cambiar la configuración' gets an immediate answer that this is not done from free text, together with a pointer to the explicit commands that perform it, and nothing of that request is sent onward. A user chatting in French or Spanish about other matters is not interrupted. An English- or Russian-speaking user notices no change.

## Roadmap

—

## Goals

- Close the release-audit finding that the explicit-action guarantee is enforced only for English and Russian phrasing.
- Ensure French and Spanish requests to create a project, set credentials or change configuration are never passed onward and are redirected to the explicit commands.
- Preserve existing English, Russian and ordinary-conversation behavior and keep the test suite green.

## Non-Goals

- Localizing the client's interface, refusal wording or documentation into French or Spanish.
- Changing which actions count as sensitive, or changing what the engine or its project agent does.
- Covering languages other than the ones the session accepts today plus French and Spanish.
- Adding, removing or renaming any explicit command, or changing the free-text entry itself.
- Interpreting or executing the requested action on the user's behalf in any language.
- Semantic understanding of arbitrary intent; the guarantee stays phrase-based detection with a conservative bias.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | User decision D-002, 2026-11-16 18:31 |
| — | A single free-text engine entry point exists; every other client-facing operation is an explicit parameterized command. | User decision D-007, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: A free-text input that expresses a sensitive explicit action is refused and redirected in every language the session accepts, at minimum English, Russian, French and Spanish.
- **FR-2**: Sensitive explicit actions covered are at least: creating or scaffolding a project, setting or defining credentials such as a password, token or key, and changing configuration or settings.
- **FR-3**: For each of those action families the common French and Spanish phrasings are detected, including 'crée un projet', 'crear un proyecto', 'définir le mot de passe' and 'cambiar la configuración'.
- **FR-4**: Detection within a supported language covers ordinary variation in verb form and word order for those actions and is not limited to one fixed phrase per action.
- **FR-5**: Detection is insensitive to letter case, accents and diacritics, and to leading, trailing or repeated whitespace, so a French or Spanish phrase written without diacritics is detected as well.
- **FR-6**: A refused input is never passed onward: nothing derived from it reaches the engine's free-text entry.
- **FR-7**: The refusal tells the user that the action is not performed from free text and points to the explicit commands that perform it, in the same style as the refusal the session already produces for sensitive English and Russian requests.
- **FR-8**: English and Russian detection keeps producing exactly the results it produces today for the same inputs.
- **FR-9**: Free-text input that does not express a sensitive action still reaches the engine unchanged in all four languages, including ordinary French and Spanish conversation.
- **FR-10**: Refusal and forwarding decisions are deterministic for the same input within a session.
- **FR-11**: The existing automated tests keep their expectations and pass.

## User Stories

- As a French-speaking user, I want a request to create a project or define a password written as plain conversation to be refused and redirected, so that I know the action happens only through an explicit command and nothing unintended travels onward.
- As a Spanish-speaking user, I want a request to change configuration written as plain conversation to be refused and redirected, so that an unintended configuration change cannot be started from chat.
- As a maintainer running the release audit, I want the explicit-action guarantee to hold for every language the session accepts, so that the audit finding does not return at release.
- As a user chatting in French or Spanish about anything else, I want my conversation to keep working normally, so that the wider protection does not become a nuisance.

## Acceptance Criteria

- **AC-1**: Typing 'crée un projet' in an interactive session produces the refusal-and-redirect answer and passes nothing onward.
- **AC-2**: Typing 'crear un proyecto' in an interactive session produces the refusal-and-redirect answer and passes nothing onward.
- **AC-3**: Typing 'définir le mot de passe' in an interactive session produces the refusal-and-redirect answer and passes nothing onward.
- **AC-4**: Typing 'cambiar la configuración' in an interactive session produces the refusal-and-redirect answer and passes nothing onward.
- **AC-5**: Low-variation forms of the same French and Spanish requests — a different verb form, a different word order, and the same text written without diacritics — are also refused and pass nothing onward.
- **AC-6**: The refusal answer names the explicit commands the user can use for the requested action and reads in the same style as the existing sensitive-request refusal.
- **AC-7**: Sensitive requests phrased in English and in Russian are refused exactly as before, and the pre-existing test expectations still hold.
- **AC-8**: Ordinary French and Spanish conversation, for example a greeting or a question unrelated to projects, passwords or configuration, is still forwarded as free text and answered normally.
- **AC-9**: During the refused cases no outgoing request derived from the refused input exists, as observed in the automated tests.

## Scope Boundaries

- Widening sensitive explicit-action detection in interactive free text to French and Spanish, alongside the existing English and Russian coverage.
- Detecting the sensitive action families already guarded today: creating or scaffolding a project, setting or defining credentials (password, token, key), and changing configuration or settings.
- Covering common inflected and alternative phrasings of those actions within each supported language, including input written without diacritics.
- Returning the same kind of refusal-and-redirect answer the session already gives for sensitive requests in the supported languages.
- Keeping ordinary non-sensitive free text flowing to the engine, and keeping English and Russian results identical to today.
- Keeping the existing automated tests green and extending the suite to cover the new languages.
- Localizing the client's interface, refusal wording or documentation into French or Spanish.
- Changing which actions count as sensitive, or changing what the engine or its project agent does.
- Covering languages other than the ones the session accepts today plus French and Spanish.
- Adding, removing or renaming any explicit command, or changing the free-text entry itself.
- Interpreting or executing the requested action on the user's behalf in any language.
- Semantic understanding of arbitrary intent; the guarantee stays phrase-based detection with a conservative bias.

## Risks

- Over-broad matching could refuse ordinary French or Spanish conversation, degrading the session for those users.
- Accent-insensitive normalization can collapse distinct words and cause false positives in French or Spanish.
- Verb-form coverage may still miss rarer phrasings of a sensitive action within the four languages, leaving a residual gap even though the audited examples are closed.
- The refusal answer stays in its current language, so a French or Spanish speaker may not fully understand the redirect even though the action is correctly blocked.
- Users of other languages the session may later accept remain uncovered; this fix closes only the four languages named.
- A test asserting on exact refusal wording could break on unrelated wording changes; acceptance is on behavior, not on a fixed sentence.

## Open Questions

- None.

## Assumptions

- The languages the session accepts today are English and Russian, and French and Spanish are added to the guarantee by this fix; no other language is claimed.
- The refusal answer keeps the language and style the session already uses for sensitive requests; localizing it is not part of this change.
- The set of sensitive action families guarded today stays as it is; only language coverage is closed.
- Detection stays conservative: refusing a borderline French or Spanish input is preferred over forwarding a sensitive request.
- A phrase naming project creation, a credential change or a configuration change is sensitive whether it is phrased as a statement, a question or a wish.
- A refused input is never partially forwarded.
- Ordinary French and Spanish words that merely contain a guarded stem inside a longer, unrelated word are not treated as sensitive requests.

## Related Documents

- README.md
- CHANGELOG.md
- releases/0.1.1/release.md

## Revision History

- v1 — initial specification for the release-audit fix widening sensitive explicit-action detection to French and Spanish.
- v2 — removed process mechanics from the constraints and restated them as product behavior; only language coverage and the redirect behavior remain.


## Summary

Completed the reviewer-mandated redirect for French and Spanish refusals; the detection widening was already committed by earlier attempts and was left as is. In `forgel_code/interactive.py` the French and Spanish `MESSAGES["sensitive"]` sentences now follow the same structure as the English and Russian ones: they state that adopting a repository, creating a project, setting a secret and changing the configuration are explicit separate actions never carried out from a sentence, and then point at the one explicit command surface the client already has (`forgel-code`), naming each guarded family — creating a project, defining a password, token or key, and changing the configuration — instead of referring to explicit commands in general terms. The command surface is referenced through a single `EXPLICIT_COMMAND` constant so no command is added, renamed or removed, and the English and Russian wording is untouched. Because a French or Spanish input that names no other language signal has to be attributed to one of the two Latin languages for the refusal to be composed in that language at all, the action words themselves (`créer`, `cree`, `définir`, `definis`, `définis`, `changer`, `configurer` / `crear`, `crea`, `asignar`, `clave`, `nuevo`, `nueva` and their plurals) were added to `FRENCH_WORDS`/`SPANISH_WORDS`. `tests/test_localization.py` now splits the audited phrases from their low-variation forms, asserts for every refused French and Spanish phrase that the answer is the sensitive refusal, contains `EXPLICIT_COMMAND` and names all three action families, and still records no `say` call; a wording test checks that each French and Spanish refusal states the boundary before it names the command. A new case pins the English and Russian refusals to their own wording and away from the French and Spanish ones. `CHANGELOG.md` states that the refusal points at the explicit command together with the action it performs. Verified with `python -m pytest -q`: 345 passed, 452 subtests passed. `git status --porcelain` shows only the three files below.; the completion step did not decide; committed the agent's own files and escalated the rest

## Files Changed

- `CHANGELOG.md`
- `forgel_code/interactive.py`
- `tests/test_localization.py`

## Commands

- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--unified=0", "--", "forgel_code/interactive.py"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--unified=3", "--", "forgel_code/interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_localization.py"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_localization.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "diff", "--unified=2", "--", "forgel_code/interactive.py"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "diff", "--unified=1", "--", "CHANGELOG.md"]` → exit 0
- `["git", "diff", "--unified=0", "--", "CHANGELOG.md"]` → exit 0
- `["git", "diff", "--unified=2", "--", "forgel_code/interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--unified=2", "--", "forgel_code/interactive.py"]` → exit 0
- `["git", "diff", "--unified=1", "--", "tests/test_localization.py"]` → exit 0
- `["git", "diff", "--unified=0", "--", "CHANGELOG.md"]` → exit 0
- `["python", "-m", "pytest"]` → exit 0

## Final Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/okalistratov/Documents/sites/code
configfile: pyproject.toml
collected 345 items

tests/test_check_cleanup.py ..                                           [  0%]
tests/test_cli.py ...................................................... [ 16%]
.................                                                        [ 21%]
tests/test_cli_extra.py .........                                        [ 23%]
tests/test_extras.py ......................                              [ 30%]
tests/test_idle_refresh.py ....                                          [ 31%]
tests/test_install.py .................................................. [ 45%]
......                                                                   [ 47%]
tests/test_install_timeout_verdict.py ....                               [ 48%]
tests/test_interactive.py .....................................          [ 59%]
tests/test_localization.py ..........................                    [ 66%]
tests/test_packaging.py ..............                                   [ 71%]
tests/test_packaging_types.py ..                                         [ 71%]
tests/test_readme_install.py ..................................          [ 81%]
tests/test_redact.py ..................................                  [ 91%]
tests/test_redact_descriptor.py ..........                               [ 94%]
tests/test_redact_quoted_bare.py ..........                              [ 97%]
tests/test_retained_text.py ......                                       [ 98%]
tests/test_stub_contract.py ....                                         [100%]

======================= 345 passed in 224.78s (0:03:44) ========================

```

## Actions

- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- recall
- read_file: forgel_code/interactive.py
- recall
- recall
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: README.md
- read_file: CHANGELOG.md
- read_file: releases/0.1.1/release.md
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: tests/test_localization.py
- read_file: forgel_code/commands.py
- read_file: tests/stub_engine.py
- read_file: README.md
- recall
- read_file: tests/test_cli_extra.py
- run: ['python', '-m', 'pytest', '-q']
- read_file: releases/0.1.0/plan.md
- write_file: forgel_code/interactive.py
- run: ['git', 'status', '--porcelain']
- run: ['git', 'restore', 'forgel_code/interactive.py']
- run: ['git', 'diff', '--unified=0', '--', 'forgel_code/interactive.py']
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'diff', '--unified=3', '--', 'forgel_code/interactive.py']
- read_file: README.md
- read_file: forgel_code/commands.py
- read_file: tests/test_localization.py
- read_file: README.md
- run: ['python', '-m', 'pytest', '-q']
- read_file: CHANGELOG.md
- read_file: tests/test_localization.py
- read_file: tests/test_interactive.py
- write_file: tests/test_localization.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/cli.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_localization.py']
- write_file: _forgel_words.diff
- delete_file: _forgel_words.diff
- write_file: forgel_code/interactive.py
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/interactive.py
- read_file: tests/test_localization.py
- read_file: tests/test_localization.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- write_file: tests/test_localization.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_localization.py']
- run: ['python', '-m', 'pytest', '-q']
- read_file: CHANGELOG.md
- read_file: CHANGELOG.md
- write_file: CHANGELOG.md
- run: ['git', 'diff', '--unified=2', '--', 'forgel_code/interactive.py']
- run: ['git', 'status', '--porcelain']
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'diff', '--stat']
- run: ['git', 'diff', '--unified=1', '--', 'CHANGELOG.md']
- write_file: CHANGELOG.md
- run: ['git', 'diff', '--unified=0', '--', 'CHANGELOG.md']
- run: ['git', 'diff', '--unified=2', '--', 'forgel_code/interactive.py']
- write_file: CHANGELOG.md
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/cli.py
- read_file: tests/test_localization.py
- read_file: tests/test_localization.py
- run: ['python', '-m', 'pytest', '-q']
- read_file: forgel_code/cli.py
- read_file: README.md
- read_file: CHANGELOG.md
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', '--unified=2', '--', 'forgel_code/interactive.py']
- read_file: forgel_code/commands.py
- read_file: README.md
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'diff', '--unified=1', '--', 'tests/test_localization.py']
- read_file: releases/0.1.1/plan.md
- run: ['git', 'diff', '--unified=0', '--', 'CHANGELOG.md']
