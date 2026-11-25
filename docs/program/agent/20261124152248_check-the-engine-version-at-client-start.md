# Agent Run: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Status: `failed`
- Repository: `code`
- Steps: 242
- Finished: 2026-11-25T15:20:08+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- none

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 242
- Estimated input tokens (all calls): 12278405
- Provider input/output tokens: 12738581 / 237050
- Provider cache hit/miss tokens: 12356219 / 382362
- Estimated prompt at the end: 17280 tokens
- State: not needed

## Specification (`docs/program/specs/20261124152248_check-the-engine-version-at-client-start.md`)

# Task Spec: Check the engine version at client startup

## Document Information

| Field | Value |
|-------|-------|
| Feature | Check the engine version at client startup |
| Project | — |
| Task | `20261124152248_check-the-engine-version-at-client-start` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-25T05:21:32+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

Forgel Code declares no minimum supported engine version and does not confirm the engine before using it, so a user with no engine, or with an engine too old for the client, gets a low-level operating-system error text or a confusing failure later in the operation instead of a message that says what to install or upgrade.

**Outcome:** Forgel Code owns one declared minimum supported engine version and confirms the engine before its first use in an invocation. A missing engine produces one actionable message naming the engine and carrying a pasteable install instruction; an engine below the minimum, or an engine whose version cannot be confirmed from its own answer, produces one actionable message naming the required minimum, the version found and a pasteable upgrade instruction; a compatible engine is used exactly as before. Asking the client for its version or its usage help stays independent of the engine and reports the declared minimum.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: a user who has only the client, or an outdated engine, is told in plain words what to install or upgrade instead of being handed a process-level error.

## User Experience

A user who runs a client operation without the engine sees a short message that names the engine, says the client requires it, and shows one line to copy and run that installs the engine. A user whose engine is older than required sees the required version, the version found, and one line to copy and run that installs a newer engine. A user with a current engine notices no change. Asking the client for its version still answers and also shows the minimum engine version the client needs, even where no engine is installed.

## Roadmap

—

## Goals

- A user without the engine learns the exact install instruction instead of a low-level error text.
- A user with a too-old engine learns the required version and the exact upgrade instruction.
- A user with a current engine sees no change in behaviour.
- Version reporting and usage help keep working with no engine installed.
- The minimum supported engine version is declared once and is observable by the user.

## Non-Goals

- Changing anything in the engine, including the engine's own installer and the version it reports
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together
- Any user-facing option, setting or configuration that skips or lowers the confirmation
- Changing what a client operation asks the engine, what it prints, or its exit status, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository end-to-end verification
- Translating the messages; project artifacts and user-facing messages are English

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands. It does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |
| — | The base parameterized command line stays in the engine. The separate client replaces the interactive chat mode. | D-003, User, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code. It is a Python client installed as forgel-code, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The work proceeds in order: machine-readable engine commands first, then the client, then removal of the replaced chat mode from the engine. | D-006, User accepted the proposal, 2026-11-16 18:34 |
| — | Every client-facing operation is a parameterized engine command with an optional single machine-readable object as its answer. | D-007, User accepted the proposal, 2026-11-16 18:34 |
| — | The client moves to a separate public repository in the same organization as the engine. | D-001, User, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: R-1: The client declares exactly one minimum supported engine version. That value cannot be overridden, lowered or skipped by any option, setting or configuration the user controls, and the value shown to the user is the same value enforced before use, with no second copy that could differ.
- **FR-2**: R-2: Asking the client for its own version prints the client version and the declared minimum engine version, exits successfully, and works on a machine with no engine installed, sending nothing to the engine.
- **FR-3**: R-3: The client's usage help is produced and exits successfully on a machine with no engine installed, sending nothing to the engine.
- **FR-4**: R-4: Before the client first uses the engine in an invocation, it confirms that the engine is present and asks the version the engine reports about itself, and carries that result through the rest of the invocation. Reporting the client's own version and printing usage help are exempt from this confirmation.
- **FR-5**: R-5: When the engine cannot be found or cannot be started, the invocation fails with one message that names the engine, states that the client requires it, and contains a single-line instruction that installs the engine and can be pasted and run unchanged. The requested work is not attempted, and the message never leaves the user with the low-level operating-system error text as the only thing shown.
- **FR-6**: R-6: When the engine reports a version below the declared minimum, the invocation fails with one message that names the required minimum version, the version found and a single-line instruction that installs a newer engine and can be pasted and run unchanged. The requested work is not attempted.
- **FR-7**: R-7: When the engine answers but no version can be confirmed from its answer, the invocation fails in the same actionable shape as the too-old case: it states that compatibility could not be confirmed, names the required minimum version and carries the upgrade instruction. The requested work is not attempted.
- **FR-8**: R-8: When the engine reports the declared minimum or a newer version, the requested operation proceeds exactly as before: the same requests reach the engine, the human-readable and machine-readable output is unchanged, and the exit status is unchanged.
- **FR-9**: R-9: Versions compare as sequences of numeric components, numerically, one component at a time from the first. A version with fewer components equals the same version with trailing zero components, a leading version marker and any non-numeric suffix after the numeric components do not affect the outcome, and a larger later component counts as newer even when its text is longer.
- **FR-10**: R-10: The engine's version is requested at most once per invocation. After a failed confirmation the invocation sends no request of its own to the engine.
- **FR-11**: R-11: In the client's machine-readable output form, the missing-engine and the not-compatible failures each surface as exactly one failure result carrying the same message and a non-zero exit status, consistent with the client's other failures.
- **FR-12**: R-12: Starting the interactive session performs the same confirmation first. With a missing, too-old or unconfirmable engine the session prints the actionable message and exits non-zero without opening a prompt.
- **FR-13**: R-13: The client never installs, upgrades or otherwise modifies the engine; every failure path only reports what the user can do.

