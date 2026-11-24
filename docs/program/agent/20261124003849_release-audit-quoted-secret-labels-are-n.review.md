# Task Review: Release audit: Quoted secret labels are not fully redacted. For a message such as `'token': 'ab

- Task: `20261124003849_release-audit-quoted-secret-labels-are-n`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T01:12:30+00:00

## Summary

The change fixes the quoted-label masking gap in the shared redaction step (`_binding` in `forgel_code/interactive.py`) instead of at a display site: `_label_quote_end` decides whether the quote after a label closes the label (separator, space or trailing punctuation) or opens a value (alnum/value characters glued to it), and `_quoted_binding` then resolves the value either through a separator (reusing `_separator_end`/`_bound_value`, so repeated separators stay visible and unquoted values stop at whitespace) or as an adjacent quoted run. Label, its two quotes and the separator stay outside the masked span, and the value's own quotes stay around the placeholder through the existing quoted-span logic, so single-quoted, double-quoted and JSON-style (`"token":"...`) forms all mask fully while `the word "token" appears here`, `say 'password' please`, `"secret" is missing` and `the 'token' was rotated.` stay unchanged. Tests were added, not weakened: `tests/test_redact.py` gains cases for the single-quoted, double-quoted and JSON-style forms, unquoted values after quoted labels, repeated separators, neighbour non-masking, idempotence with exactly one placeholder, absence of any value character, and an end-to-end session check with a quoted label in an engine reply; the existing reply stub was extended (not relaxed) and the pre-existing assertions on `token: [redacted]` still hold. QA reported pass for the local and environment acceptance checks and no test removals. The commit is scoped to the two needed files with no unrelated, temporary or generated content.

## Requirements

- FR-1: A single-quoted secret label keeps the label and both quotes and the separator, and the value becomes the masking placeholder.: pass — `_label_quote_end` treats the closing quote as part of the label when a separator follows; tests `'token': 'abc123'`, `'password'='hunter2'`, `'secret': 'swordfish'` check the exact displayed text.
- FR-2: A double-quoted label, including the JSON-style form with the closing quote directly followed by a colon, keeps label, quotes and separator, and masks the value.: pass — `"token": "abc123"`, `"password" = "hunter2 and more"`, `"secret" : "swordfish"` and `{"token":"abc123"}` are covered with exact expected output.
- FR-3: A quoted value keeps its own quotes around the placeholder with no character of the value left.: pass — The mask reuses the existing quoted-span logic; `test_no_character_of_a_quoted_secret_stays_visible` asserts the value is absent while the quotes remain.
- FR-4: An unquoted value after a quoted label is masked up to the next whitespace or end of message.: pass — `_quoted_binding` delegates to `_bound_value`, and `'token': abc123 now` -> `'token': [redacted] now` is tested.
- FR-5: No character of a quoted-label secret appears in reply text, engine state or engine error text.: pass — The fix sits in the shared `redact` path used at every display point; the session-level test asserts `abc123` is absent from the engine reply output.
- FR-6: Masking an already masked message changes nothing further.: pass — Quoted forms were added to the idempotence table in `test_redaction_is_idempotent`.
- FR-7: Exactly one placeholder per masked value, and repeated separators between a quoted label and its value stay visible.: pass — `'token':: abc123` -> `'token':: [redacted]` and `"token" == "abc123"` are tested; placeholder counting is asserted (`count("[redacted]") == 1`).
- FR-8: Messages with no secret binding, and messages that only mention a secret label, are displayed unchanged.: pass — `_quoted_binding` returns no span without a separator or adjacent quoted run; `test_a_quoted_label_does_not_mask_its_neighbours` covers four mention-only sentences.
- FR-9: The label's quotation marks never cause a neighbouring word, separator or trailing punctuation to be masked.: pass — Returning the mask span after the label's closing quote keeps the surrounding text intact; `say 'password' please`, `"secret" is missing` and `the 'token' was rotated.` are asserted unchanged.
- FR-10: The automated suite covers single-quoted label with single-quoted value, double-quoted label with double-quoted value, and the JSON-style form.: pass — Three dedicated test methods cover exactly these forms, plus the JSON-style case where the label's closing quote is directly followed by the colon.
- FR-11: The existing suite continues to pass with no test weakened, skipped or deleted.: pass — No test removals were detected and no assertions were relaxed; the reply stub was extended with a quoted label while keeping the previously asserted `token: abc123` fragment, and QA reported the full suite and acceptance checks passing.
- AC-1: Single-quoted label with single-quoted value masks the value and the value cannot be found in the displayed line.: pass — Exact-output and substring-absence assertions plus QA's acceptance check.
- AC-2: Double-quoted label with double-quoted value (closing quote directly followed by a colon) masks the value and the value cannot be found.: pass — Covered by the JSON-style and double-quoted tests with exact output and absence checks.
- AC-3: Single-quoted label with unquoted value yields a single placeholder, nothing of the value left, no neighbouring word masked.: pass — `'token': abc123 now` -> `'token': [redacted] now` with placeholder count 1 and absence assertions.
- AC-4: Masking an already masked quoted-label message leaves it unchanged, one placeholder per value.: pass — `test_redaction_is_idempotent` includes the quoted forms and asserts `redact(once) == once` with `count("[redacted]") == 1`.
- AC-5: Messages without a secret binding and mention-only messages are displayed unchanged.: pass — Covered by the neighbour non-masking test and the existing mention/secret-free tests, which remain unchanged.
- AC-6: The suite contains passing checks for the single-quoted, double-quoted and JSON-style forms and the whole suite passes.: pass — The three test methods exist; QA's environment and acceptance runs reported pass with exit 0.
- Change is coherent and scoped: only the files the task needs, no unrelated, temporary, debug or generated files.: pass — The diff touches only `forgel_code/interactive.py` and `tests/test_redact.py`; the worktree is clean and no changes were escalated.

## Blocking

- none

## Test Removals

- none


