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
