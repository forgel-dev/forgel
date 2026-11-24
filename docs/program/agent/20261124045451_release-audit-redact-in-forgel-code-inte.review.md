# Task Review: Release audit: `redact()` in `forgel_code/interactive.py` treats the first word after a recogni

- Task: `20261124045451_release-audit-redact-in-forgel-code-inte`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T05:29:46+00:00

## Summary

The attributed change replaces the single-word binding after a secret label with a descriptor walker (`_descriptor_span`/`_copula_span`) that keeps ordinary descriptor words and copulas visible while masking the value behind them, reuses the existing `[redacted]` placeholder, stays recursive only in the forward direction (each step strictly advances), and preserves the previously handled separator, quote, authorization-scheme and Russian-stem paths. The new test file covers both reported shapes (label-led and mid-sentence), multiple descriptors, Russian labels, absence of any credential fragment, idempotency, the retained state text and the background-refresh failure text, and re-asserts the previously masked forms (direct binding, compound labels, `Bearer`, Russian) plus prose without a value. The CHANGELOG entry is an English `[Unreleased] / Fixed` bullet that states behavior, and no file outside the task is touched. No test was removed or weakened, and QA reports every acceptance check and the suite passing.

## Requirements

- FR-1/AC-1: a recognized label followed by an ordinary descriptor and then a value keeps the label and descriptor and masks the value.: pass — `_descriptor_span` walks the descriptor and binds the following value; covered by the added cases such as `token value is hunter2` → `token value is [redacted]`.
- FR-2/AC-2: a sentence beginning with the label, then a descriptor, then a value keeps the label and descriptor and masks the value.: pass — Sentence-initial forms (`password field is hunter2`, `secret value hunter2`, Russian `токен значение hunter2`) are asserted in the added test file.
- FR-3/AC-3: no fragment of the credential remains in the displayed text for those shapes.: pass — `test_no_part_of_the_credential_stays_visible` asserts the credential is absent for both shapes, including a trailing word after the value.
- FR-4/AC-4: the retained status text and the retained background-refresh failure text carry the placeholder instead of the credential.: pass — `DescriptorRetentionTest` drives the real session with stub engines and asserts `last_state` and `idle_failure` contain the placeholder and no credential fragment, and that the output stream is clean.
- FR-5/AC-5: previously working masking is unchanged (direct binding, compound labels, authorization scheme words, Russian stems).: pass — `test_the_previously_masked_forms_are_unchanged` re-asserts `password=hunter2`, `token:abc123`, `db_password=…`, `AWS_SECRET_ACCESS_KEY=…`, `Authorization: Bearer …`, `пароль: …`, `токен …`; the separator, quote and scheme branches are reached before the new descriptor path, so their behavior is preserved.
- FR-6/AC-6: prose that mentions a secret word without a value is unchanged, with no placeholder inserted.: pass — No-value prose returns None through `_is_narrative`/`_is_prose`; `test_prose_without_a_value_stays_unchanged` covers English and Russian forms and QA's prose check passes.
- FR-7: the masking placeholder is the one the client already uses.: pass — The change only reuses the existing `REDACTED` constant and even short-circuits on an already present placeholder, so corrected output matches other secret forms.
- FR-8: the behavior holds for every language the session speaks, including the Russian label stems already recognized.: pass — Russian descriptor cases (`токен значение это hunter2`, `пароль значение: hunter2`) are asserted; other languages pass through the same descriptor walk, and the label vocabulary is deliberately unchanged (non-goal).
- FR-9/AC-7: the existing automated test suite continues to pass.: pass — QA environment and suite checks passed; no existing test was modified or removed, and the change is additive to the tested forms.
- Review-only criterion: masked output keeps the surrounding sentence readable and uses the placeholder the client already uses.: pass — Descriptor words, copulas, separators and quotes stay in place and only the value span becomes `[redacted]`; the placeholder is the pre-existing one.
- The change is coherent, limited to the task, and excludes unrelated, temporary or generated files.: pass — Only `forgel_code/interactive.py`, the new `tests/test_redact_descriptor.py` and an English `[Unreleased] / Fixed` CHANGELOG bullet are committed; the new test module is free of debug or generated content.

## Blocking

- none

## Test Removals

- none


