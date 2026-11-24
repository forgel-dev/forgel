# Task Spec: Release audit: `redact()` in `forgel_code/interactive.py` treats the first word after a recogni

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `redact()` in `forgel_code/interactive.py` treats the first word after a recogni |
| Project | — |
| Task | `20261124045451_release-audit-redact-in-forgel-code-inte` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T04:55:12+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client masks the wrong word when a secret label is followed by an ordinary descriptor before the credential. A sentence such as "token value is hunter2" is displayed with the descriptor masked and the credential left visible, and the same leaked text is what the client retains when it re-reads state in the background. The guarantee that no secret, token or key material ever appears in the session, or in anything the client keeps, is therefore broken.

**Outcome:** Masking of secret-bearing sentences is correct: the label and any ordinary descriptor around it stay visible, the credential itself is replaced by the masking placeholder, and no part of the credential reaches the transcript, the retained state snapshot or the background-refresh failure text. Sentences that only mention a secret word in passing are left untouched, and all previously supported secret forms stay masked as before.

## Product Intent

Forgel Code is a thin interactive client over the engine's parameterized commands; the owner must be able to paste ordinary sentences, including ones that mention credentials, without those credentials ever being shown back or stored by the client.

## User Experience

The owner types or pastes a sentence that contains a credential, for example one that names a label and a descriptor before the value. What the client echoes back, and what it later shows after a background refresh, contains the label and the surrounding words but shows the placeholder where the credential was; the credential itself never appears on screen or in any text the client keeps.

## Roadmap

—

## Goals

- The displayed session masks the credential and keeps the label and descriptor visible for the reported sentence shapes.
- Nothing the client retains contains the credential.
- Previously working masking and unrelated session behavior are unchanged.

## Non-Goals

- Changing which words count as secret labels
- Changing the masking placeholder wording or the visual style of the session
- Changing how the client maps sentences to engine commands
- Changing the engine or its commands
- Any change to the wording or structure of the client's prompts, help or localization strings beyond what masking needs

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | D-002, user 2026-11-16 18:31 |
| — | The client is named Forgel Code, installed as a Python package, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, user 2026-11-16 18:34 |
| — | The single free-text engine entry point is the say command; every client-facing operation is a parameterized command. | D-007, user 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: When a recognized secret label is followed by an ordinary descriptor word and then a value, the client displays the label and the descriptor unchanged and replaces the value with the masking placeholder.
- **FR-2**: When a sentence begins with a recognized secret label, is followed by an ordinary descriptor word and then a value, the display keeps the label and descriptor and replaces the value with the masking placeholder.
- **FR-3**: A displayed sentence that carried a credential contains no fragment of that credential after masking.
- **FR-4**: Text the client retains for a later status display, and text it retains when a background refresh fails, contain no fragment of any credential.
- **FR-5**: Masking that already worked stays unchanged: a value bound directly to the label, a compound label whose segment names key material, a credential that follows an authorization scheme word (which stays visible), and a label-bearing Russian sentence are all masked as before.
- **FR-6**: Ordinary prose that mentions a secret word without presenting a value is displayed unchanged, with no placeholder inserted.
- **FR-7**: The masking placeholder is the one the client already uses, so the corrected output is consistent with output produced for other secret forms.
- **FR-8**: The behavior holds for sentences in every language the session speaks, including the Russian label stems the client already recognizes.
- **FR-9**: The existing automated test suite continues to pass.

## User Stories

- As the owner, I want a sentence that mentions a credential to be shown back with the credential masked, so that I can paste real values into the session without exposing them.
- As the owner, I want the status text the client keeps for me to be free of credentials, so that nothing I see later leaks a secret.

## Acceptance Criteria

- **AC-1**: A sentence that names a secret label, an ordinary descriptor and then a credential is displayed with the label and the descriptor visible and the credential replaced by the existing masking placeholder.
- **AC-2**: A sentence that begins with a secret label, continues with an ordinary descriptor and then a credential is displayed with the label and descriptor visible and the credential replaced by the placeholder.
- **AC-3**: No character sequence of the credential appears in the displayed text for either of those two shapes.
- **AC-4**: The status text the client retains, and the failure text it retains when a background refresh fails, contain the placeholder instead of the credential for those shapes.
- **AC-5**: Sentences that previously masked correctly — direct binding, compound labels, authorization scheme words, Russian label stems — still produce the same masked output as before.
- **AC-6**: Prose that mentions a secret word without a value is displayed unchanged.
- **AC-7**: The existing automated test suite passes.

## Scope Boundaries

- Masking of the credential value when a recognized secret label is followed by one or more ordinary descriptor words before the value
- Masking remains correct when such a sentence begins with the label
- The masked output keeps the label, the descriptor and the rest of the sentence readable
- Retained state snapshots and background-refresh failure text carry the same already-masked text, never the credential
- Existing masking behavior for directly bound values, compound labels, authorization scheme words and non-secret prose stays unchanged
- Automated tests covering the corrected masking and the retention path
- Changing which words count as secret labels
- Changing the masking placeholder wording or the visual style of the session
- Changing how the client maps sentences to engine commands
- Changing the engine or its commands
- Any change to the wording or structure of the client's prompts, help or localization strings beyond what masking needs

## Risks

- Over-masking: extending the mask too far may redact ordinary descriptive prose or whole sentences, degrading the transcript.
- Under-masking: a credential separated from its label by more than one descriptor word, punctuation or a line break may still slip through.
- The retention path may build its text from an unmasked source rather than from the displayed text, so correcting display alone leaves the retention guarantee broken.
- A fix aimed at one example sentence may regress the previously working forms (direct binding, authorization scheme words, compound labels).
- Masking may be applied to a fragment of the sentence only, leaving the remainder of the credential visible later in the line.

## Open Questions

- None.

## Assumptions

- The descriptor words involved are ordinary words that are not part of the client's function-word vocabulary, and it is the value after them that is the credential.
- When several ordinary words sit between the label and the value, the credential is the value and the intervening words remain visible.
- If prose genuinely presents no value after the label and descriptor, nothing is masked.
- Correcting the masking at its source is sufficient; the retention path only needs to keep storing the already-masked text.

## Related Documents

- FORGEL.md
- AGENTS.md
- CHANGELOG.md

## Revision History

- 1: initial specification for the release-audit finding on masking of a label followed by a descriptor.
