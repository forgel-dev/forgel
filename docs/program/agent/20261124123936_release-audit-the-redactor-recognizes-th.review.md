# Task Review: Release audit: The redactor recognizes the French password label only as the whitespace-separat

- Task: `20261124123936_release-audit-the-redactor-recognizes-th`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T13:05:30+00:00

## Summary

The attributed change is small and directly addresses the audited leak. `forgel_code/interactive.py` adds a `_joined_phrase` helper and consults it from `_secret_label`, so a label whose segments are the words of an existing multi-word secret phrase joined only by `_` or `-` (in any case, since the label is already folded/lowered) is now treated as a secret label; the value after such a single-token label then takes the ordinary secret-label redaction path with the existing `[redacted]` placeholder. The recognition is derived from the existing `SECRET_PHRASES`, so no new vocabulary or language is introduced, dotted spellings still fall through to the previous segment logic, and dotted or extra-segment compounds are not newly matched. A dedicated test module covers both joiners in several cases, upper/lower casing, every value form the spaced label already supported (colon, equals, double-equals, quoted, bare, copula, bracketed, multiline, plural), quoted and bracketed labels, idempotency, the no-adjacent-value case, and unchanged behavior for the other labels in English, Russian, French and Spanish. It also drives the real `InteractiveSession` against stub engines to prove the value is masked both on display and in the retained state for replies, task titles and errors. The CHANGELOG entry is an accurate English behavioral note without volatile implementation detail, no unrelated, temporary or generated file was committed, no test was removed or weakened, and QA reports the full suite and the acceptance checks green. The only nit is an unused `json` import in the new test module, which is not a requirement failure.

## Requirements

- The French password label is recognized as a secret label when written as separate words, joined with underscores and joined with hyphens, regardless of letter case.: pass — `_joined_phrase` compares the joined segments against the existing `SECRET_PHRASES` after the label is lowered and folded, so `mot_de_passe`, `mot-de-passe`, `MOT_DE_PASSE` and `Mot-De-Passe` are recognized; the spaced form keeps its existing phrase path. Tests cover the four spellings.
- A value adjacent to a joined French password label is redacted with the same placeholder and is absent from the rendered message and from the retained session text.: pass — The joined label now flows through the ordinary single-token secret-label redaction, so `REDACTED` is used; the session tests assert the value is absent from the printed output and from `last_state` / `idle_failure` for a reply, a task title and an engine error.
- Redaction of a joined label works with the value forms and separators already handled for the spaced form: delimited assignment, colon or equals separator, quoted values, bare values, quoted and bracketed labels.: pass — `test_a_joined_label_matches_its_spaced_equivalent` compares the joined rendering with the spaced rendering for eighteen forms, including `=`, `==`, `:`, quoted, bare, copula, bracketed, quoted-label, bracketed-label and multiline values.
- A joined French password label with no adjacent value causes no part of the surrounding message to be redacted.: pass — `test_a_joined_label_without_a_value_is_left_alone` asserts the message is returned unchanged for bare, plural and in-sentence joined labels.
- All previously supported secret labels in every supported language continue to be redacted exactly as before.: pass — The change only adds a positive branch in `_secret_label`; segment and stem matching is untouched. The new test asserts exact outputs for the spaced French form, French `clé`, English `password`, Russian `пароль`, Spanish `contraseña` and the compound `db_password`, and the existing redaction suites remain in place with QA green.
- The full test suite passes.: pass — QA reports the environment test and e2e checks green and the full-suite acceptance check exits 0.
- AC-1: hyphen-joined label with a value yields the redaction placeholder in both rendered output and retained text.: pass — Acceptance check passed (exit 0); the session tests assert `mot-de-passe: [redacted]` in output and state.
- AC-2: underscore-joined label with a value yields the redaction placeholder in both rendered output and retained text.: pass — Covered by `test_a_joined_reply_is_masked_before_display` (`mot_de_passe=[redacted]`) and `test_the_joined_state_is_retained_masked` (`mot_de_passe : [redacted]`), both passing within the green suite.
- AC-5: quoted and bracketed joined labels are redacted the same way as their spaced equivalents.: pass — The equivalence test includes `'mot de passe'`, `"mot de passe"` and `[mot de passe]` forms and compares joined against spaced output; the acceptance check passed.
- Non-goals respected: no new language or secret vocabulary, no change to the placeholder, strategy or context, no engine change, no architectural rewrite or internal renaming, no user-facing vocabulary documentation.: pass — Recognition reuses `SECRET_PHRASES`, the placeholder and context logic are untouched, only `_secret_label` and one new helper changed, and the only documentation touched is the CHANGELOG entry.
- The change is internally consistent, includes every file it needs, and excludes unrelated, temporary, debug or generated files; no test is deleted or weakened.: pass — The diff is limited to the redactor, one new self-contained test module and its CHANGELOG entry; the test-removal scan reports none, and no unrelated artifact appears in the attributed commit.
- Documentation is accurate, English and behavioral, with no volatile implementation detail.: pass — The CHANGELOG bullet states the behavior (joined spellings recognized in any case, masked before display and retention, unchanged behavior elsewhere) without interfaces, timings or internal structure, and is verified by reading per D-106.

## Blocking

- none

## Test Removals

- none


