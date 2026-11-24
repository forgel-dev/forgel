# Agent Run: Release audit: In `_quoted_binding`, after a quoted label and whitespace, a bare next token ret

- Task: `20261124053445_release-audit-in-quoted-binding-after-a-`
- Status: `done`
- Repository: `code`
- Steps: 37
- Finished: 2026-11-24T05:53:56+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- A bare value after a quoted label ends at the same boundary as a bare value after an unquoted label: whitespace, with trailing clause punctuation left visible.
- A token after a quoted label that carries value markers (digit, mixed case or value punctuation) is treated as the value even when a word follows it, mirroring the unquoted-label rule.
- A quoted word followed by an ordinary word that continues the sentence is not a binding, so ordinary prose about a quoted label stays readable.
- The masking placeholder stays `[redacted]` and quotation marks around a quoted value stay visible, unchanged from today.
- No CHANGELOG entry was added: the specification lists producing or updating user documentation about masking as out of scope.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 37
- Estimated input tokens (all calls): 1384865
- Provider input/output tokens: 1418949 / 100461
- Provider cache hit/miss tokens: 1305856 / 113093
- Estimated prompt at the end: 41872 tokens
- State: `docs/program/agent/20261124053445_release-audit-in-quoted-binding-after-a-.state.md`

## Specification (`docs/program/specs/20261124053445_release-audit-in-quoted-binding-after-a-.md`)

# Task Spec: Release audit: In `_quoted_binding`, after a quoted label and whitespace, a bare next token ret

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: In `_quoted_binding`, after a quoted label and whitespace, a bare next token ret |
| Project | — |
| Task | `20261124053445_release-audit-in-quoted-binding-after-a-` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T05:35:14+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

Credential masking of quoted labels is incomplete: when a label appears in single or double quotes and the value follows after whitespace as a bare token, with no separator and no second quote, the value is not recognised as a credential binding and stays visible. A quoted label followed by an unquoted value therefore leaks the secret into what the user sees.

**Outcome:** Every credential whose label is quoted and whose value follows after whitespace as a bare token is masked in the output shown to the user, matching the masking already applied when an unquoted label is followed by a bare value. All other masking outcomes and all other output remain exactly as they are today, and the existing test suite passes.

## Product Intent

Forgel Code is a thin UI over the engine's parameterized commands and shows their output to the user. Anything the client presents must not expose credentials, whatever shape the label takes. Quoted labels are a common shape, and the quoted-label part of the masking guarantee is only half met while a bare value after a quoted label escapes masking.

## User Experience

A user running a command whose output contains a quoted credential label followed by an unquoted value sees the value masked rather than the real secret, so the console never displays the credential.

## Roadmap

—

## Goals

- Quoted labels followed by a bare unquoted value are masked in the output shown to the user.
- Every previously masked credential form remains masked.
- Unrelated output stays unmasked and readable.
- The existing test suite passes without weakening any test.

## Non-Goals

- Redesigning masking for forms that already work.
- Masking arbitrary prose or single quoted words that are not label-value bindings.
- Changing how the client obtains, formats or displays engine output beyond the masked value.
- Producing or updating user documentation about masking as part of this change.
- Altering existing tests to make the change pass.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, user decision log, 2026-11-16 18:31 |

## Functional Requirements

- **FR-1**: After a quoted label, whitespace and a bare unquoted value, the binding is treated as a credential binding and the value is masked in the output shown to the user.
- **FR-2**: Single-quoted labels and double-quoted labels are treated identically in that detection.
- **FR-3**: A quoted label followed by a separator and a value is still masked.
- **FR-4**: A quoted label followed by a quoted value is still masked.
- **FR-5**: An unquoted label followed by a bare value is still masked.
- **FR-6**: A quoted word that is not followed by a value, such as a quoted word at the end of a line or one followed by punctuation, is not treated as a credential binding and is left unchanged.
- **FR-7**: Output that contains no credential binding is returned unchanged.
- **FR-8**: No existing automated test is weakened, removed or modified to obtain the result.
- **FR-9**: The full existing test suite passes.

## User Stories

- As a user reading command output in the console, I want a credential under a quoted label to be masked, so that the secret is never displayed.
- As a maintainer, I want the correction to close the quoted-label gap without loosening the rule, so that unrelated output stays readable.

## Acceptance Criteria

- **AC-1**: A line made of a single-quoted label, whitespace and a bare value has the value masked in the produced output.
- **AC-2**: A line made of a double-quoted label, whitespace and a bare value has the value masked in the produced output.
- **AC-3**: A quoted label followed by a separator and a value is still masked.
- **AC-4**: A quoted label followed by a quoted value is still masked.
- **AC-5**: An unquoted label followed by a bare value is still masked.
- **AC-6**: A quoted word with no value after it is not masked.
- **AC-7**: Output without any credential binding is unchanged.
- **AC-8**: The full existing test suite passes.
- **AC-9**: No existing test was weakened, removed or modified to obtain the pass.

## Scope Boundaries

