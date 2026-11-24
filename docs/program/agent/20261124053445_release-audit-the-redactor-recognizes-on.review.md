# Task Review: Release audit: The redactor recognizes only English secret words and Russian stems (`SECRET_WOR

- Task: `20261124053445_release-audit-the-redactor-recognizes-on`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T12:36:53+00:00

## Summary

The change extends the existing single redaction path in `forgel_code/interactive.py`: a diacritic-folded French/Spanish vocabulary (`SECRET_WORDS_FOLDED`) is checked both on the whole label and on each compound segment, and a dedicated phrase matcher extends a label across whitespace (including line breaks) for the multi-word French password label, so the already existing separator/binding/masking logic is reused unchanged for the new languages. Because no second masking path is created and `_binding`, the mask placeholder and the places where redaction is applied are untouched, displayed text, retained session text and error text are masked by the same rule, while English and Russian recognition keeps working (the folded set only adds new spellings, and the existing suites still pass per QA). The new `tests/test_redact_french_spanish.py` covers case, plurality, diacritics, separator parity, repeated occurrences, prose without a value, idempotency, cross-language sentences, and session-level displayed/retained/error text for French and Spanish, without removing or weakening any existing test. No unrelated, temporary or generated file is committed and no secret is introduced. Residual observations (hyphen/underscore-joined spellings such as `mot-de-passe`, and French sentences that interpose other words between the label and the separator) are outside the enumerated label and separator forms the specification requires, so they are noted but not blocking.

## Requirements

- FR-1/FR-2: A value introduced by a French label and by a Spanish label is masked in displayed text, in retained session text and in error text.: pass — The new vocabulary is matched inside the single `redact` path that already feeds display, retention and error reporting; `tests/test_redact_french_spanish.py` exercises the session reply, the retained task title and the engine error text for both languages.
- FR-3: The French labels cover the words for password (including the multi-word form), key, token and secret.: pass — `mot/mots de passe` via `SECRET_PHRASES`, `cle/cles/clef/clefs`, `jeton/jetons`, `secret/secrets` in `SECRET_WORDS_FOLDED`. Hyphen- or underscore-joined spellings (`mot-de-passe`) are not matched, but the specification enumerates only the whitespace-separated multi-word form.
- FR-4: The Spanish labels cover the words for password, key and secret.: pass — `contrasena/contrasenas/contrasenia/contrasenias`, `clave/claves`, `secreto/secretos`; the Spanish token word coincides with the already recognized English `token`.
- FR-5: Each recognized French and Spanish label is matched case-insensitively.: pass — Labels are lower-cased before comparison; lower, upper and mixed case are asserted in the tests.
- FR-6: Plural forms of the French and Spanish labels are recognized as well as the singular forms.: pass — Plural spellings (`cles`, `clefs`, `jetons`, `secrets`, `claves`, `contrasenas`, `secretos`, `mots de passe`) are enumerated and tested.
- FR-7: Accented and unaccented spellings are equally recognized.: pass — `_plain` lower-cases and folds diacritics with the existing table, so `clé`/`cle` and `contraseña`/`contrasena` are one label; both spellings are asserted.
- FR-8: A multi-word label is recognized when its words are separated by any amount of whitespace, including a line break.: pass — `_phrase_end` walks the phrase words through `_skip_gap`, so single spaces, repeated spaces, tabs and line breaks inside `mot de passe` all match; tested.
- FR-9: The separators and separator spacing already accepted for English and Russian are accepted identically for French and Spanish, with none added or dropped.: pass — The binding/separator logic (`_binding`, `_skip_gap`, `_WHITESPACE`) is untouched; the tests assert the same separator shapes for `clé`/`clave` as for the existing languages.
- FR-10: Masking replaces the whole value with the existing placeholder, keeps the label and separator visible and copies no fragment of the value.: pass — The unchanged masking branch emits the existing `[redacted]` placeholder after the label and separator; tests assert the exact output and the absence of the value fragment.
- FR-11: Every occurrence of a labelled value in one piece of text is masked, not only the first.: pass — The loop still walks all label spans and advances `copied`; two-value French and Spanish sentences are asserted to produce two placeholders.
- FR-12: Text with no recognized label followed by a separator and a value is returned unchanged, including ordinary French and Spanish prose.: pass — Prose is protected by the binding rule plus the added French/Spanish function words and narrative forms; `la clé du projet est prête`, `les jetons sont expirés`, `mot de passe oublié`, `la contraseña es segura`, `los secretos del proyecto` are asserted unchanged.
- FR-13: Already masked text is not masked again and is not altered by a second pass.: pass — Idempotency is asserted for French and Spanish lines with exactly one placeholder remaining after the second pass.
- FR-14: English and Russian label recognition, masking appearance and every previously satisfied masking expectation stay exactly as before.: pass — The English and Russian vocabularies are untouched and the folded set only adds equality check branches; the existing expectation set passes per QA and the new file re-asserts English and Russian forms. The shared function-word set gains French/Spanish entries, but no previously satisfied English or Russian case is reported failing.
- FR-15: Masking does not depend on the language of the rest of the sentence.: pass — A French label inside an English sentence and a Spanish/English mix in one line are asserted to be masked.
- FR-16: Retained and reported text is masked before it is stored or shown, with no unmasked intermediate version.: pass — No new masking site or retention path is introduced; the existing pipeline redacts before storing and rendering, and the session tests inspect the retained and error text.
- AC-11 (review-only): The new behaviour is covered by automated expectations for displayed text, retained text and error text in French and Spanish.: pass — `tests/test_redact_french_spanish.py` defines French/Spanish reply engines (displayed), a state engine whose retained task titles carry labelled values (retained), and French/Spanish failing engines (error), plus direct `redact` expectations for vocabulary, case, plurality, diacritics, whitespace, separators, multiple values, prose, idempotency and cross-language sentences.
- The change contains every file it needs, adds no unrelated, temporary, debug or generated file, and does not weaken or delete existing tests.: pass — Only `forgel_code/interactive.py` and the new test file are attributed; no test removal was detected and no escalated file exists.

## Blocking

- none

## Test Removals

- none


