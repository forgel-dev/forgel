# Agent Run: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Status: `done`
- Repository: `code`
- Steps: 531
- Finished: 2026-11-27T23:26:38+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The stub engine doubles were corrected rather than the confirmation bypassed: the tests kept exercising the client's real startup path.
- The install line uses the client's own version tag for the published install script, so running it installs a current engine and is safe to re-run in both the missing and the too-old case.
- Version questions are answered by the engine's `version` command in the machine-readable form, matching the client's existing engine protocol.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 5
- Handoffs: 4
- Model calls: 531
- Estimated input tokens (all calls): 26513514
- Provider input/output tokens: 26668888 / 526186
- Provider cache hit/miss tokens: 26256512 / 412376
- Estimated prompt at the end: 57244 tokens
- State: `docs/program/agent/20261124152248_check-the-engine-version-at-client-start.state.md`

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
| Created | 2026-11-27T21:54:16+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The client declares no minimum supported engine version and does not confirm the engine before using it, so a user who installed only the client, or who has an engine too old for the client, receives a low-level system error text or a confusing failure deep inside the operation instead of a message that says what to install or upgrade. The client therefore cannot guarantee that the engine it talks to understands what the client asks of it.

**Outcome:** The client owns one declared minimum supported engine version and confirms the engine before its first use in an invocation. A missing or unstartable engine produces one actionable message that names the engine, states that the client requires it, and carries a single installation line that can be copied and run unchanged. An engine below the minimum, or an engine whose version cannot be confirmed from its own answer, produces one actionable message that names the required minimum, the version found where one exists, and the same installation line. A compatible engine is used exactly as before. Reporting the client's own version and printing usage help stay independent of the engine and show the declared minimum.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: a user who has only the client, or an outdated engine, is told in plain words what to install or upgrade instead of being handed a process-level error.

## User Experience

A user who runs a client operation without the engine sees a short message that names the engine, says the client requires it, and shows one line to copy and run that installs the engine. A user whose engine is older than required sees the required version, the version found, and one line to copy and run that installs a newer engine. A user who asks the client for its version gets the client version and the minimum engine version the client needs, even with no engine installed. A user with a current engine notices no change.

## Roadmap

—

## Goals

- A user without the engine learns the exact install instruction instead of a low-level error text.
- A user with a too-old engine learns the required version and the exact upgrade instruction.
- A user with a current engine sees no change in behaviour.
- Version reporting and usage help keep working with no engine installed.
- The minimum supported engine version is declared once and is observable by the user.
- An engine that cannot confirm its version is reported in the same actionable shape as a too-old one.

## Non-Goals

