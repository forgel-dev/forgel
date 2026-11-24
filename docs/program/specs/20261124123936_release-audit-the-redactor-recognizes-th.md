# Task Spec: Release audit: The redactor recognizes the French password label only as the whitespace-separat

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The redactor recognizes the French password label only as the whitespace-separat |
| Project | — |
| Task | `20261124123936_release-audit-the-redactor-recognizes-th` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T12:39:48+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The redactor that keeps secrets and key material out of the Forgel Code session recognizes the French password label only as the whitespace-separated phrase `mot de passe`. Joined forms such as `mot_de_passe` and `mot-de-passe` are treated as one compound label whose segments (`mot`, `de`, `passe`) are not secret words, so the label is not recognized as a secret label, the secret-value matcher does not fire, and there is no phrase match to bound. As a result an engine reply or error containing a joined French password label with an adjacent value is displayed and retained with the value intact, which is a data leak and contradicts the requirement that secrets and key material never appear in the session. A previous review noted this residual and dismissed it; it is a defect, not an optional improvement.

**Outcome:** The redactor recognizes the French password label in its joined forms as well as its whitespace-separated form, so an engine reply or error that carries a joined or spaced French password label with an adjacent value is redacted before display and before retention, with no plaintext value left in the session. The existing redaction behavior for every other secret label and language is unchanged, and the whole test suite passes.

## Product Intent

The client is a thin interactive UI over the engine, and nothing the engine returns may put secrets or key material into the user's session: not on screen, not in the stored conversation. Redaction must hold for the languages the client already supports, including the French password label in any spelling a reply or error might produce.

## User Experience

A user whose engine reply or error mentions a French password label sees the value replaced by the redaction placeholder whether the label is written as separate words, with underscores or with hyphens. The user never sees or later finds the plaintext value in the session, and every other message renders exactly as it did before.

## Roadmap

—

## Goals

- Close the audited leak: no engine reply or error carrying a joined French password label reaches the user or the stored conversation with its value intact.
- Keep the redaction behavior for every other label and language unchanged and proven by the existing suite.

## Non-Goals

- Adding new languages or new secret-label vocabularies beyond the French password label.
- Changing the redaction placeholder, the redaction strategy, or how much surrounding context is kept.
- Changing engine behavior, engine commands, or how replies are produced or stored.
- Reworking the redactor to a different architecture or renaming its internals.
- Documenting the redaction vocabulary in user-facing documents.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine and does not itself call the model, read project files or run checks; secrets must never be surfaced from engine exchanges. | D-002, user decision log |
| — | The client is a Python client installed as `forgel-code` with Pareto 20/80 scope and imports nothing from the engine. | D-004, user decision log |
| — | Requirement and specification documents state functional behavior only, with no technical detail or implementation file list. | D-110, FORGEL.md native rules |

## Functional Requirements

- **FR-1**: The French password label is recognized as a secret label when written as separate words, when joined with underscores, and when joined with hyphens, regardless of letter case.
- **FR-2**: A value adjacent to a joined French password label is redacted with the same placeholder used for other secret values and is not present in the rendered message nor in the retained session text.
- **FR-3**: Redaction of a joined French password label works with the value forms and separators already handled for the spaced form: delimited assignment, colon or equals separator, quoted values, bare values, and a label wrapped in quotes or brackets.
- **FR-4**: A joined French password label with no adjacent value does not cause any part of the surrounding message to be redacted.
- **FR-5**: All previously supported secret labels in every supported language continue to be redacted exactly as before.
- **FR-6**: The full test suite passes.

## User Stories

- As a user of Forgel Code, I want a French password label written with underscores or hyphens to be redacted just like the spaced form, so that an engine reply or error cannot leak a password onto my screen or into my session history.

## Acceptance Criteria

- **AC-1**: For a message containing a hyphen-joined French password label followed by a value, the rendered output and the retained session text contain the redaction placeholder instead of the value.
- **AC-2**: For a message containing an underscore-joined French password label followed by a value, the rendered output and the retained session text contain the redaction placeholder instead of the value.
- **AC-3**: The spaced French password label and all other supported secret labels still redact as before.
- **AC-4**: A joined French password label without an adjacent value leaves the message unchanged.
- **AC-5**: Quoted and bracketed joined French password labels are redacted the same way as their spaced equivalents.
- **AC-6**: The full test suite passes.

## Scope Boundaries

- Recognize the French password label in its joined spellings (underscore-joined and hyphen-joined) in addition to the existing whitespace-separated phrase, wherever replies and errors are redacted before display and retention.
- Redact the value adjacent to a joined French password label with the same placeholder and the same before/after context behavior already used for the spaced form.
- Cover the joined spellings in the redaction test suite for the delimited assignment and label/value separators already covered for the spaced form, including the case where the label is quoted or bracketed.
- Keep every existing secret-word match, phrase match, localization behavior and redaction test green.
- Adding new languages or new secret-label vocabularies beyond the French password label.
- Changing the redaction placeholder, the redaction strategy, or how much surrounding context is kept.
- Changing engine behavior, engine commands, or how replies are produced or stored.
- Reworking the redactor to a different architecture or renaming its internals.
- Documenting the redaction vocabulary in user-facing documents.

## Risks

- A joined-label rule that is too broad could redact ordinary text that merely contains the letters of the label without an adjacent value, creating false positives.
- Narrowing or widening the secret-word list could change unrelated matches and break existing localization tests.
- If redaction is applied only at the display path and not the retention path (or vice versa), the leak persists in the other path.
- Testing only one joined spelling or only one separator could leave the audited case partially unfixed.
- The milestone cross-repository direction could invite out-of-scope engine changes that this task does not need and must not make.

## Open Questions

- None.

## Assumptions

- The joined spellings to support are exactly underscore-joined and hyphen-joined, because those are the forms the audit named and those are the separators used by the other supported labels.
- Case-insensitive matching continues to apply, since the spaced form is already matched case-insensitively.
- The placeholder and context rules stay identical to other secret labels; only recognition of the label spelling changes.
- Redaction must cover the rendering path used for replies and errors, since retained text is derived from the same redaction behavior.
- No configuration switch is introduced; recognizing the joined label is unconditional.

## Related Documents

- FORGEL.md
- AGENTS.md
- CHANGELOG.md

## Revision History

- 1.0 — Initial specification for the release audit finding on joined French password labels.
