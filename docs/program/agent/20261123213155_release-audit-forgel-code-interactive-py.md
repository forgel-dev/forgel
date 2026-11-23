# Agent Run: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Status: `done`
- Repository: `code`
- Steps: 40
- Finished: 2026-11-23T22:22:42+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The fixed mask marker stays the existing `[redacted]` placeholder.
- Russian labels are matched by stem (парол, секрет, токен, ключ) so inflected forms are recognized.
- The label segment separators for compound labels are underscore, dot and hyphen, as stated in the specification's scope.
- A scheme word after a whitespace joiner binds a credential only when the following token is not an ordinary prose word (so "bearer of good news" stays untouched).

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 40
- Estimated input tokens (all calls): 1968224
- Provider input/output tokens: 2029889 / 291655
- Provider cache hit/miss tokens: 1856768 / 173121
- Estimated prompt at the end: 84812 tokens
- State: `docs/program/agent/20261123213155_release-audit-forgel-code-interactive-py.state.md`

## Specification (`docs/program/specs/20261123213155_release-audit-forgel-code-interactive-py.md`)

# Task Spec: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the |
| Project | — |
| Task | `20261123213155_release-audit-forgel-code-interactive-py` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T21:32:29+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

Secrets present in engine replies and engine errors reach the screen because the session's text masking only recognizes a limited English keyword immediately followed by an equals sign or a single following whitespace-separated word. A secret introduced by a colon, by an authorization scheme word, by a non-English label, or by a compound label name passes through unmasked, so sensitive key material becomes visible in the interactive session and the guarantee that secret key material stays out of the session is broken.

**Outcome:** Every engine reply and every engine error displayed in the session is masked before display, so a value bound to a secret-bearing label never appears in the visible session text — regardless of whether the label and value are joined by a colon, an equals sign or whitespace, whether an authorization scheme word sits between them, whether the label is English or Russian, or whether the label is a compound name containing a secret keyword as one of its segments. Ordinary prose and the rest of the message are left intact, labels stay readable next to the mask, and previously working session behavior does not regress.

## Product Intent

Forgel Code is a thin, trustworthy console over the engine (D-002, D-004); a user must be able to read engine output on screen without the session leaking credentials the engine happened to echo.

## User Experience

When the engine's answer or an engine error mentions a credential, the user sees the label followed by a fixed mask marker instead of the value; when the message contains no credential, the user sees it exactly as before, with phrasing, punctuation and spacing unchanged.

## Roadmap

—

## Goals

- The reported leak is closed for colon-joined, equals-joined, whitespace-joined, scheme-prefixed, non-English and compound-label secret forms.
- The guarantee that no secret key material appears in the interactive session is restored for all engine replies and engine errors.
- Benign messages are displayed unchanged.
- Previously working session behavior does not regress.

## Non-Goals

- Detecting secrets that carry no label at all, such as an unaccompanied high-entropy string or a bare key-looking blob.
- Hiding secrets anywhere other than what the session shows to the user.
- Changing the wording of engine replies or engine errors, or stopping the engine from echoing secrets at its source.
- Any change to the client's commands, prompts, layout or interaction model.
- Vendor-specific recognition of particular credential formats beyond generic label, joining punctuation and scheme handling.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; model access, the sandbox, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code, a Python client, following a Pareto 20/80 scope. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | Work proceeds in order: machine-readable engine commands first, then the client and the console, then removal of the replaced chat mode from the engine. | D-006, User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: Masking means: for a recognized secret-bearing label, the value bound to that label is replaced by a single fixed mask marker while the label is preserved, so the original value does not appear anywhere in the displayed text.
- **FR-2**: A value following a recognized secret keyword and a colon, with or without intervening whitespace, is masked.
- **FR-3**: A value following a recognized secret keyword and an equals sign, with or without surrounding whitespace, is masked.
- **FR-4**: A value following a recognized secret keyword and whitespace (the previously supported single-token form) continues to be masked.
- **FR-5**: A value that follows a recognized secret keyword plus a colon or whitespace and then an authorization scheme word is masked; the scheme word may remain visible, the credential after it may not.
- **FR-6**: Secret keywords are recognized in English and in Russian; a Russian secret label followed by a colon, an equals sign or whitespace masks its value exactly as an English label does.
- **FR-7**: A compound label containing a secret keyword as one of its segments is treated as a secret-bearing label; the whole label may remain visible but its bound value is masked.
- **FR-8**: Label recognition is case-insensitive, including for non-English labels.
- **FR-9**: Text not bound to a recognized secret-bearing label is displayed unchanged, including ordinary sentences that merely contain the word for a secret without a bound value.
- **FR-10**: The label text itself is preserved next to the mask so the user can tell what kind of value was hidden.
- **FR-11**: Masking is applied to every engine reply and every engine error before it is shown in the session, with no path by which engine output reaches the screen unmasked.
- **FR-12**: Masking already-masked text neither errors nor reveals a value, and masking empty or secret-free text returns it unchanged.
- **FR-13**: Previously working session behavior continues to work, including the masking forms that already worked.