- Changing anything in the engine, including the engine's own installer and the version it reports
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together, which the milestone plans separately
- Any user-facing option, setting or configuration that skips, lowers or overrides the confirmation
- Changing what a client operation asks the engine, what it prints, or how it ends, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository verification
- Translating the messages; project artifacts and user-facing messages are English

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The interactive client moves to a separate public repository in the same organization as the engine. | User decision log D-001, User, 2026-11-16 21:14 |
| — | The client is a thin UI over the engine's parameterized commands. It does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | User decision log D-002, User, 2026-11-16 18:31 |
| — | The base parameterized command line stays in the engine. The separate client replaces the interactive chat mode. | User decision log D-003, User, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code. It is a Python client installed as forgel-code, follows a Pareto 20/80 scope and imports nothing from the engine. | User decision log D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User decision log D-006, User accepted the proposal, 2026-11-16 18:34 |
| — | The single free-text engine entry point is forgel say. Every client-facing operation is a parameterized command with an optional single JSON object on stdout; the active project is an engine-side session with the default key local. | User decision log D-007, User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: The client declares exactly one minimum supported engine version; the value it shows the user is the same value it enforces before using the engine, and no user-controlled option or setting lowers, skips or overrides it.
- **FR-2**: Asking the client for its own version reports the client version together with the declared minimum supported engine version, ends successfully, works on a machine with no engine installed, and contacts no engine.
- **FR-3**: The client's usage help is produced and ends successfully on a machine with no engine installed, and contacts no engine.
- **FR-4**: Reporting the client's version and printing usage help are the only surfaces exempt from engine confirmation; every other client operation confirms the engine before doing anything else.
- **FR-5**: Before the client first uses the engine in an invocation it confirms that the engine is present and asks the engine the version it reports about itself, and carries that result through the rest of the invocation.
- **FR-6**: The engine's version is asked at most once per invocation.
- **FR-7**: After a failed confirmation the invocation makes no further request to the engine and does not attempt the requested work.
- **FR-8**: When the engine cannot be found or cannot be started, the invocation fails with one message that names the engine, states that the client requires it, and contains one line that installs a current engine and can be copied and run unchanged; the low-level system error text is never the only thing the user sees.
- **FR-9**: When the engine reports a version below the declared minimum, the invocation fails with one message that names the required minimum version, the version found, and one line that installs a newer engine and can be copied and run unchanged; the requested work is not attempted.
- **FR-10**: When the engine answers but no version can be confirmed from its answer, the invocation fails in the same actionable shape as the too-old case: it states that compatibility could not be confirmed, names the required minimum version and carries the line that installs a newer engine; the requested work is not attempted.
- **FR-11**: The installation line carried by every failure message is one complete line that a user can copy and run unchanged; the same line serves the missing and the too-old case because running it installs a current engine in either situation.
- **FR-12**: Versions compare as sequences of numeric components, numerically, one component at a time from the first; a version with fewer components equals the same version with trailing zero components; a leading version marker and any non-numeric suffix after the numeric components do not affect the outcome; a larger later component counts as newer even when its text is longer; the declared minimum is an inclusive lower bound.
- **FR-13**: When the engine reports the declared minimum or a newer version, the requested operation behaves exactly as before: the same requests reach the engine, the human-readable and structured output is unchanged, and the outcome is unchanged.
- **FR-14**: The client never installs, upgrades or otherwise modifies the engine; every failure path only reports what the user can do.
- **FR-15**: When the client reports a failure in its structured form, a missing engine and a not-compatible engine each appear as exactly one reported failure carrying the same message as the plain form and a non-zero outcome, consistent with the client's other failures.
- **FR-16**: Starting the interactive session performs the same confirmation first; with a missing, too-old or unconfirmable engine the session prints the actionable message and ends with a non-zero outcome without opening a prompt.

## User Stories

- As a user who installed only the client, I want the client to name the engine and show me how to install it, so that I am not left with a low-level error text.
- As a user with an older engine, I want to be told the version the client requires and how to get a newer one, so that I can fix it in one step.
- As a user with a current engine, I want the client to behave exactly as before, so that this confirmation costs me nothing.
- As a user checking my setup, I want to see the client version and the engine version it requires without installing an engine, so that I can verify compatibility before installing anything.
- As a user who opens the interactive session, I want the engine to be confirmed before the prompt appears, so that I do not type into a session that cannot serve me.

## Acceptance Criteria

