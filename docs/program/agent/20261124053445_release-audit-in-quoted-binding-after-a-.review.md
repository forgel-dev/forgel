# Task Review: Release audit: In `_quoted_binding`, after a quoted label and whitespace, a bare next token ret

- Task: `20261124053445_release-audit-in-quoted-binding-after-a-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T06:01:08+00:00

## Summary

The change closes the quoted-label gap in credential masking: `_quoted_binding` no longer stops at the separator/quoted-run branches but also evaluates the bare word after a quoted label and reuses the existing binding helpers (`_scheme_value`, `_copula_span`, `_carries_markers`, `_span`), so a quoted label followed by a bare value is masked with the same placeholder and the same value boundaries as an unquoted label. A new `_closes_clause` helper and two constants (`_INLINE_WHITESPACE`, `_CLAUSE_END`) keep a plain word that merely continues the sentence from being treated as a value, and quoted words with nothing after them (end of line, punctuation) stay untouched, so unrelated output is unchanged. Both quote styles route through the same code path. The added test module covers every acceptance criterion including idempotency and preservation of the already-working forms, no existing test was edited or removed, and QA reports the full suite, the environment test and the acceptance checks passing on a clean worktree with only the two task files committed. The earlier masking outcomes for separators, quoted values and unquoted labels are preserved; handling of an auth-scheme or copula word between the quoted label and its value is an extension that follows the same leak-prevention intent and does not contradict any acceptance criterion.

## Requirements

- After a quoted label, whitespace and a bare unquoted value, the binding is treated as a credential binding and the value is masked.: pass — The final branch of `_quoted_binding` resolves the bare token after `_skip_gap` and returns its span, so the value is replaced by the existing `[redacted]` placeholder; verified by the masked-output acceptance check and the new quoted-bare tests.
- Single-quoted and double-quoted labels are treated identically in that detection.: pass — Both quote styles reach `_quoted_binding` after `_label_quote_end`; there is no quote-specific branch, and the new tests cover each style for the bare-value case.
- A quoted label followed by a separator and a value is still masked.: pass — The separator branch is untouched and still runs before the new code; covered by the existing quoted-label separator tests and the new regression tests.
- A quoted label followed by a quoted value is still masked.: pass — The `_QUOTE_PAIRS` branch is unchanged and precedes the new logic; covered by existing and new tests.
- An unquoted label followed by a bare value is still masked.: pass — The unquoted path is not modified; the change only adds a branch in `_quoted_binding`, and the suite passes.
- A quoted word with no value after it (end of line, punctuation) is not masked.: pass — At end of text `_quoted_binding` returns early, and `_label_end` returns None when punctuation follows, so such quoted words stay untouched; the new tests assert this for `'token'`, `'token'.` and comma cases.
- Output that contains no credential binding is returned unchanged.: pass — The new logic is gated by secret-label recognition and by `_is_prose`/`_carries_markers`/`_closes_clause`, and the new no-binding tests plus the full suite pass.
- No existing automated test is weakened, removed or modified to obtain the result.: pass — The attributed diff touches only `forgel_code/interactive.py` and the new `tests/test_redact_quoted_bare.py`; no existing test file appears in the commit and no removal was reported.
- The full existing test suite passes.: pass — QA verdict is pass on the environment gate, the e2e checks and the acceptance command, on a clean worktree.
- The change is coherent, includes every needed file and excludes unrelated, temporary or generated files.: pass — Only the implementation module and its focused test module are committed; helper constants are placed with the other masking constants and the docstring is updated to match the new behavior.

## Blocking

- none

## Test Removals

- none


