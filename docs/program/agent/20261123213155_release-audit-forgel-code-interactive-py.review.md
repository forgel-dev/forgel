# Task Review: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-23T22:31:07+00:00

## Summary

The change rewrites `redact()` into a label/binding parser that covers colon-, equals-, scheme-, Russian- and compound-label forms, and it adds `tests/test_redact.py` including session-level checks that replies, engine state and engine errors are masked before display. However, the prose/credential heuristics the implementation introduces break two opposing requirements. First, a clause-initial secret word followed by an ordinary word is treated as a bound value, so benign text such as `Password updated.` or `Secret rotation scheduled` is altered, which contradicts the requirement that text merely mentioning a secret word is displayed unchanged. Second, the previously working whitespace form is now gated on the label starting a clause or the value looking credential-like, so a mid-sentence form such as `the token abc` or `set password swordfish` is no longer masked, regressing the previously supported behavior and leaving the secret visible. The tests only cover the forms that happen to pass, so neither defect is caught.

## Requirements

- FR-1: a bound value is replaced by one fixed mask marker while the label is preserved.: pass — The rewritten `redact()` splices `[redacted]` over the bound span and keeps the label text; the tests confirm the label stays next to the mask.
- FR-2: a value after a secret keyword and a colon, with or without whitespace, is masked.: pass — Covered by `test_a_colon_joined_value_is_masked`; the `:` branch in `_binding` does not depend on surrounding prose.
- FR-3: a value after a secret keyword and an equals sign, with or without surrounding whitespace, is masked.: pass — Covered by `test_an_equals_joined_value_is_masked` and by the compound-label cases.
- FR-4: a value after a recognized secret keyword and whitespace (the previously supported single-token form) continues to be masked.: fail — The whitespace branch requires the label to stand alone or the next word to look credential-like (`_stands_alone` / `_looks_like_credential`). `the token abc`, `set password swordfish` or `установлен пароль swordfish` therefore stay unmasked, although the previous implementation masked the following token in any position.
- FR-5: a value after a secret keyword plus colon or whitespace and an authorization scheme word is masked, scheme word may stay.: pass — `test_an_authorization_scheme_stays_visible` shows `Authorization: Bearer [redacted]` and `the token Bearer [redacted]`.
- FR-6: English and Russian secret labels are recognized for colon, equals and whitespace forms.: pass — Russian stems are matched case-insensitively and the colon/equals cases pass; the whitespace Russian case shares the FR-4 defect and is reported there.
- FR-7: a compound label with a secret keyword as one segment has its value masked.: pass — `_segments`/`_secret_label` handle `_`, `.` and `-`, and the compound cases in `test_a_compound_label_is_masked` pass.
- FR-8: label recognition is case-insensitive, including non-English labels.: pass — Labels are lower-cased before matching; `Пароль=hunter2` is masked.
- FR-9: text not bound to a recognized secret-bearing label is displayed unchanged, including ordinary sentences that merely mention a secret word.: fail — A clause-initial label followed by any word that is not in the prose list is treated as bound: `Password updated.` becomes `Password [redacted].` and `Secret rotation scheduled` is altered. That is an ordinary sentence mentioning the label without a value, and it violates this requirement.
- FR-10: the label text is preserved next to the mask.: pass — The label span is never replaced; only the value span is.
- FR-11/AC-9 (review-only): every engine reply and every engine error is masked before it reaches the session display.: pass — The attributed session tests exercise the reply path, the engine-state path and the error path and assert the values are absent and `[redacted]` is present; the diff does not remove any display-side redaction call.
- FR-12: masking empty or secret-free text returns it unchanged and masking twice neither errors nor reveals a value.: pass — `redact('')` returns early, `_span` recognizes an existing `[redacted]` span, and `test_redaction_is_idempotent`/`test_secret_free_text_is_unchanged` pass.
- FR-13: previously working session behavior, including the masking forms that already worked, does not regress.: fail — The old implementation masked the token following a secret keyword anywhere in the text; the new standalone/credential heuristic drops that for mid-sentence occurrences, so a previously masked form now leaks.
- AC-6: a message that merely mentions a secret word without binding a value is displayed unchanged.: fail — Only the three chosen sample sentences are tested; `Password updated.` is a counterexample that is masked.
- AC-7: a message with no secret-bearing label is displayed byte-for-byte unchanged.: fail — Messages with no secret at all are preserved, but the requirement is contradicted for ordinary messages mentioning a label: `Token expired` is rewritten to `Token [redacted]`.
- AC-10: for each recognized form the secret value does not appear as a substring of what the user is shown.: fail — The whitespace-joined form leaks when it appears mid-sentence and the value is short and alphabetic, e.g. `the token abc` is displayed unchanged.

## Blocking

- FR-9/AC-6/AC-7: a clause-initial secret label followed by an ordinary word is masked as if bound, so benign text such as `Password updated.` or `Secret rotation scheduled` is altered instead of displayed unchanged.
- FR-4/FR-13/AC-10: the previously working whitespace form is no longer masked mid-sentence when the value is short and alphabetic (e.g. `the token abc`, `set password swordfish`), so the secret remains visible.

## Test Removals

- none


