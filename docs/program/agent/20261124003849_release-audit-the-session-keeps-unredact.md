# Agent Run: Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw

- Task: `20261124003849_release-audit-the-session-keeps-unredact`
- Status: `done`
- Repository: `code`
- Steps: 40
- Finished: 2026-11-24T04:44:41+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The two engine-derived texts the client keeps for the session are the last state text and the last idle-refresh failure text, as named in the audit finding; no other engine text is retained, so only these two sites needed masking.
- The existing `redact` routine is reused unchanged; masking rules, the mask marker and the secret label set stay as they are.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 40
- Estimated input tokens (all calls): 1695265
- Provider input/output tokens: 1739632 / 126169
- Provider cache hit/miss tokens: 1628160 / 111472
- Estimated prompt at the end: 44087 tokens
- State: `docs/program/agent/20261124003849_release-audit-the-session-keeps-unredact.state.md`

## Specification (`docs/program/specs/20261124003849_release-audit-the-session-keeps-unredact.md`)

# Task Spec: Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw |
| Project | — |
| Task | `20261124003849_release-audit-the-session-keeps-unredact` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T04:30:10+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The client keeps engine-produced text in memory verbatim. When a state display is assembled, the joined text is retained as the session's last state without masking, and when an idle refresh fails, the engine's error message is retained as the session's last idle failure without masking. If the engine answer or the error text carries key material, the readable secret stays in the client for the rest of the session, even though the screen would have shown it masked. This breaks the requirement that secrets never appear in anything the client keeps, and the release audit flagged it.

**Outcome:** No engine-produced text retained by the client for the session carries a readable secret. Every copy of an engine answer or engine error message that the client holds in memory has already been masked, so showing or re-showing that retained text later reveals only the mask, while secret-free text is retained and shown exactly as before.

## Product Intent

Forgel Code is a thin console over the engine's parameterized commands: it shows what the engine reports and must never become a place where key material accumulates. The requirement that secrets never appear in anything the client keeps applies to the screen and to the client's in-memory session state alike.

## User Experience

The user sees the same messages as before, with secrets shown as a mask. If the engine reports an error or a state that mentions key material, the user sees the mask on that message and on any later repeat of it, and nothing readable is kept behind the scenes for the rest of the session.

## Roadmap

—

## Goals

- Remove readable key material from every engine-derived text the client keeps in memory for the session.
- Keep user-visible behavior for secret-free text unchanged.
- Keep the existing test suite green.

## Non-Goals

- Changing the masking rules, the mask marker or the set of labels treated as secret
- Changing what the client asks the engine for or how it parses the answer
- Persisting session state to disk or adding a new stored artifact
- Auditing or masking text the client never receives from the engine
- Moving model access, sandboxing or release approval anywhere near the client

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; model access, the sandbox, independent QA, review and release approval stay in the engine. | User decision log D-002, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code; it is a Python client installed as forgel-code, follows a Pareto 20/80 scope and imports nothing from the engine. | User decision log D-004, 2026-11-16 18:34 |
| — | Every client-facing operation is a parameterized engine command with an optional single JSON object on stdout; the active project is an engine-side session with the default key local. | User decision log D-007, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: Any text produced by the engine that the client keeps in memory for the session is masked before it is kept, so the in-memory copy never contains a value the client would mask on screen.
- **FR-2**: The retained state text shown by the state display is the masked text; repeating the display later does not reveal the secret.
- **FR-3**: The retained idle-refresh failure text is masked before retention, and any later display of that failure shows only the mask.
- **FR-4**: Masking applies equally to engine answers and engine error messages.
- **FR-5**: Text that carries no key material is retained and shown unchanged, apart from the masking applied today.
- **FR-6**: Masking an already-masked retained text leaves it unchanged: no second marker appears and no content is lost.
- **FR-7**: What the user sees on a later repeat of retained text equals what the client retained; there is no path where the retained copy is more revealing than the display.
- **FR-8**: No other client behavior changes, and the existing test suite passes.

## User Stories

- As a user reading the console, I want secrets in engine answers and errors to appear only as a mask, so that a shared screen or a scrolling log never exposes them.
- As a user who repeats a state or failure display later in the session, I want the repeat to show the same masked text, so that the earlier masking is not undone.
- As a maintainer, I want the client to hold no readable key material, so that the release audit finding is closed rather than reworded.

## Acceptance Criteria