- Treat a quoted label followed by whitespace and then a bare, unquoted value as a credential binding.
- Mask the value in that binding in the output presented to the user.
- Support single-quoted and double-quoted labels equally.
- Preserve every previously masked form: a quoted label followed by a separator and a value, a quoted label followed by a quoted value, and an unquoted label followed by a bare value.
- Preserve output that contains no credential binding.
- Redesigning masking for forms that already work.
- Masking arbitrary prose or single quoted words that are not label-value bindings.
- Changing how the client obtains, formats or displays engine output beyond the masked value.
- Producing or updating user documentation about masking as part of this change.
- Altering existing tests to make the change pass.

## Risks

- Broadening the quoted-label rule too far would mask ordinary quoted words followed by a word and change unrelated output; the acceptance criterion for a quoted word with no value only partially guards against this.
- Changing the visible placeholder or surrounding formatting would break expectations elsewhere in the suite.
- The user-facing documentation of masking may not be updated by this task, so the documented behaviour could lag the fixed behaviour; that divergence is out of scope here and belongs to a documentation task.
- The audit finding names an internal detection point, while this specification states observable behaviour; the developer must ensure the chosen change covers both quote styles and not just one surfaced case.

## Open Questions

- None.

## Assumptions

- Credential masking is applied to the output the client presents to the user, so this is a correction of a partially met existing guarantee rather than a new feature.
- The bare value ends at whitespace, mirroring how a bare value after an unquoted label is bounded today.
- A quoted label with nothing after it, or followed only by punctuation, is not a binding, mirroring the existing behaviour for unquoted labels.
- The visible placeholder shown in place of a masked value stays the same as it is today.
- Prose that happens to contain a quoted word followed by an ordinary word is not a credential context unless the quoted word is a label; the change must keep such text readable.

## Related Documents

- FORGEL.md
- AGENTS.md
- CHANGELOG.md

## Revision History

- 1.0 — initial specification for the release audit finding on quoted-label masking.
- 1.1 — removed implementation detail from the constraints and kept requirements and acceptance limited to observable behaviour.
- 1.2 — removed the remaining process wording from the constraints so the document states functional requirements only.


## Summary

Closed the quoted-label gap in credential masking in `forgel_code/interactive.py`. `_quoted_binding` previously bound a value to a quoted label only through a separator (`'token': abc`) or a quoted run (`'token' 'abc'`) and returned None for anything else, so a quoted label followed by whitespace and a bare unquoted value (`'token' abc123`, `"password" hunter2`) left the secret visible. It now inspects the token after the closing quote: an authorization-scheme word still routes to `_scheme_value` (scheme visible, credential masked), a copula routes to `_copula_span` (`the 'token' is VALUE`), a prose/narrative word still means the label is only mentioned, and any other token is masked when it carries value markers or closes the clause. Clause closing is decided by a new helper `_closes_clause`, together with two new constants `_INLINE_WHITESPACE` and `_CLAUSE_END`, so a bare value at the end of the line or in front of punctuation is masked while a quoted word followed only by punctuation, or by a word that continues the sentence, stays unchanged. Single-quoted and double-quoted labels travel the same code path, so both behave identically, and the previously working forms (separator, quoted value, unquoted label with a bare value, unchanged secret-free output) keep their behaviour and their visible placeholder. No existing test was touched; new coverage lives in `tests/test_redact_quoted_bare.py` (10 tests, 37 subtests) covering single- and double-quoted bare values, clause-ending values, the preserved separator/quoted-value/unquoted-label forms, quoted words without a value, secret-free text, and idempotence with exactly one marker. The full suite passes: `python -m pytest -q` -> 334 passed, 363 subtests passed.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact_quoted_bare.py`

## Commands

- `["git", "status", "--porcelain"]` → exit 0
- `["git", "show", "HEAD:forgel_code/interactive.py"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--stat", "HEAD"]` → exit 0
- `["git", "diff", "HEAD", "--", "forgel_code/interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_redact_quoted_bare.py"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
.............................................................................................. [ 28%]
........................................................................ [ 49%]
.......................................................................................... [ 76%]
..............................................................................                        [100%]
334 passed, 363 subtests passed in 187.96s (0:03:07)

```

## Actions

- read_file: forgel_code/render.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/cli.py
- read_file: tests/test_redact.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_redact_descriptor.py
- read_file: tests/test_retained_text.py
- read_file: CHANGELOG.md
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'status', '--porcelain']
- run: ['git', 'checkout', '--', 'forgel_code/interactive.py']
- recall
- run: ['git', 'show', 'HEAD:forgel_code/interactive.py']
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'diff', '--stat', 'HEAD']
- run: ['git', 'diff', 'HEAD', '--', 'forgel_code/interactive.py']
- run: ['python', '-m', 'pytest', '-q']
- read_file: tests/test_redact.py
- read_file: tests/test_redact.py
- recall
- write_file: tests/test_redact_quoted_bare.py
- write_file: tests/test_redact_quoted_bare.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact_quoted_bare.py']
- run: ['git', 'status', '--porcelain']
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'add', 'forgel_code/interactive.py', 'tests/test_redact_quoted_bare.py']
