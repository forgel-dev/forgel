# Task Spec: Release audit: The redactor recognizes only English secret words and Russian stems (`SECRET_WOR

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The redactor recognizes only English secret words and Russian stems (`SECRET_WOR |
| Project | — |
| Task | `20261124053445_release-audit-the-redactor-recognizes-on` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T11:49:27+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The masking that keeps secrets off the screen and out of retained text was built for English secret words and Russian stems only. The session now also converses in French and Spanish, so a reply that labels a password, a key, a token or a secret in French or Spanish passes through unchanged: it is displayed, kept in session state and echoed in error text, and the release's no-secret-on-screen requirement no longer holds for the languages the product speaks.

**Outcome:** Masking of labelled secret values works uniformly in every language the session speaks — English, Russian, French and Spanish. A French or Spanish reply that labels a secret value shows, stores and reports the value masked exactly as an English or Russian reply does, unlabelled prose is untouched, and all previously existing masking behaviour and tests remain intact.

## Product Intent

The release audit requires that no secret value reaches the screen, the retained session text or an error message in any language the interactive client speaks. Masking is a language-independent guarantee, not a property of the English vocabulary.

## User Experience

A French- or Spanish-speaking user converses with the client in their own language. When a reply, a retained turn or an error message mentions a password, key, token or secret, the user sees the label and a mask instead of the value — the same way an English- or Russian-speaking user already does. Sentences that merely use those words in ordinary prose are shown unchanged.

## Roadmap

—

## Goals

- Labelled secret values in French and Spanish text are masked in displayed text, retained session text and error text.
- Masking behaviour in English and Russian is unchanged.
- Ordinary French and Spanish prose is not altered.
- The release audit finding about language-limited secret recognition is resolved and demonstrable.

## Non-Goals

- Adding any language beyond English, Russian, French and Spanish.
- Detecting secrets that are not introduced by a label (entropy scanning, free-form credential hunting, pattern guessing).
- Changing where masking is applied, how the mask placeholder looks, or the separator forms already accepted for the existing languages.
- Changing session behaviour, reply generation, retention policy or error reporting beyond the fact that their text is masked correctly.
- Documenting the internal vocabulary of labels.
- Any other release-audit finding.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, user 2026-11-16 18:31 |
| — | The client's working name is Forgel Code; it follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, user accepted 2026-11-16 18:34 |
| — | Every committed project artifact is in English, while chat replies follow the user's language; the product itself speaks several chat languages. | AGENTS.md project rules, D-025; FORGEL.md Language section |
| — | A release without its audit is not published; only a critical or major audit finding holds a release back, and the audit finding here is release-blocking while unresolved. | FORGEL.md Releases section |
| — | A requirements document states functional requirements only, with no technical detail; a specification never lists implementation files. | FORGEL.md Native Rules, D-104 and D-110 |

## Functional Requirements

- **FR-1**: A value introduced by a French secret label is masked wherever masking is already applied: in text shown to the user, in text retained in session state and in error text.
- **FR-2**: A value introduced by a Spanish secret label is masked in the same three places.
- **FR-3**: The recognized French labels cover the words for password, key, token and secret, including the multi-word form of the password label.
- **FR-4**: The recognized Spanish labels cover the words for password, key and secret.
- **FR-5**: Each recognized French and Spanish label is matched case-insensitively.
- **FR-6**: Plural forms of the French and Spanish labels are recognized as well as the singular forms.
- **FR-7**: Accented and unaccented spellings of the French and Spanish labels are equally recognized, so a user typing without the diacritics is still protected.
- **FR-8**: A multi-word label is recognized when its words are separated by any amount of whitespace, including a line break.
- **FR-9**: The separators and separator spacing already accepted between a label and its value for English and Russian are accepted identically for French and Spanish; no new separator form is introduced and none is dropped.
- **FR-10**: Masking replaces the whole value with the existing mask placeholder while leaving the label and the separator visible; the masked text contains no character run copied from the value.
- **FR-11**: Every occurrence of a labelled value in one piece of text is masked, not only the first.
- **FR-12**: Text that contains no recognized label followed by a separator and a value is returned unchanged, including French and Spanish sentences that use these words in ordinary prose.
- **FR-13**: Text that is already masked is not masked again and is not altered by a second pass.
- **FR-14**: English and Russian label recognition, masking appearance and every previously satisfied masking expectation stay exactly as before.
- **FR-15**: The masking rule does not depend on which language the rest of the reply is written in; a French label inside an English sentence and an English label inside a Spanish sentence are both masked.
- **FR-16**: Retained and reported text is masked before it is stored or shown, so no unmasked intermediate version of a labelled value is left in session state or in an error message.

## User Stories

- As a French-speaking user, I want a labelled password or key in a reply to appear masked, so that my secret never shows on screen or in the retained conversation.
- As a Spanish-speaking user, I want a labelled password or key in a reply or an error message to appear masked, so that I can share screens and logs safely.
- As a user who types without accents, I want the unaccented spelling of these labels to be masked just the same, so that a missing diacritic does not expose my secret.
- As a reader of the release audit, I want language-independent masking evidence, so that I can trust that no secret reaches the screen in any supported language.
- As a user writing ordinary prose, I want sentences that merely mention these words to stay readable, so that masking does not mangle my conversation.

## Acceptance Criteria

- **AC-1**: A French reply that labels a password, a key, a token or a secret shows each value as the mask placeholder in the displayed text, and the displayed text contains no fragment of any of those values.
- **AC-2**: A Spanish reply that labels a password, a key or a secret shows each value as the mask placeholder in the displayed text, and the displayed text contains no fragment of any of those values.
- **AC-3**: The same French and Spanish replies, when retained in session state, are retained in the masked form; no unmasked value is present in the retained text.
- **AC-4**: An error message built from French or Spanish text that labels a secret value presents the value masked and contains no fragment of it.
- **AC-5**: The French and Spanish labels are recognized in lower case, upper case and mixed case, in singular and plural, with and without diacritics, and with a multi-word label split by single spaces, repeated spaces or a line break.
- **AC-6**: The masked result keeps the original label and its separator and substitutes the existing mask placeholder for the value, matching the appearance of masking in English and Russian.
- **AC-7**: When one French or Spanish sentence labels two values, both are masked.
- **AC-8**: A French or Spanish sentence that uses these words without a following labelled value is displayed and retained unchanged.
- **AC-9**: An already masked French or Spanish line passes through a second masking pass unchanged.
- **AC-10**: English and Russian masking behaves exactly as it did before, and the full existing automated expectation set still passes.
- **AC-11**: The newly added behaviour is covered by automated expectations that exercise the displayed text, the retained text and the error text for French and Spanish.

## Scope Boundaries

- Recognition of French secret labels in text that is displayed, retained in session state or included in error text.
- Recognition of Spanish secret labels in the same text.
- The accented and unaccented spellings of each French and Spanish label, their plural forms, letter-case variants and whitespace variants inside a multi-word label.
- Parity of the newly recognized labels with the existing English and Russian labels: same separator forms, same masking appearance, same places where masking is applied.
- Proof that text without a secret label is left unchanged, including French and Spanish prose that uses these words without a following value.
- All existing masking behaviour and automated expectations stay green.
- Adding any language beyond English, Russian, French and Spanish.
- Detecting secrets that are not introduced by a label (entropy scanning, free-form credential hunting, pattern guessing).
- Changing where masking is applied, how the mask placeholder looks, or the separator forms already accepted for the existing languages.
- Changing session behaviour, reply generation, retention policy or error reporting beyond the fact that their text is masked correctly.
- Documenting the internal vocabulary of labels.
- Any other release-audit finding.

## Risks

- French and Spanish words for key and secret are short and common, so over-masking ordinary prose is plausible; the acceptance therefore requires that prose without a following labelled value stays unchanged.
- If unaccented and plural spellings are only partly covered, a user typing without diacritics or labelling several values still leaks, which would re-open the audit finding.
- A second parallel masking path for the new labels would drift from the existing one and leave some output place unmasked; the requirements demand one uniform rule.
- The audit finding names specific reply shapes; a fix that handles only those exact strings would pass a narrow check and still leak in other positions, so the acceptance covers case, plurality, diacritics, multiple occurrences and all three output places.
- Masking that produces an empty or misleading result would hide the fact that a value was removed; the acceptance requires the label and separator to stay visible.
- The release audit is the gate: while a critical or major finding stands, the release is held, so this finding must be demonstrably resolved rather than argued.

## Open Questions

- None.

## Assumptions

- The languages the session speaks are exactly English, Russian, French and Spanish, so no other language vocabulary is added.
- The French label set is the words for password (the multi-word form), key (both the accented and unaccented spelling, and the alternative word for key), token and secret.
- The Spanish label set is the words for password, key and secret.
- Plural forms are part of the same vocabulary because a reply can label several passwords or keys at once.
- Unaccented spellings are recognized because users often type without diacritics, and a missing accent must not turn into a leak.
- The words for token and secret in Spanish coincide with the English words already recognized or are close enough not to need a separate entry; the security guarantee comes from the label matching, not from how many spellings are enumerated.
- The mask placeholder, the accepted separators and the set of masked places are the ones the product already uses; this task extends recognition only.
- Ordinary prose that happens to place a colon after one of these words may be masked; that is the accepted cost of never leaking a labelled value.

## Related Documents

- FORGEL.md
- AGENTS.md
- README.md
- CHANGELOG.md
- releases/0.1.1/release.md

## Revision History

- 1.0 — initial specification for the release-audit finding on language-limited secret recognition