- **AC-1**: When the engine returns an answer whose text contains key material, nothing the client retains for the session contains that value in readable form; the user sees only the mask.
- **AC-2**: When the engine fails with an error message containing key material, the failure text the client retains and any later display of it contain only the mask.
- **AC-3**: An answer or error without key material is retained and shown exactly as before.
- **AC-4**: Masking retained text a second time yields the same text, with one marker per masked value.
- **AC-5**: Repeating a retained state or failure display later shows the same masked text that was retained.
- **AC-6**: All pre-existing tests pass.

## Scope Boundaries

- Masking engine-produced text before the client retains it in memory, for state display text and for idle-refresh failure text
- Keeping displayed text and retained text identical so a later repeat of retained text is masked as well
- Preserving current masking rules and current display behavior for text without key material
- Regression coverage for answers and error messages that contain key material
- Changing the masking rules, the mask marker or the set of labels treated as secret
- Changing what the client asks the engine for or how it parses the answer
- Persisting session state to disk or adding a new stored artifact
- Auditing or masking text the client never receives from the engine
- Moving model access, sandboxing or release approval anywhere near the client

## Risks

- Masking only the printed form while a raw copy remains in memory would leave the audit finding unresolved.
- A retained raw copy that is re-displayed later would leak even though the first display was masked; acceptance therefore covers the later repeat.
- Over-masking could hide legitimate content that happens to follow a secret label, which existing masking behavior tolerates but should not be widened.
- Another engine-derived text retained outside the two reported places could keep the finding alive; the outcome requires that no retained engine text is readable.
- Re-masking retained text on every repeat could stack markers if masking is not idempotent.

## Open Questions

- None.

## Assumptions

- The client already has a masking routine with the behavior covered by the existing masking tests, and this task reuses it rather than writing a new one.
- The two retained texts named in the audit finding are the state text and the idle-refresh failure text, and these are the only engine-derived texts kept for the session.
- The client displays masked text today, so the fix makes retention match display rather than introducing new user-visible masking.
- Masking is deterministic and idempotent, as the existing tests indicate.

## Related Documents

- releases/0.1.1/release.md
- releases/0.1.1/plan.md

## Revision History

- v1: initial specification for resolving the release audit finding on unredacted engine text retained in client memory


## Summary

The interactive session now masks engine-derived text before it is retained in memory. `show_state` builds the state text with `redact(...)` before comparing it to and storing it in `last_state`, and the forced refresh path in `refresh` stores `redact(...)` as well, so the retained state equals what the screen showed and a later repeat only shows the mask. `idle_refresh` masks the engine error message (`redact(exc.message)`) before keeping it in `idle_failure`; the once-per-message comparison uses the masked text, so an already-masked retained failure stays unchanged and the displayed text is the retained text. Secret-free text is unaffected because `redact` is idempotent and returns it unchanged. Added `tests/test_retained_text.py`, which drives real stub engine processes and asserts that retained state and retained idle failure contain no readable secret, that a repeat of the retained text shows the same masked text, that re-masking leaves it unchanged, and that secret-free state is retained and shown exactly as before. Full suite: `python -m pytest -q` -> 314 passed, 293 subtests passed.

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_retained_text.py`

## Commands

- `["git", "diff", "--stat", "forgel_code/interactive.py"]` → exit 0
- `["git", "diff", "forgel_code/interactive.py"]` → exit 0
- `["git", "diff", "forgel_code/interactive.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_retained_text.py"]` → exit 4
- `["python", "-m", "pytest", "-q", "tests/test_retained_text.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0

## Final Test Output

```
.............................................................................................. [ 29%]
........................................................................ [ 52%]
.......................................................................................... [ 81%]
................................................... [ 97%]
.......                                          [100%]
314 passed, 293 subtests passed in 208.58s (0:03:28)

```

## Actions

- read_file: forgel_code/session.py
- read_file: forgel_code/render.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_idle_refresh.py
- read_file: tests/test_redact.py
- read_file: forgel_code/engine.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- run: ['git', 'diff', '--stat', 'forgel_code/interactive.py']
- run: ['git', 'diff', 'forgel_code/interactive.py']
- write_file: forgel_code/interactive.py
- run: ['git', 'checkout', '--', 'forgel_code/interactive.py']
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['git', 'diff', 'forgel_code/interactive.py']
- recall
- run: ['python', '-m', 'pytest', '-q', 'tests/test_retained_text.py']
- list_files
- write_file: tests/test_retained_text.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_retained_text.py']
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'status', '--porcelain']
- run: ['git', 'commit', '-m', 'Mask engine text before the session retains it', '-m', 'The state display and the idle-refresh failure kept the raw engine text in memory for the session, so a later repeat of that copy would have shown key material the screen masked. Both retained texts are now masked before they are kept, which makes the retained copy exactly what the screen shows.']