## User Stories

- As a developer watching Forgel Code work, I want credentials echoed by the engine to be masked before they reach my screen, so that a pasted secret does not end up visible in my terminal or my session history.
- As a developer whose labels and messages are not always in English, I want secret labels in my own language to be recognized, so that the protection does not depend on the language of the output.
- As a developer reading engine errors, I want the label to stay visible next to the mask, so that I can tell what kind of value was hidden without learning the value.

## Acceptance Criteria

- **AC-1**: A message containing a secret label followed directly by a colon and a value is displayed with the value replaced by the mask marker and the value absent from the displayed text.
- **AC-2**: A message containing a secret label, a colon, an authorization scheme word and a credential is displayed with the label and surrounding wording preserved and the credential replaced by the mask marker.
- **AC-3**: A message containing a Russian secret label followed by a colon and a value is displayed with the value replaced by the mask marker.
- **AC-4**: A message containing a compound label built from several segments, one of which is a secret keyword, joined to a value is displayed with the value replaced by the mask marker.
- **AC-5**: A message containing a secret label joined to a value by an equals sign with no surrounding spaces is displayed with the value replaced by the mask marker.
- **AC-6**: A message that merely mentions a secret word without binding a value to it is displayed unchanged.
- **AC-7**: A message with no secret-bearing label is displayed byte-for-byte unchanged, including punctuation, spacing and wording.
- **AC-8**: Masking the same message twice produces the same displayed result as masking it once, and masking empty text succeeds and yields empty text.
- **AC-9**: Every engine reply and every engine error that reaches the session display is masked under these rules, with no displayed engine text bypassing masking.
- **AC-10**: For each recognized form above, the secret value does not appear as a substring anywhere in what the user is shown for that message.
- **AC-11**: Previously working session behavior does not regress.

## Scope Boundaries

- Recognition of secret-bearing labels joined to a value by a colon, an equals sign, or whitespace.
- Recognition of a credential that follows an authorization scheme word placed after a secret-bearing label.
- Recognition of secret keywords in languages other than English, at minimum English and Russian.
- Recognition of compound labels in which a secret keyword appears as one of several label segments, segments being separated by underscores, dots or hyphens.
- Masking applied to every engine reply and every engine error presented in the session, before the text becomes visible.
- Replacing only the secret value while the surrounding label and the remaining message stay readable.
- Idempotent and total behavior: masking the same text twice, masking empty text, and masking text with no secret all succeed without error.
- Detecting secrets that carry no label at all, such as an unaccompanied high-entropy string or a bare key-looking blob.
- Hiding secrets anywhere other than what the session shows to the user.
- Changing the wording of engine replies or engine errors, or stopping the engine from echoing secrets at its source.
- Any change to the client's commands, prompts, layout or interaction model.
- Vendor-specific recognition of particular credential formats beyond generic label, joining punctuation and scheme handling.

## Risks

- Over-broad matching removes ordinary words from benign messages, degrading readability and breaking expected unchanged output.
- Under-broad matching leaves one of the reported forms leaking, so the finding is not actually resolved even though some new behavior passes.
- Masking applied after some engine output has already become visible leaves a bypass; the guarantee holds only if masking truly precedes display on every path.
- Unicode case-insensitivity may differ from ASCII handling, so a naive ASCII-only case-insensitive match could miss upper-case Russian labels.
- A value containing several space-separated tokens may be only partially masked if a single token is consumed.
- A message that merely mentions a secret word inside a sentence can look covered while a genuine bound value still leaks, giving false confidence in the coverage.
- The mask marker appearing inside an already-masked message could itself be re-matched, producing a different result on a second pass.

