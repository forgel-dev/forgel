# Task Review: Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw

- Task: `20261124003849_release-audit-the-session-keeps-unredact`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T04:51:53+00:00

## Summary

The attributed change does exactly what the release-audit finding requires: `show_state`, the forced branch of `refresh`, and `idle_refresh` now mask engine-produced text with the existing `redact` routine before it is stored in `last_state` / `idle_failure`, so the in-memory copy equals what the screen showed and a later repeat cannot reveal a secret. Display paths are unchanged and are shown by the new tests to already mask, so displayed and retained text coincide. Secret-free text keeps its previous form because `redact` leaves it untouched, and the new tests explicitly assert idempotence of `redact` on the retained copy (AC-4). The change is scoped to the two reported retention points named in the specification's assumptions, does not touch masking rules, the marker, the parsed answer, or persist anything, and adds regression coverage for both engine answers and engine errors (FR-4). The added test file is real product regression coverage, not a documentation guard, and no pre-existing test was removed or weakened. The environment gate and the listed acceptance checks pass.

## Requirements

- FR-1: Any text produced by the engine that the client keeps in memory for the session is masked before it is kept (state text and idle-refresh failure text).: pass — `show_state` stores `redact("\n".join(lines))`, `refresh(force=True)` stores `redact(...)`, and `idle_refresh` stores `redact(exc.message)`; the specification's assumption names these two as the only engine-derived retained texts.
- FR-2: The retained state text shown by the state display is the masked text; repeating the display later does not reveal the secret.: pass — The same masked string is both stored in `last_state` and written, so a later repeat of the retained text stays masked; covered by `test_repeating_a_retained_state_display_shows_the_mask`.
- FR-3: The retained idle-refresh failure text is masked before retention and any later display shows only the mask.: pass — `failure = redact(exc.message)` is compared and stored, and `show_failure` is exercised by a test that asserts no readable secret reaches the output.
- FR-4: Masking applies equally to engine answers and engine error messages.: pass — State text (answer-derived) and `EngineError` messages are both redacted; regression tests cover both a secret-bearing state and a secret-bearing error.
- FR-5: Text that carries no key material is retained and shown unchanged, apart from the masking applied today.: pass — `redact` is applied to the same text as before and is the pre-existing routine; `test_secret_free_state_is_retained_unchanged` asserts byte-identical retention and display for a clean state.
- FR-6: Masking an already-masked retained text leaves it unchanged, with one marker per masked value.: pass — Retained copies are asserted equal to their own re-redaction in both the state and failure tests, confirming no stacked marker and no content loss.
- FR-7: What the user sees on a later repeat equals what the client retained; no path where the retained copy is more revealing than the display.: pass — Retention now uses exactly the displayed (masked) string in every touched path; the tests assert absence of the raw value in both the retained attribute and the output.
- FR-8: No other client behavior changes and the existing test suite passes.: pass — Only the three retention points changed; deduplication now compares masked messages, which for secret-free text is identical to before. Environment gate and listed acceptance checks report pass, and no test was removed.
- AC-1/AC-2/AC-3/AC-4/AC-5: Acceptance criteria for secret-bearing answers, secret-bearing errors, secret-free text, idempotent re-masking and repeated displays.: pass — Each criterion has a matching assertion in tests/test_retained_text.py, and the acceptance checks for the masked-answer and secret-free cases are recorded as passing.
- AC-6: All pre-existing tests pass.: pass — QA verdict is pass; no test removals were detected in the attributed commit.
- Non-goals/constraints: no change to masking rules, marker or secret labels, no change to engine requests or parsing, no persistence, no new stored artifact, no unrelated refactor or new interface.: pass — The diff only wraps existing masked text at retention points and adds one focused test module; nothing else in the client is touched.
- No unrelated, temporary, debug or generated files in the change, and every needed file present.: pass — The commit contains only forgel_code/interactive.py and the new tests/test_retained_text.py; the worktree is clean and no escalated changes exist.

## Blocking

- none

## Test Removals

- none