- **AC-1**: With no engine installed, asking the client for its version ends successfully and reports the client version together with the declared minimum engine version, contacting no engine. Check: review observes the version request on a machine without the engine and confirms the reported pair, the successful outcome and the absence of engine contact.
- **AC-2**: With no engine installed, the client's usage help is printed and ends successfully without contacting an engine. Check: review observes the help request on a machine without the engine and confirms the printed help, the successful outcome and the absence of engine contact.
- **AC-3**: An engine reporting a version one numeric component below the minimum shown by the version report is refused as too old, and an engine reporting exactly that shown minimum is accepted. Check: review observes both boundary cases against the value the version report shows.
- **AC-4**: No user-facing option or setting lowers, skips or overrides the enforced minimum. Check: review compares the shown and enforced values and inspects the client's options and settings.
- **AC-5**: An invocation that asks the engine for several things causes the engine's version to be asked at most once. Check: review observes such an invocation and counts the version questions the engine receives.
- **AC-6**: A failed confirmation leaves the engine with no request beyond the version question, whether the engine is too old or reports no usable version. Check: review observes both failure cases and confirms that no operation request followed.
- **AC-7**: Every operation covered by the confirmation asks the engine about its version before any other request. Check: review observes the order of the requests such an operation makes to the engine.
- **AC-8**: With no engine installed, an operation that needs the engine fails and prints one message that names the engine, says the client requires it, and contains a single installation line that can be copied and run unchanged; the low-level system error is not what the user sees alone. Check: review reads the message produced without an engine.
- **AC-9**: With an engine older than the declared minimum, an operation fails and prints one message naming the required minimum, the version found and a single installation line, with no work attempted. Check: review reads the message produced against an older engine and confirms that no work was attempted.
- **AC-10**: With an engine that answers but reports no usable version, the operation fails in the same actionable shape, names the required minimum and carries the installation line. Check: review reads the message produced against an engine that reports no version and compares its shape with the too-old message.
- **AC-11**: The installation lines shown in the failure messages are complete single lines that can be copied and run unchanged. Check: review judges the printed lines to be complete and runnable as printed.
- **AC-12**: An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0; an engine reporting 0.9.0 is accepted against a minimum of 0.9.0; a minimum reported with a non-numeric suffix or with trailing zero components is accepted as equal; a leading version marker changes nothing. Check: review observes each of these comparisons.
- **AC-13**: With an engine exactly at the declared minimum and with a newer engine, every operation and the interactive session behave as before: the same requests reach the engine, the same output appears and the outcome is unchanged. Check: review compares this behaviour with the behaviour that precedes the change.
- **AC-14**: The client never installs, upgrades or modifies the engine: after each failure path nothing is installed, and an engine that was present keeps its version and content. Check: review observes the engine's state after the missing-engine and too-old failure paths.
- **AC-15**: When the client reports in its structured form, a missing engine and an engine below the minimum each yield exactly one reported failure carrying the same message as the plain form and a non-zero outcome. Check: review observes both failures in the structured form and compares the message and the outcome with the plain form.
- **AC-16**: Starting the interactive session with no engine, or with an engine below the minimum, prints the actionable message and ends with a non-zero outcome without ever showing a prompt, and the engine receives no request beyond the version question. Check: review observes the session start against an absent and an older engine.

## Work Packages

### 1. Declared minimum and engine-free surfaces
- The client declares exactly one minimum supported engine version; the value it shows the user is the same value it enforces before using the engine, and no user-controlled option or setting lowers, skips or overrides it.
- Asking the client for its own version reports the client version together with the declared minimum supported engine version, ends successfully, works on a machine with no engine installed, and contacts no engine.
- The client's usage help is produced and ends successfully on a machine with no engine installed, and contacts no engine.
- Reporting the client's version and printing usage help are the only surfaces exempt from engine confirmation; every other client operation confirms the engine before doing anything else.
- With no engine installed, asking the client for its version ends successfully and reports the client version together with the declared minimum engine version, contacting no engine. Check: review observes the version request on a machine without the engine and confirms the reported pair, the successful outcome and the absence of engine contact.
- With no engine installed, the client's usage help is printed and ends successfully without contacting an engine. Check: review observes the help request on a machine without the engine and confirms the printed help, the successful outcome and the absence of engine contact.
- An engine reporting a version one numeric component below the minimum shown by the version report is refused as too old, and an engine reporting exactly that shown minimum is accepted. Check: review observes both boundary cases against the value the version report shows.
- No user-facing option or setting lowers, skips or overrides the enforced minimum. Check: review compares the shown and enforced values and inspects the client's options and settings.

### 2. Confirmation before engine use
- Before the client first uses the engine in an invocation it confirms that the engine is present and asks the engine the version it reports about itself, and carries that result through the rest of the invocation.
- The engine's version is asked at most once per invocation.
- After a failed confirmation the invocation makes no further request to the engine and does not attempt the requested work.
- An invocation that asks the engine for several things causes the engine's version to be asked at most once. Check: review observes such an invocation and counts the version questions the engine receives.
- A failed confirmation leaves the engine with no request beyond the version question, whether the engine is too old or reports no usable version. Check: review observes both failure cases and confirms that no operation request followed.
- Every operation covered by the confirmation asks the engine about its version before any other request. Check: review observes the order of the requests such an operation makes to the engine.