## Open Questions

- None.

## Assumptions

- The fixed mask marker is a short visible placeholder, a run of asterisks for example, chosen by the developer and used consistently; its exact characters are not a product decision.
- The authorization scheme word is not itself secret and may remain visible with its label.
- For compound labels the whole label may remain visible; only the bound value is hidden.
- Russian is the non-English language that must be supported because it is the language of the project's chat interaction; further languages are welcome but not required.
- Underscore, dot and hyphen all count as label segment separators.
- Hiding secrets that have already left the visible session is out of scope for this task.
- Where a label is followed by an authorization scheme word, only the credential after the scheme word is hidden, not the scheme word.

## Related Documents

- `docs/program/decisions.md`

## Revision History

- v2 — rewrote non-goals and assumptions in behavior terms, removed process and implementation detail, aligned requirements and acceptance, and mapped each acceptance criterion to a check.
- v1 — initial specification from the release audit finding: masking must cover colon-joined, equals-joined, whitespace-joined, scheme-prefixed, non-English and compound-label secret forms in every displayed engine reply and error.


## Summary

Rewrote `redact()` in `forgel_code/interactive.py` so every engine reply and engine error is masked before display. Secret-bearing labels are now recognized case-insensitively in English and Russian (Russian by stem), as single words or compound labels whose segments are joined by `_`, `.` or `-`, and a value bound to such a label by a colon, an equals sign (with or without spaces) or whitespace is replaced with the fixed marker `[redacted]` while the label stays visible. Whitespace/colon-bound authorization scheme words (e.g. `Bearer`) stay visible with only the credential after them masked. Prose that merely mentions a secret word ("the token is missing", "rotate the password please") is left intact, and secret-free text is returned unchanged and byte-for-byte; masking is idempotent and total for empty input. The mask already had a single funnel through `InteractiveSession.write()`, so every reply, error and state line continues to pass through it. The implementation no longer imports `re` (the client's stdlib allowlist forbids it), doing label scanning by hand instead. Added `tests/test_redact.py`, which checks each required form (colon, equals, whitespace, scheme-prefixed, Russian, compound labels), unchanged benign text, idempotency, and end-to-end that engine replies, engine state lines and engine errors reach the session screen with the value absent. Full suite `python -m pytest -q` passes: 267 passed, 172 subtests.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact.py`

## Commands

- `["python", "-m", "pytest", "-q"]` → exit 124
- `["python", "-m", "pytest", "-q", "tests/test_interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_install.py", "tests/test_install_timeout_verdict.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_redact.py", "tests/test_interactive.py"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_redact.py", "tests/test_interactive.py"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_redact.py", "tests/test_interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_redact.py", "tests/test_interactive.py", "tests/test_cli.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 1
- `["python", "-m", "pytest", "-q", "tests/test_install.py::InstallerBoundedCheckTest::test_shell_that_ignores_the_stop_is_still_bounded", "tests/test_install_timeout_verdict.py::TimeoutVerdictOrderingTest::test_step_inside_the_bound_keeps_its_own_nonzero_outcome"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
............................................................................................... [ 35%]
........................................................................ [ 62%]
.............................................................. [ 85%]
......................................                                                                  [100%]
267 passed, 172 subtests passed in 204.73s (0:03:24)

```

## Actions

- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/session.py
- read_file: forgel_code/render.py
- read_file: forgel_code/engine.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_interactive.py']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', 'tests/test_install_timeout_verdict.py']
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/engine.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/session.py
- read_file: tests/test_interactive.py
- write_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py', 'tests/test_interactive.py']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py', 'tests/test_interactive.py']
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py', 'tests/test_interactive.py']
- run: ['python', '-m', 'pytest', '-q']
- read_file: tests/test_cli.py
- write_file: forgel_code/interactive.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py', 'tests/test_interactive.py', 'tests/test_cli.py']
- run: ['python', '-m', 'pytest', '-q']
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py::InstallerBoundedCheckTest::test_shell_that_ignores_the_stop_is_still_bounded', 'tests/test_install_timeout_verdict.py::TimeoutVerdictOrderingTest::test_step_inside_the_bound_keeps_its_own_nonzero_outcome']
- run: ['python', '-m', 'pytest', '-q']
