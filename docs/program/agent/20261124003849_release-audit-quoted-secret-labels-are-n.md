# Agent Run: Release audit: Quoted secret labels are not fully redacted. For a message such as `'token': 'ab

- Task: `20261124003849_release-audit-quoted-secret-labels-are-n`
- Status: `done`
- Repository: `code`
- Steps: 36
- Finished: 2026-11-24T01:05:31+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- A quoted value belongs to the quoted label as a whole: the marker sits inside the value's own quotes, so the rest of the quoted run is masked too, matching the existing behaviour for unquoted labels with quoted values (`password: "hunter2 and more"`).
- A quoted label binds a value only through an `=`/`:` separator or an immediately adjacent quoted run; a plain word after the closing quote still counts as a mention and stays visible.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 36
- Estimated input tokens (all calls): 1131655
- Provider input/output tokens: 1171158 / 113059
- Provider cache hit/miss tokens: 1067392 / 103766
- Estimated prompt at the end: 37280 tokens
- State: `docs/program/agent/20261124003849_release-audit-quoted-secret-labels-are-n.state.md`

## Specification (`docs/program/specs/20261124003849_release-audit-quoted-secret-labels-are-n.md`)

# Task Spec: Release audit: Quoted secret labels are not fully redacted. For a message such as `'token': 'ab

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: Quoted secret labels are not fully redacted. For a message such as `'token': 'ab |
| Project | — |
| Task | `20261124003849_release-audit-quoted-secret-labels-are-n` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T00:39:45+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client's session display masks secret values before showing engine output, but its recognition of where a secret value begins fails when the secret label is itself written inside quotation marks. In a message such as a single-quoted label followed by a single-quoted value, or the JSON-style double-quoted equivalent, the closing quote of the label is mistaken for the opening quote of the value. The masked span therefore covers only the separator and the secret value stays visible in the session, which breaks the promise that key material never reaches the screen.

**Outcome:** A secret whose label is quoted, in single or double quotes and in the JSON-style form, is masked in full wherever the session displays text: the label, its own quotes and the separator stay readable, the value is replaced by the masking placeholder, and no character of the value appears. All previously guaranteed masking behavior (unquoted labels, equals and colon separators, whitespace-joined values, authorization schemes, Russian and compound labels, label-only mentions, idempotence, one placeholder per masked value) is unchanged and still holds.

## Product Intent

The client is a thin display over the engine's answers and must never show key material that an engine answer, a task title or an engine error carries. Owners read session output and paste it into reports and conversations, so any secret that escapes masking becomes a disclosure.

## User Experience

An owner reading a session line that quotes a secret label, such as a configuration fragment echoed by the engine, sees a masked placeholder where the value was and can read the rest of the line normally. The value never appears, and pasting the line elsewhere shares no secret.

## Roadmap

—

## Goals

- Remove the masking gap for quoted secret labels so that no secret value bound to a quoted label reaches the session display.
- Keep every previously guaranteed masking behavior and every existing test result intact.

## Non-Goals

- Changing which words count as secret labels.
- Changing the masking placeholder or the masking of unquoted labels, other separators, authorization schemes, Russian or compound labels.
- Changing the engine, its answers or its own secret handling.
- Redacting arbitrary quoted text, JSON documents as a whole, or content that carries no secret label.
- Changing how the session obtains, renders or formats engine answers.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself, so secrets are protected by the client's own display layer and not by changing the engine. | D-002, user decision log, 2026-11-16 18:31 |
| — | The client is a Python package installed as a console client with a Pareto 20/80 scope and imports nothing from the engine. | D-004, user decision log, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: When a message contains a secret label enclosed in matching single quotation marks, followed by a separator and a value, the displayed text keeps the label and both of its quotation marks as they are, keeps the separator as it is, and replaces the value with the masking placeholder.
- **FR-2**: When a message contains a secret label enclosed in matching double quotation marks, including the JSON-style form where the label's closing quote is directly followed by a colon, the displayed text keeps the label and both of its quotation marks and the separator as they are, and replaces the value with the masking placeholder.
- **FR-3**: When the value of a quoted secret label is itself quoted, the value's own quotation marks stay visible around the masking placeholder and no character of the value remains.
- **FR-4**: When the value of a quoted secret label is unquoted, the whole value up to the next whitespace or the end of the message is replaced by the masking placeholder.
- **FR-5**: No character of a secret bound to a quoted label appears in any text the session displays, including reply text, engine state and engine error text.
- **FR-6**: Masking a message that is already masked changes nothing further.
- **FR-7**: Each masked value carries exactly one masking placeholder, and repeated separator characters between a quoted label and its value stay visible.
- **FR-8**: A message with no secret bound to a label, and a message that only mentions a secret label without binding a value to it, is displayed unchanged.
- **FR-9**: The quotation marks that a fix introduces as part of the label never cause a neighbouring word, a separator or trailing punctuation to be masked.
- **FR-10**: The automated test suite covers a single-quoted secret label with a single-quoted value, a double-quoted secret label with a double-quoted value, and the JSON-style form where the label's closing quote is directly followed by the separator.
- **FR-11**: The existing test suite continues to pass without any test being weakened, skipped or deleted.

## User Stories

- As an owner reading the session, I want a secret whose label is quoted to be masked in full, so that the value never reaches my screen or anything I paste elsewhere.
- As an owner pasting a session line into a report, I want quoted configuration fragments to keep their readable structure with only the secret replaced, so that the line still makes sense.

## Acceptance Criteria

- **AC-1**: A session line carrying a single-quoted secret label with a single-quoted value displays the label and its quotes, the separator, and the masking placeholder in place of the value; searching the displayed line for the value finds nothing.
- **AC-2**: A session line carrying a double-quoted secret label with a double-quoted value, in the form where the label's closing quote is directly followed by a colon, displays the label and its quotes, the colon, and the masking placeholder in place of the value; searching the displayed line for the value finds nothing.
- **AC-3**: A single-quoted secret label followed by an unquoted value displays the value replaced by a single masking placeholder, with nothing of the value left and no neighbouring word masked.
- **AC-4**: Masking an already masked message that carries a quoted secret label leaves it unchanged, and each masked value carries exactly one masking placeholder.
- **AC-5**: Messages without a secret binding, and messages that only mention a secret label, are displayed unchanged.
- **AC-6**: The automated test suite contains passing checks for the single-quoted form, the double-quoted form and the JSON-style form, and the whole suite passes.

## Scope Boundaries

- Recognizing the closing quotation mark of a quoted secret label as part of the label rather than as the start of the value.
- Masking the full value of a quoted secret label, in single quotes, double quotes and the JSON-style form.
- Masking an unquoted value that follows a quoted secret label.
- Keeping the label's own quotes, the separator and the surrounding text unchanged.
- Preserving every existing masking behavior and idempotence.
- Covering both quoted-label forms in the automated test suite.
- Changing which words count as secret labels.
- Changing the masking placeholder or the masking of unquoted labels, other separators, authorization schemes, Russian or compound labels.
- Changing the engine, its answers or its own secret handling.
- Redacting arbitrary quoted text, JSON documents as a whole, or content that carries no secret label.
- Changing how the session obtains, renders or formats engine answers.

## Risks

- Treating any quote after a label as part of the label could over-match ordinary prose that uses apostrophes, leaving text unchanged where a mask was expected.
- A narrow fix for the quoted case could regress the already guaranteed unquoted, equals-separated, whitespace-joined or authorization-scheme masking.
- The change could break idempotence or produce two placeholders for one value.
- If the fix is applied only at one display site, another place where engine text reaches the screen stays unprotected.
- Over-broad masking of JSON-style text could hide non-secret adjacent fields, which the acceptance rejects.

## Open Questions

- None.

## Assumptions

- A quotation mark immediately appended to a secret label, with no separator between them, belongs to the label when the same quote character also opens the value; this is what distinguishes the label's closing quote from the value's opening quote.
- The masked placeholder already used for unquoted values is the correct representation for quoted values as well, and it sits inside the value's own quotes.
- Masking continues to apply at every point where the session displays text, so the fix belongs to the shared masking step rather than to one display site.
- Values of quoted labels end at the next whitespace or the end of the message when they are unquoted.

## Related Documents

- README.md
- CHANGELOG.md

## Revision History

- 1.0 — initial specification of the release-audit finding about quoted secret labels not being fully redacted.


## Summary

Extended the session masking so a secret label wrapped in matching quotation marks is recognised as a label rather than as the opening quote of its value. `forgel_code/interactive.py` gains `_label_quote_end`, which decides that a quote after a label closes the label when no value character touches it (a separator, whitespace, punctuation or end of message follows), and `_quoted_binding`, which takes the value bound to that quoted label through `=`/`:` separators or as an adjacent quoted run; `_binding` now consults both before falling back to the previous behaviour. Quoted labels therefore keep the label, both of its quotes, the separator and any repeated separators visible, while the value is replaced by the single `[redacted]` placeholder — inside the value's own quotes when the value is quoted, up to the next whitespace when it is not. `tests/test_redact.py` adds coverage for the single-quoted label with a single-quoted value, the double-quoted label with a double-quoted value, the JSON-style form (`{"token":"abc123"}`), an unquoted value after a quoted label, repeated separators, non-masking of neighbouring words and trailing punctuation, idempotence and exactly-one-placeholder for the quoted forms, absence of any value character, and a session-level reply carrying a quoted label. Full suite: `python -m pytest -q` -> 297 passed, 262 subtests passed.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact.py`

## Commands

- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pytest", "tests/test_redact.py", "-q"]` → exit 1
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "forgel_code/interactive.py"]` → exit 0
- `["git", "diff", "tests/test_redact.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
.............................................................................................. [ 31%]
........................................................................ [ 55%]
.......................................................................................... [ 86%]
.........................................                  [100%]
297 passed, 262 subtests passed in 183.97s (0:03:03)

```

## Actions

- read_file: forgel_code/render.py
- read_file: tests/test_redact.py
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- write_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', '-q']
- read_file: tests/test_redact.py
- read_file: tests/test_redact.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- write_file: forgel_code/interactive.py
- recall
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_redact.py
- read_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', 'tests/test_redact.py', '-q']
- write_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', '-q']
- read_file: .gitignore
- read_file: forgel_code/interactive.py
- write_file: None
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', 'forgel_code/interactive.py']
- run: ['git', 'diff', 'tests/test_redact.py']