### 3. Actionable failures for a missing, older or unconfirmable engine
- When the engine cannot be found or cannot be started, the invocation fails with one message that names the engine, states that the client requires it, and contains one line that installs a current engine and can be copied and run unchanged; the low-level system error text is never the only thing the user sees.
- When the engine reports a version below the declared minimum, the invocation fails with one message that names the required minimum version, the version found, and one line that installs a newer engine and can be copied and run unchanged; the requested work is not attempted.
- When the engine answers but no version can be confirmed from its answer, the invocation fails in the same actionable shape as the too-old case: it states that compatibility could not be confirmed, names the required minimum version and carries the line that installs a newer engine; the requested work is not attempted.
- The installation line carried by every failure message is one complete line that a user can copy and run unchanged; the same line serves the missing and the too-old case because running it installs a current engine in either situation.
- With no engine installed, an operation that needs the engine fails and prints one message that names the engine, says the client requires it, and contains a single installation line that can be copied and run unchanged; the low-level system error is not what the user sees alone. Check: review reads the message produced without an engine.
- With an engine older than the declared minimum, an operation fails and prints one message naming the required minimum, the version found and a single installation line, with no work attempted. Check: review reads the message produced against an older engine and confirms that no work was attempted.
- With an engine that answers but reports no usable version, the operation fails in the same actionable shape, names the required minimum and carries the installation line. Check: review reads the message produced against an engine that reports no version and compares its shape with the too-old message.
- The installation lines shown in the failure messages are complete single lines that can be copied and run unchanged. Check: review judges the printed lines to be complete and runnable as printed.

### 4. Comparison rules, unchanged behaviour and engine integrity
- Versions compare as sequences of numeric components, numerically, one component at a time from the first; a version with fewer components equals the same version with trailing zero components; a leading version marker and any non-numeric suffix after the numeric components do not affect the outcome; a larger later component counts as newer even when its text is longer; the declared minimum is an inclusive lower bound.
- When the engine reports the declared minimum or a newer version, the requested operation behaves exactly as before: the same requests reach the engine, the human-readable and structured output is unchanged, and the outcome is unchanged.
- The client never installs, upgrades or otherwise modifies the engine; every failure path only reports what the user can do.
- An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0; an engine reporting 0.9.0 is accepted against a minimum of 0.9.0; a minimum reported with a non-numeric suffix or with trailing zero components is accepted as equal; a leading version marker changes nothing. Check: review observes each of these comparisons.
- With an engine exactly at the declared minimum and with a newer engine, every operation and the interactive session behave as before: the same requests reach the engine, the same output appears and the outcome is unchanged. Check: review compares this behaviour with the behaviour that precedes the change.
- The client never installs, upgrades or modifies the engine: after each failure path nothing is installed, and an engine that was present keeps its version and content. Check: review observes the engine's state after the missing-engine and too-old failure paths.

### 5. Structured failures and the interactive session
- When the client reports a failure in its structured form, a missing engine and a not-compatible engine each appear as exactly one reported failure carrying the same message as the plain form and a non-zero outcome, consistent with the client's other failures.
- Starting the interactive session performs the same confirmation first; with a missing, too-old or unconfirmable engine the session prints the actionable message and ends with a non-zero outcome without opening a prompt.
- When the client reports in its structured form, a missing engine and an engine below the minimum each yield exactly one reported failure carrying the same message as the plain form and a non-zero outcome. Check: review observes both failures in the structured form and compares the message and the outcome with the plain form.
- Starting the interactive session with no engine, or with an engine below the minimum, prints the actionable message and ends with a non-zero outcome without ever showing a prompt, and the engine receives no request beyond the version question. Check: review observes the session start against an absent and an older engine.

## Scope Boundaries

- One declared minimum supported engine version owned by the client
- The client's own version report showing the client version together with the declared minimum engine version
- Confirming the engine's presence and the version it reports about itself before the client first uses the engine in an invocation
- An actionable failure for a missing or unstartable engine that names the engine and carries a pasteable installation instruction
- An actionable failure for an engine below the declared minimum that names the required version, the version found, and carries a pasteable installation instruction
- Treating an engine whose version cannot be confirmed as not compatible, reported in the same actionable shape
- Comparing versions by numeric components with an inclusive lower bound
- Keeping the client's version report and usage help usable with no engine installed
- The same confirmation before the interactive session opens
- The client's existing structured failure reporting carrying these failures
- The declaration that the client never installs, upgrades or modifies the engine itself
- Changing anything in the engine, including the engine's own installer and the version it reports
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together, which the milestone plans separately
- Any user-facing option, setting or configuration that skips, lowers or overrides the confirmation
- Changing what a client operation asks the engine, what it prints, or how it ends, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository verification
- Translating the messages; project artifacts and user-facing messages are English

## Risks

