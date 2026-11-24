# Task Review: Release audit: Redaction misses values separated from a secret label by a newline and values be

- Task: `20261124003849_release-audit-redaction-misses-values-se`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T04:28:41+00:00

## Summary

The attributed change is coherent and complete: `forgel_code/interactive.py` widens the label/value gap to whitespace containing line breaks, keeps every separator and line break visible, and adds a punctuation/bracket-aware value span for explicit ':'/'=' separators together with an idempotence guard for the marker. `tests/test_redact.py` adds focused unit tests for the newline, CRLF, punctuation-prefixed, bracketed, no-value, secret-free and double-masking forms plus a session-level test that the client masks a value on the line after its label in an engine reply, without removing or weakening any existing expectation. The change sticks to the requested scope (no new configuration, no label/scheme changes, no engine interface changes, no documentation), contains no unrelated or generated files, and the deterministic checks reported by QA pass.

## Requirements

- FR-1 / AC-1: label + explicit colon + line break + value on the next line is shown as label, colon, same line break and one marker; no character of the value visible.: pass — `_separator_end` and `_skip_gap` now skip whitespace including line breaks, while only the value span is replaced, so the separator and line break stay. Covered by the new colon/equals line-break tests and the acceptance check that passed.
- FR-2 / AC-2 / AC-3: the line-break rule works both for one block of text and for separate display lines, keeps the line count and leaves all other lines character for character.: pass — Masking operates on the whole text and the gap/separator skips only whitespace, so no newline is consumed or added; unit tests assert the line count and unchanged neighbouring lines, and the session test asserts the masked reply lines.
- FR-3 / AC-4: a punctuation-prefixed value after ':' or '=' is masked together with its leading punctuation, with the label, separator and space visible and exactly one marker.: pass — `_explicit_span`/`_marked_span` replace the punctuation and the value with one marker for any punctuation, not only the examples in the finding; covered for '!', '@', '#' across several labels.
- FR-4 / AC-5: a bracketed value after an explicit separator is masked entirely, brackets included, with exactly one marker.: pass — `_VALUE_BRACKETS` handles the bracketed run whole, so no bracket or value character survives; tests cover '[hunter2]', '[abc123]' and a spaced bracketed value.
- FR-5 / AC-6: quoted values keep their current rendering, quotes visible with the marker between them.: pass — `_explicit_span` sends quote pairs to the unchanged `_span` path; the existing quoted-value expectations still pass.
- FR-6: repeated separator characters stay visible and only the value is replaced.: pass — Only the value span is replaced; the separator run including repeats and interleaved whitespace is untouched, matching the existing repeated-separator expectations and the new '==' case.
- FR-7 / AC-10: exactly one marker per masked value and masking twice equals masking once, including the new forms.: pass — `_explicit_span` recognises the existing marker first, and bracket/word spans never re-include it; the dedicated idempotence test asserts one marker and a fixed point for every new form.
- FR-8: no character of a masked value appears anywhere in the shown text for every new and existing form.: pass — The whole span is replaced in one substitution; tests assert the secret is absent and the marker count is one.
- FR-9 / AC-7 / AC-8: a label mention without a value (same line or followed by a line break) and an authorization scheme before a credential keep today's rendering.: pass — The separator/punctuation path returns None when no value follows, existing mention/function-word/narrative-word exceptions and the auth-scheme pass-through are preserved, and tests cover 'password:', 'password:\n', 'password:\n\n' and the bearer form.
- FR-10 / AC-9: secret-free text, including punctuation, line breaks and several lines, is returned unchanged character for character.: pass — Non-secret labels never enter the binding path and the masking replaces only spans; tests cover multiline secret-free text in English and Russian and the full existing suite still passes per QA.
- FR-11 / AC-11: every masking form the client already handles keeps its current rendering and the whole existing expectation suite passes.: pass — No existing expectation was removed or weakened; the environment gate and test runs passed and the preserved space/colon/equals/quote/JSON/quoted-label cases are untouched.
- AC-12 (review-only): the finding is resolved for any secret label, any explicit separator and any punctuation, not only the named examples.: pass — The rule is generic over labels (including Russian stems, compounds and quoted labels), both explicit separators and any non-alphanumeric punctuation; tests exercise several labels, separators and punctuation characters, so the fix is not tuned to the audit examples.
- Scope and repository rules: one coherent change, only needed files, no unrelated/temporary/debug/generated files, no unrequested feature, no weakened or deleted test, no documentation change.: pass — Only `forgel_code/interactive.py` and `tests/test_redact.py` are committed; the added test engine is a legitimate test fixture, there is no configuration, interface or documentation change, and no test removal was detected.

## Blocking

- none

## Test Removals

- none


