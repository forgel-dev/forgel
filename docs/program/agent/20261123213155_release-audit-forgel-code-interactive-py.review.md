# Task Review: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T23:07:55+00:00

## Summary

The attributed change replaces the narrow token-based redactor with a structured label/binding recogniser in forgel_code/interactive.py and rebuilds tests/test_redact.py around the acceptance criteria. Reading the final state against the specification: labels are recognised case-insensitively as single words or '_', '.' and '-' compounds whose segment is a secret word, plus Russian stem-based labels (FR-2); ':' and '=' runs bind and mask a whole value, a quoted run is masked between visible quotes, an authorization scheme word stays visible while the credential after it is masked, a copula is skipped and the following word decides by the stated prose-vocabulary rule, and the marker is never re-masked (FR-1, FR-3, FR-4, FR-5, FR-6, FR-7, FR-10). Every pinned example in AC-1 to AC-6 resolves to exactly the stated output (token:abc123, password = hunter2, password==hunter2, Authorization: Bearer abc123, the token Bearer secretvalue, токен: abc123, AWS_SECRET_ACCESS_KEY=abc, db_password=hunter2, aws.secret.key: hunter2, api-key=hunter2, token abc, токен abc123, the token abc, set password swordfish, password: "hunter2 and more"), and the benign set (Password updated., Secret rotation scheduled, the token is missing, rotate the password please, send the secret later, release: 0.1.1 open, empty text, the Russian sentence) is returned byte-for-byte unchanged because those words are in the fixed prose vocabulary and the empty input short-circuits. Blanket over-masking is the direction the specification explicitly accepts as safe, and the one odd edge I found (a label wrapped in quotes, where the closing quote is read as an opening quote and the rest of the line is masked) is not a pinned form and never leaks a value. The test file maps one-to-one onto the acceptance criteria plus three session-level tests that run real stubbed engines and assert that a reply, a task title and an engine error reach a captured screen with the value absent and the label plus marker present; none of the pre-change scenarios is left uncovered, and the declared 'replaced' names correspond to renamings inside this same attributed change series, with the original scenarios still present and passing. Nothing unrelated, temporary or generated is committed, QA and the acceptance checks pass, and no secret or weakened test is present.

## Requirements

- A value bound to a recognised secret label is replaced by the single mask marker while the label and surrounding text stay identical.: pass — FR-1: redact() splices only the bound span and keeps everything before and after it unchanged; the marker stays [redacted].
- Colon-bound and equals-bound values are masked with or without surrounding whitespace, and multiple separator characters stay visible.: pass — FR-3 and AC-1: token:abc123, password: hunter2, password = hunter2 and password==hunter2 all resolve to the pinned output; the separator run is consumed but emitted verbatim.
- A bare label followed by whitespace masks the next word unless the word is recognised everyday prose.: pass — FR-6/FR-9 and AC-5: token abc, the token abc, токен abc123 and set password swordfish are masked, while the prose vocabulary keeps narrating words untouched; the rule is applied wherever the label sits, with no clause-start gating.
- An authorization scheme word stays visible and the credential after it is masked, with or without a separator, taking precedence over the bare-label rule.: pass — FR-5 and AC-2: both Authorization: Bearer abc123 and the token Bearer secretvalue keep the scheme word and mask the credential; the scheme set matches the specified list.
- Russian and compound labels (including environment-style names) mask their value; label recognition is case-insensitive.: pass — FR-2 and AC-3: the stem set and the '_', '.', '-' compound segmentation cover пароль:, Пароль=, токен:, db_password=, aws.secret.key:, api-key= and AWS_SECRET_ACCESS_KEY=, and comparison is lower-cased throughout.
- Quoted values are masked whole between visible quotation marks, including an unclosed quote.: pass — FR-4/AC-6: the quote-pair map masks only the content for double, single, backtick and guillemet quotes and masks to end of line when no closing quote exists.
- A copula or auxiliary between label and value is skipped and itself stays visible.: pass — FR-7: the copula set (English and Russian) jumps to the following word and the immutable text keeps the copula in place.
- Text not bound to a secret label is displayed unchanged, including benign sentences that mention a secret word.: pass — FR-8 and AC-4: Password updated., Secret rotation scheduled, the token is missing, rotate the password please, send the secret later, release: 0.1.1 open, empty text and нажмите на кнопку (дважды)! all come back identical.
- Masking is idempotent, never double-masks, and returns empty text unchanged.: pass — FR-10: the marker is matched before any value rule and replaced by itself; redact('') returns '' immediately, and the idempotence test covers every masked form.
- Every engine reply and every engine error that reaches the session screen is masked, with no bypass path.: pass — FR-11/AC-8: session-level tests drive real stubbed engines and assert that a reply, a task title and an error message show neither value fragment while the label and marker are visible.
- Previously working behaviour does not regress and no test is deleted without justification.: pass — AC-9: the existing separator, scheme, Russian, compound and mention scenarios are all still present in the final tests/test_redact.py and pass, and the worktree is clean with only the two attributed files changed.

## Blocking

- none

## Test Removals

- none

- tests/test_redact.py::RedactFormTest::test_a_colon_joined_value_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_separator_bound_values_are_masked_whole
- tests/test_redact.py::RedactFormTest::test_an_equals_joined_value_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_separator_bound_values_are_masked_whole
- tests/test_redact.py::RedactFormTest::test_a_whitespace_joined_value_still_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_a_bare_label_binds_a_word_that_is_not_prose
- tests/test_redact.py::RedactFormTest::test_a_russian_label_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_russian_and_compound_labels_are_masked
- tests/test_redact.py::RedactFormTest::test_a_compound_label_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_russian_and_compound_labels_are_masked
- tests/test_redact.py::RedactFormTest::test_a_mentioned_label_is_left_alone: replaced -> tests/test_redact.py::RedactFormTest::test_benign_prose_is_displayed_unchanged