- If the engine's version answer is absent or shaped differently than the client expects, every operation that needs the engine would fail because an unconfirmed engine is treated as too old, and the client would be unusable.
- The engine work that provides the version answer may not be complete when this task lands, so no real engine would pass the confirmation.
- The project's existing cross-repository verification may rely on an engine that reports an older version and would be rejected; its premise must be corrected rather than the confirmation bypassed.
- Treating an unconfirmed version as incompatible is strict; an engine that works but answers differently locks the user out.
- Choosing the declared minimum too high locks out engines that would otherwise work; choosing it too low lets the client reach an engine missing the answers it depends on.
- The printed installation line can drift from the project's published installation guidance, and the combined installation it names is planned separately and may not exist yet when this task lands.
- The confirmation adds one engine question to every invocation; a slow version answer increases the delay before any work starts.
- The user documentation in this repository still describes the version report without the declared minimum engine version; that documentation belongs to a separately planned task, so product and documentation are temporarily out of step.

## Open Questions

- None.

## Assumptions

- The engine reports its own version when the client asks, as part of the engine work planned before this task.
- The engine's version answer is cheap and stable, so asking it once per invocation does not noticeably delay the user.
- No engine release exists yet, so the concrete minimum is chosen by the developer against the engine's planned capabilities rather than against a published release.
- The single installation line comes from the project's published guidance for the current release line and installs a current engine; because it is safe to re-run when the client is already present, one line serves both the missing and the too-old case.
- An engine that cannot confirm its version cannot be trusted for the client's contract, so it is treated as too old and reported in the same actionable shape.
- A leading version marker and any non-numeric suffix after the numeric components are ignored, and missing trailing components count as zero.
- The interactive session belongs to the client, so confirming the engine before it opens is part of this task.
- The client's existing non-zero outcome convention is reused for these failures; no specific non-zero value is required.

## Related Documents

- README.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md
- releases/0.2.0/plan.md
- releases/0.2.0/release.md

## Revision History

- v1 — initial specification of the engine-version confirmation at client startup, the declared minimum, and the actionable install and upgrade messages.
- v2 — removed implementation wording from the non-goals and the requirement and acceptance text, restated the structured output requirement in product terms, and limited the checks to this repository.
- v3 — rewrote the document as a formal product specification: decided the comparison rules, the treatment of an unconfirmed engine, the single instruction line per failure, the structured failure shape, the exempt surfaces and the session confirmation; forbade the client from installing or upgrading the engine; gave every acceptance criterion a stated check; recorded the documentation lag as a separately planned task.
- v4 — flattened requirements and acceptance into single ordered lists, grouped them into five titled work packages with integer indices and at most four acceptance criteria each, removed remaining implementation wording from every section, replaced automated checks with review-verifiable observations and dropped the test command.


## Summary

Completed and verified the engine-version confirmation at client startup. The client enforces a single declared minimum engine version (forgel_code/compat.py) that is the same value the version report shows; `--version` and help stay engine-free. Every other command and the interactive session confirm the engine once, ask for its version exactly once, and refuse a missing, too-old or unconfirmable engine before any operation request. Failure paths print one actionable English message naming the engine, the required minimum and the found version, with a single copy-pasteable install line, and reuse the existing plain/JSON failure reporting and non-zero exit codes. Version comparison follows the numeric-component rules. This session fixed the test doubles so they answer the version question: tests/stub_engine.py now defines the module-level ENGINE it referenced (the version answer previously raised NameError) and answers `version`/`--version` before replaying canned output, and tests/test_interactive.py's inline stub answers `version` and exports FORGEL_ENGINE so the real startup path reaches the stub. Verified with the repository gate `python3 -m unittest discover -s tests`: 378 tests, OK.

## Files Changed

- `forgel_code/cli.py`
- `forgel_code/interactive.py`
- `tests/stub_engine.py`
- `tests/test_cli.py`
- `tests/test_cli_extra.py`
- `tests/test_interactive.py`

## Commands

