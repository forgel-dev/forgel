# Task Review: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-23T22:54:38+00:00

## Summary

The redactor rewrite handles colon, equals, whitespace, authorization-scheme, Russian, compound and benign-prose forms correctly, and the environment checks pass. Two pinned forms are nevertheless wrong: a quoted value is masked together with its quotation marks (`password: "hunter2 and more"` renders `password: [redacted]` instead of `password: "[redacted]"`), and a repeated separator loses a character (`password==hunter2` renders `password=[redacted]` instead of `password==[redacted]`). Neither form is covered by the attributed tests, and the replacement tests cited in the developer justification are not present in the repository, so the change does not satisfy the quoted-value requirement and does not byte-preserve text outside the masked value for repeated separators.

## Requirements

- Masking replaces the value bound to a recognized secret-bearing label with the fixed marker and preserves the label.: pass — Colon, equals, whitespace, scheme, Russian and compound forms replace the value and keep the label.
- A value after a secret keyword and a colon, with or without whitespace, is masked.: pass — `token:abc123` and `password: hunter2` mask the value.
- A value after a secret keyword and an equals sign, with or without surrounding whitespace, is masked.: pass — `password=hunter2` and `password = hunter2` mask the value; the repeated-separator case is reported separately.
- The previously supported whitespace single-token form continues to mask.: pass — `token abc` masks `abc`.
- An authorization scheme word after a label or separator stays visible and the credential after it is masked.: pass — `Authorization: Bearer abc123` and `the token Bearer secretvalue` keep the scheme word and mask the credential.
- Russian and compound labels are recognized case-insensitively and masked.: pass — `пароль:`, `Пароль=`, `токен`, `db_password=`, `aws.secret.key:`, `api-key=` and `AWS_SECRET_ACCESS_KEY=` all mask.
- Text not bound to a recognized secret-bearing label is displayed unchanged.: pass — `Password updated.`, `Secret rotation scheduled`, `the token is missing`, `rotate the password please`, `send the secret later`, `release: 0.1.1 open`, empty text and the Russian sentence are unchanged.
- Masking is idempotent, and empty or secret-free text is returned unchanged.: pass — The idempotence and secret-free cases in tests/test_redact.py pass for the covered forms.
- Every engine reply and every engine error that reaches the session display is masked.: pass — The session tests check an engine reply, a task title and an engine error; the QA e2e checks pass.
- Previously working session behavior continues to work.: pass — The QA local and e2e checks pass, and tests/test_interactive.py is unchanged.
- A quoted value is masked whole while its quotation marks stay visible.: fail — `_span` returns a span that includes the opening and closing quote, so `password: "hunter2 and more"` is rendered `password: [redacted]` instead of `password: "[redacted]"`, contrary to FR-1, FR-4 and AC-6; tests/test_redact.py has no quoted-value case.
- A run of separator characters binds the following value and the separators are preserved (`password==hunter2` -> `password==[redacted]`).: fail — `_binding` passes the position after the first separator to `_bound_value`, which treats the second `=` as the first character of the value; `password==hunter2` is rendered `password=[redacted]`, altering a character outside the masked value (FR-1, FR-3, AC-1).
- For each recognized form the secret value does not appear as a substring anywhere in the displayed text.: pass — The masked spans remove the value; the two failures above concern the characters left around the mask, not the value appearing.
- Each listed masking form is demonstrable as an executable example in the client's test area, and the replacement tests named in the developer justification exist.: fail — tests/test_redact.py has no quoted-value test and no exact assertion for `password==hunter2`; the cited replacements (`test_separator_bound_values_are_masked_whole`, `test_a_bare_label_binds_a_word_that_is_not_prose`, `test_russian_and_compound_labels_are_masked`, `test_benign_prose_is_displayed_unchanged`) are absent from the repository.

## Blocking

- Quoted values lose their quotation marks: `redact('password: "hunter2 and more"')` yields `password: [redacted]`, not the required `password: "[redacted]"` (FR-1, FR-4, AC-6), and no test covers the form.
- Repeated separators are altered: `redact('password==hunter2')` yields `password=[redacted]`, not `password==[redacted]` (FR-1, FR-3, AC-1), because the second `=` is treated as the start of the value.
- The attributed test file does not exercise the quoted-value form or pin the `password==hunter2` rendering, and the replacement tests named in the developer justification are not present in the attributed change.

## Test Removals

- none

- tests/test_redact.py::RedactFormTest::test_a_colon_joined_value_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_separator_bound_values_are_masked_whole
- tests/test_redact.py::RedactFormTest::test_an_equals_joined_value_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_separator_bound_values_are_masked_whole
- tests/test_redact.py::RedactFormTest::test_a_whitespace_joined_value_still_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_a_bare_label_binds_a_word_that_is_not_prose
- tests/test_redact.py::RedactFormTest::test_a_russian_label_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_russian_and_compound_labels_are_masked
- tests/test_redact.py::RedactFormTest::test_a_compound_label_is_masked: replaced -> tests/test_redact.py::RedactFormTest::test_russian_and_compound_labels_are_masked
- tests/test_redact.py::RedactFormTest::test_a_mentioned_label_is_left_alone: replaced -> tests/test_redact.py::RedactFormTest::test_benign_prose_is_displayed_unchanged
