# Agent Run: Release audit: Redaction misses values separated from a secret label by a newline and values be

- Task: `20261124003849_release-audit-redaction-misses-values-se`
- Status: `done`
- Repository: `code`
- Steps: 16
- Finished: 2026-11-24T04:21:24+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- A run of any whitespace that contains a line break (or only spacing) separates a label from its value, mirroring the existing space-and-tab rule; carriage returns are included so CRLF text is masked.
- Punctuation directly before a value after an explicit ':'/'=' separator is treated as part of the value and replaced together with it, while enclosing quotation characters keep their visible rendering; trailing clause punctuation after the value stays visible as before.
- A bracketed run after an explicit separator is hidden whole, brackets included, on the value's own line; a '[' that opens no such run keeps its previous treatment.
- The existing mention, prose-word, copula and authorization-scheme rules keep precedence over the widened gap rule, so ordinary prose across a line break is not masked.
- No documentation or changelog update was made, following the task's non-goals.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 16
- Estimated input tokens (all calls): 557943
- Provider input/output tokens: 575127 / 111321
- Provider cache hit/miss tokens: 518784 / 56343
- Estimated prompt at the end: 58113 tokens
- State: not needed

## Specification (`docs/program/specs/20261124003849_release-audit-redaction-misses-values-se.md`)

# Task Spec: Release audit: Redaction misses values separated from a secret label by a newline and values be

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: Redaction misses values separated from a secret label by a newline and values be |
| Project | — |
| Task | `20261124003849_release-audit-redaction-misses-values-se` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T04:01:03+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client masks a value that follows a secret label only when the label and the value are joined by a space, a tab, a colon or an equals sign and the value looks like an ordinary word. Two ordinary ways of writing a secret therefore reach the screen unchanged: a label whose value sits on the next line, and a value that begins with punctuation after an explicit colon or equals sign. The reported audit finding names exactly this gap, and a credential written that way is displayed in the session.

**Outcome:** A secret label and its value are masked whatever whitespace separates them, including a line break, and whatever punctuation the value starts with after an explicit separator. Every masked value is replaced by exactly one marker, the label, the separators and the line structure stay visible, and every text that carried no value stays exactly as written.

## Product Intent

The client is a thin UI over the engine's machine-readable commands and must never display key material on the owner's screen, whichever way the engine's answer happens to spell it.

## User Experience

The owner reads an engine answer, a task title or an error message and sees the label, the separators and the line breaks as written, with a single marker in place of the secret. A credential written on the line after its label, or prefixed with punctuation, no longer appears.

## Roadmap

—

## Goals

- Close the reported finding that a credential separated from its label by a line break or beginning with punctuation is displayed.
- Keep every separator, wrapper and line break visible while exactly one marker stands for each masked value.
- Leave all text that carries no secret value untouched.
- Keep the existing masking behaviour and the whole existing expectation suite green.

## Non-Goals

- Changing which words count as a secret label or which schemes stay visible
- Changing how the client talks to the engine, what it asks for or how it shows an answer
- Masking text that carries no value for a secret label
- Adding user-facing configuration, options or messages about masking
- Documentation and release notes

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | D-002, user 2026-11-16 18:31 |
| — | The single free-text engine entry point is the engine's say command; every client-facing operation is a parameterized command with an optional single JSON object on stdout. | D-007, user accepted the proposal 2026-11-16 18:34 |
| — | A respec issue is binding: the rewritten requirements remove the rejected option, decide the remaining details and stay consistent with the acceptance. | D-107, project rules |

## Functional Requirements

- **FR-1**: When a secret label is separated from its value by whitespace that contains a line break instead of, or in addition to, spaces and tabs, the value is masked and the label, the separator and the line break stay visible.
- **FR-2**: The line-break rule applies whether the label and the value reach the owner as one block of text or are displayed on separate lines.
- **FR-3**: After an explicit colon or equals separator, a value that begins with punctuation is masked: the label, the separator and the space before the value stay visible and exactly one marker takes the place of the punctuation and the value.
- **FR-4**: A bracketed value after an explicit colon or equals separator is masked so that no character of the value remains visible and exactly one marker appears.
- **FR-5**: Quotation characters that enclose a value keep the behaviour they already have: the quotation characters stay visible and the marker stands between them.
- **FR-6**: Repeated separator characters stay visible and only the value is replaced.
- **FR-7**: Each masked value carries exactly one marker, and masking an already masked text changes nothing.
- **FR-8**: No character of a masked value appears anywhere in the text the client shows, for every form this task adds and every form it already handled.
- **FR-9**: A mention of a secret label that carries no value, on one line or followed by a line break, stays exactly as written.
- **FR-10**: Text without a secret value stays exactly as written, character for character, including its line breaks.
- **FR-11**: Every masking form the client already handles keeps its current rendering.

## User Stories

- As the owner of a project, I want a credential written on the line after its label or starting with punctuation to be masked, so that the session screen never shows key material.
- As the owner, I want the label, the separators and the line breaks to stay readable, so that I can still tell what the engine said without reading the secret.
- As a reviewer, I want the gap closed for every label, separator and punctuation character, so that the same finding cannot come back with another example.

## Acceptance Criteria

- **AC-1**: A label, an explicit colon and a line break followed by a value on the next line are shown as the label, the colon, the same line break and one marker, and no character of the value is visible.
- **AC-2**: A label, a line break and a value on the next line without any separator are shown as the label, the same line break and one marker, and no character of the value is visible.
- **AC-3**: A text in which only one line carries the value keeps its line count and every other line character for character, while the value line shows one marker in place of the value.
- **AC-4**: A value introduced by an exclamation mark after an explicit colon or equals separator loses the exclamation mark and the value and gains exactly one marker; no character of the value is visible.
- **AC-5**: A value enclosed in square brackets after an explicit colon or equals separator loses the brackets and the value and gains exactly one marker; no character of the value is visible.
- **AC-6**: A quoted value after a label renders exactly as it renders today, with the quotation characters visible and one marker between them.
- **AC-7**: An authorization scheme word before a credential stays visible and the credential is replaced by one marker, as today.
- **AC-8**: A label that carries no value is unchanged, both on a single line and when a line break follows the label.
- **AC-9**: Secret-free text, including text with punctuation, line breaks and several lines, is returned unchanged.
- **AC-10**: For every form this task adds, masking twice gives the same text as masking once and the text contains exactly one marker per masked value.
- **AC-11**: The whole existing expectation suite passes.
- **AC-12**: The finding is resolved for any secret label, any explicit separator and any punctuation, not only for the examples named in the audit finding.

## Scope Boundaries

- Masking a value that a secret label is separated from by a line break instead of a space or a tab
- Masking a value that begins with punctuation after an explicit colon or equals separator, including a prefixed form and a bracketed form
- Keeping the label, every separator character and the line structure visible while exactly one marker stands for each masked value
- Keeping a mention of a label without a value and all secret-free text unchanged, including across line breaks
- Preserving the masking the client already performs for space-, colon-, equals-, quoted- and JSON-style forms
- Regression coverage of the new and the preserved masking forms in the existing expectation suite
- Changing which words count as a secret label or which schemes stay visible
- Changing how the client talks to the engine, what it asks for or how it shows an answer
- Masking text that carries no value for a secret label
- Adding user-facing configuration, options or messages about masking
- Documentation and release notes

## Risks

- Widening the separation rule to line breaks can mask ordinary prose in which a label ends a line, for example a sentence that continues on the next line; the existing mention and function-word exceptions must keep such text unchanged or the current expectations fail.
- The masked-value marker itself begins with punctuation, so a punctuation-tolerant rule can re-mask its own output and break idempotence or produce two markers.
- Treating punctuation as part of the value can disturb the rendering of quoted and bracketed forms that current expectations pin down.
- The examples named in the audit finding are not the whole space; a rule tuned to exactly those strings leaves the same finding open for another separator, label or punctuation character and the audit can report it again.
- Masking a value that sits on the next line must hold when the owner sees the text as several lines, not only when it arrives as one block.
- A change that also relaxes which words count as a secret label would mask harmless text and break the unchanged-text expectations.

## Open Questions

- None.

## Assumptions

- Punctuation that directly precedes a value after an explicit separator is treated as part of the value and masked with it, while quotation characters that enclose a value keep their current visible-enclosing rendering; this keeps the reported forms masked without changing existing expectations.
- A run of whitespace between a label and its value counts as a separator when it contains at least one line break, mirroring the rule already applied to spaces and tabs.
- The rules that already keep a label mention, a following function word or a following authorization scheme visible continue to win over the new rules, so ordinary prose across a line break is not masked.
- No new external requirement is introduced.
- No changelog or documentation update is required for this fix.

## Related Documents

- FORGEL.md
- AGENTS.md
- CHANGELOG.md
- README.md

## Revision History

- 1: Initial specification of the audit finding on newline-separated and punctuation-prefixed secret values.
- 2: Removed a project-convention constraint and restated process wording as observable masking behaviour.


## Summary

Widened the client-side masking in forgel_code/interactive.py so that a secret value is hidden however it is separated from its label. The gap was two-fold: the separator gap only accepted spaces and tabs, and the value after an explicit ':' or '=' separator could only be a word-like run, so a value on the next line or a value introduced by punctuation reached the screen.

Changes:
- The gap between a label and its value (and between a value and an authorization scheme word) is now skipped with a single whitespace predicate that includes line breaks and the other whitespace characters, so `password:\nhunter2`, `password\nhunter2`, `token =\r\nabc123` and `Authorization:\nBearer abc123` are masked while every separator character and the line break stay visible.
- After an explicit ':'/'=' separator a separate value-span helper is used: quotation marks keep their current enclosing rendering, a word-like value keeps the existing rendering, and any other punctuation that introduces a value is treated as part of the value, so `password: !hunter2` becomes `password: [redacted]` and a bracketed run `password: [hunter2]` is hidden whole with one marker.
- Repeated separators, prose/mention/copula/authorization-scheme exceptions and the masker's own marker stay untouched, so existing renderings and idempotence are preserved.

Tests: extended tests/test_redact.py with a new `LineBreakAndPunctuationFormTest` class (line-break separation with and without a separator, CRLF and mixed whitespace, line count and other lines unchanged, punctuation-prefixed values across labels, bracketed values, valueless labels, secret-free multiline text, idempotence and one marker per masked value) plus a screen test that a multiline engine reply with a value on the next line and a punctuation-prefixed value shows no secret characters. The full suite passes: `python -m pytest -q` → 308 passed, 293 subtests passed.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact.py`

## Commands

- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_redact.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
.............................................................................................. [ 30%]
........................................................................ [ 53%]
.......................................................................................... [ 83%]
....................................................                                                [100%]
308 passed, 293 subtests passed in 194.54s (0:03:14)

```

## Actions

- read_file: forgel_code/render.py
- read_file: tests/test_redact.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: pyproject.toml
- read_file: tests/test_interactive.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- write_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py']
- run: ['python', '-m', 'pytest', '-q']