- `["git", "status", "--porcelain"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["git", "log", "--oneline", "-6"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "show", "--stat", "36510fb"]` → exit 0
- `["git", "show", "--stat", "28a08eb"]` → exit 0
- `["git", "show", "--stat", "bc13e6e"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "log", "--oneline", "-12"]` → exit 0
- `["git", "show", "--stat", "36510fb"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["git", "log", "--oneline", "-4", "--", "forgel_code/compat.py"]` → exit 0
- `["git", "show", "--name-only", "HEAD"]` → exit 0
- `["git", "show", "--name-status", "36510fb"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["git", "diff", "--", "forgel_code/interactive.py", "tests/test_cli_extra.py", "tests/test_cli.py"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_stub_contract", "-v"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_stub_contract", "-v"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_stub_contract", "tests.test_interactive"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_stub_contract"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_stub_contract", "-v"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_stub_contract", "-v"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_interactive"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_interactive.BareStartTest"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=all"]` → exit 0
- `["git", "log", "--oneline", "-5", "--", "tests/test_version_report.py", "forgel_code/compat.py"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
..........................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 378 tests in 267.460s

OK

```

## Actions

- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/cli.py
- read_file: forgel_code/__init__.py
- read_file: forgel_code/compat.py
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- run: ['git', 'log', '--oneline', '-6']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: forgel_code/engine.py
- run: ['git', 'grep', '-n', 'compat', '--', 'forgel_code', 'tests']
- search_files: compat|confirm|MIN_ENGINE_VERSION @ forgel_code
- run: ['git', 'show', '--stat', '36510fb']
- run: ['git', 'show', '--stat', '28a08eb']
- run: ['git', 'show', '--stat', 'bc13e6e']
- search_files: version_report|minimum_engine @ tests
- read_file: tests/stub_engine.py
- read_file: README.md
- read_file: tests/test_stub_contract.py
- read_file: forgel_code/interactive.py
- search_files: Engine\(|engine\.run|^def run|^def main|confirm @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- search_files: 0\.0\.0 @ .
- read_file: tests/test_version_report.py
- search_files: FORGEL_STUB_STDOUT|FORGEL_STUB_SLEEP|FORGEL_STUB_EXIT @ tests *.py
- search_files: FORGEL_STUB_STDOUT|FORGEL_STUB_EXIT|class .*Engine|Engine\(|def run_client|FORGEL_ENGINE @ tests/test_cli.py
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- read_file: forgel_code/compat.py
- run: ['git', 'grep', '-n', 'compat', '--', 'forgel_code', 'tests']
- search_files: compat|MIN_ENGINE_VERSION|confirm @ forgel_code
- read_file: forgel_code/cli.py
- read_file: forgel_code/__init__.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/interactive.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['git', 'log', '--oneline', '-12']
- read_file: tests/stub_engine.py
- search_files: MIN_ENGINE_VERSION|compat\.|0\.0\.0 @ tests
- search_files: numeric_version|supported\(|INSTALL_INSTRUCTION|requires the|install.sh @ tests
- search_files: Engine\(|def run\(|def default_engine|def session_run|compat @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_version_report.py
- run: ['git', 'show', '--stat', '36510fb']
- read_file: tests/test_interactive.py
- read_file: tests/test_stub_contract.py
- search_files: raw.githubusercontent.com|install.sh|curl @ README.md
- search_files: FORGEL_STUB_STDOUT|FORGEL_STUB_EXIT|recorded_argv|len\(self.calls @ tests
- read_file: tests/test_cli.py
- read_file: tests/stub_engine_install.py
- read_file: README.md
- search_files: STUB_ENGINE =|stub_engine|def _write_engine|def _write_stub|from forgel_code.cli import main @ tests
- search_files: class InteractiveSession|    def write|    def call|    def show_failure|    def __init__\(self, engine @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_cli_extra.py
- read_file: forgel_code/compat.py
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- read_file: forgel_code/cli.py
- search_files: confirm|MIN_ENGINE_VERSION|version_report @ forgel_code
- search_files: compat|confirm @ forgel_code/interactive.py
- search_files: compat|MIN_ENGINE_VERSION|confirm @ tests
- read_file: tests/test_version_report.py
- run: ['git', 'ls-files', '--', 'forgel_code/compat.py']
- run: ['git', 'log', '--oneline', '-4', '--', 'forgel_code/compat.py']
- search_files: Engine\(|def run\(|def default_engine|def main|def run_session|engine\.run @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/engine.py
- search_files: stub_engine|STUB_ENGINE|class .*Engine @ tests
- search_files: compat|INSTALL_INSTRUCTION|missing_message|outdated_message|unconfirmed_message|numeric_version|supported\( @ .
- read_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- read_file: tests/test_stub_contract.py
- read_file: tests/test_cli.py
- run: ['git', 'show', '--name-only', 'HEAD']
- run: ['git', 'show', '--name-status', '36510fb']
- read_file: forgel_code/__init__.py
- read_file: README.md
- read_file: tests/test_interactive.py
- read_file: tests/test_cli.py
- search_files: from forgel_code.cli import main|forgel_code\",|interactive\.run\(|main\(\[ @ tests
- read_file: forgel_code/interactive.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- search_files: launcher.write_text|_write_engine|def _write_stub|FAKE_ENGINE =|STUB_ENGINE = @ tests
- edit_file: forgel_code/cli.py
- search_files: interactive\.run\(|main\(\[\]\)|main\(list|run_client\("--version @ tests
- read_file: tests/test_interactive.py
- search_files: InteractiveSession\(|interactive\.run\( @ tests
- read_file: forgel_code/cli.py
- read_file: forgel_code/cli.py
- edit_file: forgel_code/cli.py
- read_file: forgel_code/cli.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- edit_file: forgel_code/interactive.py
- search_files: 0\.0\.0 @ .
- read_file: tests/test_interactive.py
- read_file: tests/test_redact.py
- edit_file: tests/test_cli.py
- read_file: tests/test_cli.py
- edit_file: tests/test_cli_extra.py
- read_file: tests/test_idle_refresh.py
- edit_file: forgel_code/interactive.py
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: tests/stub_engine.py
- read_file: forgel_code/compat.py
- read_file: tests/test_stub_contract.py
- run: ['git', 'diff', '--', 'forgel_code/interactive.py', 'tests/test_cli_extra.py', 'tests/test_cli.py']
- read_file: forgel_code/cli.py
- search_files: class OneShotUnchangedTest|def run_client|FAKE|stub|version @ tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/__init__.py
- search_files: MIN_ENGINE_VERSION|minimum engine|engine version|0\.0\.0|0\.1\.0 @ . *.md
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- search_files: 0\.0\.0 @ .
- read_file: forgel_code/interactive.py
- search_files: compat|^def run|    def run\(self\)|class InteractiveSession @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- search_files: self\.calls\(\) @ tests/test_interactive.py
- read_file: tests/test_interactive.py
- search_files: compat\. @ forgel_code/interactive.py
- read_file: forgel_code/engine.py
- search_files: --version|minimum_engine_version|forgel-code 0\.2\.0 @ tests
- search_files: def default_engine|def show_failure|def write @ forgel_code/interactive.py
- search_files: stub_engine|STUB_ENGINE\b @ tests
- search_files: FORGEL_STUB_SLEEP|FAKE_ENGINE_SLEEP|SESSION_STUB_SLEEP|124 @ tests
- read_file: forgel_code/interactive.py
- search_files: interactive\.run\(|compat|confirm @ tests
- read_file: tests/stub_engine.py
- edit_file: forgel_code/interactive.py
- search_files: main\(\[\]\)|interactive\.run\(|run_interactive @ tests
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- edit_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- edit_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', 'tests.test_interactive']
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract']
- read_file: tests/stub_engine.py
- read_file: tests/test_stub_contract.py
- edit_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- read_file: forgel_code/compat.py
- read_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- edit_file: tests/stub_engine.py
- read_file: forgel_code/engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- search_files: class BareStartTest|class OneShotUnchangedTest|def _write_launcher|def _launcher|def setUp|STUB|PATH @ tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- search_files: self\.calls\(\)|MIN_ENGINE_VERSION|FORGEL_ENGINE @ tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/cli.py
- search_files: def run|FORGEL_ENGINE|DEFAULT_TIMEOUT|default_engine @ forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- run: ['python3', '-m', 'unittest', 'tests.test_interactive']
- read_file: tests/test_interactive.py
- edit_file: tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'tests.test_interactive']
- read_file: tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'tests.test_interactive']
- search_files: FORGEL_ENGINE @ tests/test_interactive.py
- read_file: tests/test_interactive.py
- read_file: tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'tests.test_interactive']
- read_file: tests/test_interactive.py
- edit_file: tests/test_interactive.py
- search_files: self\.engine_path @ tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'tests.test_interactive.BareStartTest']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- run: ['git', 'log', '--oneline', '-5', '--', 'tests/test_version_report.py', 'forgel_code/compat.py']
