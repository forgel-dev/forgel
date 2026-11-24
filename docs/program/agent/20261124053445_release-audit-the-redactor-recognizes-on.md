# Agent Run: Release audit: The redactor recognizes only English secret words and Russian stems (`SECRET_WOR

- Task: `20261124053445_release-audit-the-redactor-recognizes-on`
- Status: `done`
- Repository: `code`
- Steps: 18
- Finished: 2026-11-24T12:28:28+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The French label set is mot(s) de passe, clé/cle/clef(s), jeton(s) and secret(s); the Spanish set is contraseña/contrasena(s)/contrasenia(s), clave(s) and secreto(s), since Spanish 'token' is already an English-recognized word.
- Prose protection reuses the existing mechanism: French and Spanish function and narrative words were added to the existing word sets rather than introducing a new separator or placeholder.
- Accent-insensitive comparison folds diacritics only for label matching, leaving the displayed label exactly as the user wrote it.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 18
- Estimated input tokens (all calls): 953711
- Provider input/output tokens: 983416 / 90722
- Provider cache hit/miss tokens: 862336 / 121080
- Estimated prompt at the end: 47890 tokens
- State: `docs/program/agent/20261124053445_release-audit-the-redactor-recognizes-on.state.md`

## Specification (`docs/program/specs/20261124053445_release-audit-the-redactor-recognizes-on.md`)

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


## Summary

Extended the single masking rule in forgel_code/interactive.py so French and Spanish secret labels are recognized alongside English and Russian. Added a diacritic-folding label set (cle/clef, jeton, secret, clave, contrasena/contrasenia, secreto, singular and plural), a multi-word French password label (mot(s) de passe) matched across any whitespace including line breaks, and French/Spanish function and narrative words so ordinary prose ("la clé du projet", "le mot de passe est requis", "los secretos del proyecto") is not bound to a value. Because recognition happens inside the one existing label/separator/binding path, the same separators and mask placeholder apply, all three output places (displayed reply, retained state, error text) are covered, and English/Russian behaviour is untouched. Added tests/test_redact_french_spanish.py covering redact() directly (case, plurality, diacritics, whitespace splits, separators, multiple values per line, prose untouched, idempotency, mixed-language sentences) and session-level display, retention and error-text masking for French and Spanish with stub engines. Verified with `python -m pytest`: 369 passed, 528 subtests passed, including the 24 new tests.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact_french_spanish.py`

## Commands

- `["python", "-m", "pytest", "tests/test_redact_french_spanish.py", "-x", "-q"]` → exit 1
- `["python", "-m", "pytest", "tests/test_redact_french_spanish.py", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "diff"]` → exit 0
- `["python", "-m", "pytest"]` → exit 0

## Final Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/okalistratov/Documents/sites/code
configfile: pyproject.toml
collected 369 items

tests/test_check_cleanup.py ..                                           [  0%]
tests/test_cli.py ...................................................... [ 15%]
.................                                                        [ 19%]
tests/test_cli_extra.py .........                                        [ 22%]
tests/test_extras.py ......................                              [ 28%]
tests/test_idle_refresh.py ....                                          [ 29%]
tests/test_install.py .................................................. [ 42%]
......                                                                   [ 44%]
tests/test_install_timeout_verdict.py ....                               [ 45%]
tests/test_interactive.py .....................................          [ 55%]
tests/test_localization.py ..........................                    [ 62%]
tests/test_packaging.py ..............                                   [ 66%]
tests/test_packaging_types.py ..                                         [ 66%]
tests/test_readme_install.py ..................................          [ 76%]
tests/test_redact.py ..................................                  [ 85%]
tests/test_redact_descriptor.py ..........                               [ 88%]
tests/test_redact_french_spanish.py ........................             [ 94%]
tests/test_redact_quoted_bare.py ..........                              [ 97%]
tests/test_retained_text.py ......                                       [ 98%]
tests/test_stub_contract.py ....                                         [100%]

======================= 369 passed in 192.14s (0:03:12) ========================

```

## Actions

- recall
- write_file: forgel_code/interactive.py
- write_file: tests/test_redact_french_spanish.py
- run: ['python', '-m', 'pytest', 'tests/test_redact_french_spanish.py', '-x', '-q']
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_redact_french_spanish.py
- run: ['python', '-m', 'pytest', 'tests/test_redact_french_spanish.py', '-q']
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', '--stat']
- run: ['git', 'diff']
- read_file: tests/test_redact_french_spanish.py
- run: ['git', 'add', 'forgel_code/interactive.py', 'tests/test_redact_french_spanish.py']
