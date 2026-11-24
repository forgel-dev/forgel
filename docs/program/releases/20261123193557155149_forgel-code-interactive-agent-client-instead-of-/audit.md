# Release audit 20261123193557155149_forgel-code-interactive-agent-client-instead-of-

- Round: 5
- Verdict: fail
- At: 2026-11-24T12:39:30+00:00

## Summary

The release delivers the interactive client and the successive redaction, localization, idle-refresh, retained-state and sensitive-action fixes, and the reported suites (369 tests at the final task) pass. One blocking gap remains in the redaction contract: the French password label is recognized only in its whitespace-separated form, so the common joined spellings are shown and retained unmasked. That can leak a password in an engine reply or error and violates the requirement that secrets and key material never appear in the session.

## Findings

- [major] code: The redactor recognizes the French password label only as the whitespace-separated phrase `mot de passe`. Joined forms such as `mot_de_passe` and `mot-de-passe` are parsed as a single compound label whose segments (`mot`, `de`, `passe`) are not in `SECRET_WORDS`/`SECRET_WORDS_FOLDED`, so `_secret_label` returns false and `_phrase_end` (which compares the first label to `mot`) does not match. An engine reply or error such as `mot_de_passe=hunter2` or `mot-de-passe: hunter2` is therefore displayed and retained with the value intact, leaking a password and violating the requirement that secrets/key material never appear in the session. The task-11 review notes this residual but dismisses it; it is a data leak, not an optional improvement. — Treat the joined forms as the French password label: fold case and diacritics and accept whitespace, `-` and `_` between the words in `_secret_label`/`_phrase_end` (or normalize the label before matching). Add direct and session-level tests asserting that a value following `mot_de_passe`, `mot-de-passe` or `MOT_DE_PASSE` is absent from both the displayed and the retained text.