## User Stories

- As a user who installed only the client, I want the client to name the engine and show me how to install it, so that I am not left with a low-level error text.
- As a user with an older engine, I want to be told the version the client requires and how to get a newer one, so that I can fix it in one step.
- As a user with a current engine, I want the client to behave exactly as before, so that this guard costs me nothing.
- As a user checking my setup, I want to see the client version and the engine version it requires without installing an engine, so that I can verify compatibility before installing anything.
- As a user who opens the interactive session, I want the engine to be confirmed before the prompt appears, so that I do not type into a session that cannot serve me.

## Acceptance Criteria

- **AC-1**: AC-1: With no engine installed, asking the client for its version exits successfully and prints the client version together with the declared minimum engine version, and no request reaches an engine. Check: repository test gate exercises the version request with no engine available and asserts the printed pair and the successful exit.
- **AC-2**: AC-2: With no engine installed, the client's usage help is printed and exits successfully, and no request reaches an engine. Check: repository test gate exercises the help request with no engine available.
- **AC-3**: AC-3: With no engine installed, an operation that needs the engine exits non-zero and prints one message that names the engine, says the client requires it, and contains a single-line install instruction readable and pasteable as printed; the printed text is not the bare low-level operating-system error. Check: repository test gate runs an engine-backed operation with no engine and asserts the named engine, the requirement statement and the pasted instruction line.
- **AC-4**: AC-4: With an engine reporting a version below the declared minimum, an engine-backed operation exits non-zero, prints one message naming the required minimum, the version found and a single-line upgrade instruction, and the engine receives no request from the operation itself beyond the version question. Check: repository test gate uses an engine reporting an older version and asserts the message content and that no operation request was made.
- **AC-5**: AC-5: With an engine that answers but reports no usable version, an engine-backed operation exits non-zero with the same actionable shape as the too-old case, and the engine receives no request from the operation itself. Check: repository test gate uses an engine whose answer carries no version and asserts the actionable message and the absence of an operation request.
- **AC-6**: AC-6: With an engine exactly at the declared minimum and with an engine newer than it, every engine-backed operation and the interactive session behave as before: the same requests reach the engine, the same human-readable output appears and the exit status is unchanged. Check: repository test gate exercises the operations against both engines and compares the requests, text and exit statuses with the behaviour that precedes this change.
- **AC-7**: AC-7: An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0, and an engine reporting 0.9.0 is accepted against a declared minimum of 0.9.0. Check: repository test gate exercises both comparisons.
- **AC-8**: AC-8: An engine reporting the declared minimum with a non-numeric suffix is accepted as equal to the minimum. Check: repository test gate exercises that engine answer.
- **AC-9**: AC-9: An invocation that uses the engine several times causes the engine's version to be asked at most once, and a failed confirmation leaves the engine with no request from the operation itself. Check: repository test gate counts the requests the engine receives in both situations.
- **AC-10**: AC-10: In the machine-readable output form, a missing-engine failure and a too-old-engine failure each yield exactly one failure result carrying the same message as the human-readable form and a non-zero exit status. Check: repository test gate exercises both failures in the machine-readable form and asserts one result, the message and the exit status.
- **AC-11**: AC-11: Starting the interactive session with no engine installed prints the install guidance and exits non-zero without ever showing a prompt, and the same holds for a too-old engine. Check: repository test gate starts the session against an absent and an old engine and asserts the guidance, the non-zero exit and the absence of a prompt.
- **AC-12**: AC-12: The minimum engine version printed by the version report and the one enforced before use are identical, and no user-facing option, setting or configuration changes the enforced value. Check: review compares the reported value with the enforced value and inspects the client's options and settings for any way to skip or lower it.
- **AC-13**: AC-13: The install and upgrade instruction lines shown in the failure messages are complete single lines that a user can paste into a terminal and run unchanged. Check: review reads the messages and judges the instruction lines to be complete and runnable as printed.

## Scope Boundaries

- One declared minimum supported engine version owned by the client
- The client's own version report showing the client version together with the declared minimum engine version
- Confirming the engine's presence and the version it reports about itself before the client first uses the engine in an invocation
- An actionable failure for a missing or unstartable engine that names the engine and carries a pasteable install instruction
- An actionable failure for an engine below the declared minimum that names the required version, the version found, and carries a pasteable upgrade instruction
- Treating an engine whose version cannot be confirmed as not compatible, reported in the same actionable shape
- Comparing versions by numeric components with an inclusive lower bound
- Keeping the client's version report and usage help usable with no engine installed
- The same confirmation before the interactive session opens
- The client's existing machine-readable output form carrying these failures
- Changing anything in the engine, including the engine's own installer and the version it reports
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together
- Any user-facing option, setting or configuration that skips or lowers the confirmation
- Changing what a client operation asks the engine, what it prints, or its exit status, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository end-to-end verification
- Translating the messages; project artifacts and user-facing messages are English

## Risks

- The engine's version answer may be absent or shaped differently than the client expects; because an unconfirmed engine is treated as too old, every engine-backed operation would then fail and the client would be unusable.
- The stand-in engines used by the existing client tests report a fixed old version and would be treated as incompatible; the test premises must be corrected instead of bypassing the confirmation.
- Treating an unconfirmed version as incompatible is strict; an engine that works but answers differently locks the user out.
- Choosing the declared minimum too high locks out engines that would otherwise work, and choosing it too low lets the client reach an engine missing the answers it depends on.
- A fixed install or upgrade instruction can drift from the engine's published install guidance and then be wrong for the user.
- The confirmation adds one engine call to every invocation; a slow version answer increases the delay the user sees before any work starts.
- A test-only bypass of the confirmation would leave the real startup path unproven.
- The user documentation in this repository still describes the version report without the declared minimum engine version; that documentation belongs to a separately planned task, so the product and its documentation are temporarily out of step.

## Open Questions

- None.

## Assumptions

- The engine reports its own version in its answer to the client, as part of the engine work planned before this task.
- The engine's version answer is cheap and stable, so asking it once per invocation does not change what the user perceives.
- The concrete minimum version value is chosen by the developer as the oldest engine that answers the client's needs, since no engine release exists yet; it is a client-owned value, not a user setting.
- Non-numeric suffixes after the numeric components are ignored, so such an engine counts as equal to its numeric version; a leading version marker is likewise ignored.
- Because an engine that cannot confirm its version cannot be trusted for the client's contract, an unconfirmed engine is treated as too old and reported in the same actionable shape.
- The install and upgrade instruction lines are taken from the engine's own published installation guidance for the current release line; the same line serves both cases because running it installs a current engine in either situation.
- The client's existing machine-readable failure convention is reused for these failures rather than adding a second shape.
- The project's cross-repository end-to-end verification, not the client's unit tests, remains the proof that the real engine and the real client work together.

## Related Documents

- README.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md
- releases/0.2.0/plan.md
- releases/0.2.0/release.md

## Revision History

- v1 — initial specification of the engine-version confirmation at client startup, the declared minimum, and the actionable install and upgrade messages.
- v2 — removed implementation wording from the non-goals and the requirement and acceptance text, restated the machine-readable output requirement in product terms, and limited the checks to this repository.
- v3 — rewrote the document as a formal product specification: decided the previously open details (comparison rules, unconfirmed engine treated as too old, single instruction line per failure, machine-readable failure shape, exempt surfaces, session confirmation) as requirements and assumptions, added an explicit requirement that the client never installs or upgrades the engine, gave every acceptance criterion a stated check, and recorded that the repository documentation lag belongs to a separately planned task.


## Summary

task call limit reached (242/200); raise task_calls with set_limit

## Files Changed

- none

## Commands

- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "log", "--oneline", "-5"]` → exit 0
- `["git", "diff", "forgel_code/cli.py"]` → exit 0
- `["git", "show", "--stat", "36510fb"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0
- `["python3", "-c", "import forgel_code.compat"]` → exit 0
- `["python3", "-m", "pytest", "tests", "-q"]` → exit 1
- `["git", "log", "--oneline", "-6"]` → exit 0
- `["git", "diff", "forgel_code/cli.py"]` → exit 0
- `["git", "show", "--stat", "36510fb"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "diff", "forgel_code/cli.py"]` → exit 0
- `["git", "show", "--stat", "--oneline", "HEAD"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff"]` → exit 0
- `["git", "log", "--oneline", "-8"]` → exit 0
- `["git", "show", "--stat", "HEAD"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "diff", "forgel_code/cli.py"]` → exit 0
- `["git", "show", "--stat", "--oneline", "HEAD"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0

## Final Test Output

```
not run
```

## Actions

- none
