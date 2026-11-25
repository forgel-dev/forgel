# Agent Run: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Status: `done`
- Repository: `code`
- Steps: 208
- Finished: 2026-11-25T04:42:56+00:00

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
- Sessions: 5
- Handoffs: 4
- Model calls: 208
- Estimated input tokens (all calls): 11733067
- Provider input/output tokens: 11887264 / 178413
- Provider cache hit/miss tokens: 11562240 / 325024
- Estimated prompt at the end: 19274 tokens
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
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

Forgel Code currently fails with a low-level operating-system error text when the engine is absent, which names nothing the user can act on, and it declares no minimum supported engine version, so an engine that is present but too old for the client fails later in a confusing way.

**Outcome:** Forgel Code declares one minimum supported engine version and confirms the engine before using it. A missing engine produces a single actionable message naming the engine and carrying the install instruction; an engine below the minimum, or one whose version cannot be confirmed, produces a single actionable message naming the required version and carrying the upgrade instruction; a compatible engine is used exactly as before. Asking the client for its version or its usage help still succeeds with no engine installed.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: a user who has only the client, or an outdated engine, is told in plain words what to install or upgrade instead of being handed a process-level error.

## User Experience

A user who runs a client operation without the engine sees a short message that names the engine, says the client requires it, and shows one line to copy and run that installs the engine. A user whose engine is older than required sees the required version, the version found, and one line to copy and run that installs a newer engine. A user whose engine is current notices no change. Asking the client for its version still answers and also shows the minimum engine version the client needs, even where no engine is installed.

## Roadmap

—

## Goals

- A user without the engine learns the exact install instruction instead of a low-level error text.
- A user with a too-old engine learns the required version and the exact upgrade instruction.
- A user with a current engine sees no change in behavior.
- Version reporting and usage help keep working with no engine installed.
- The minimum supported engine version is declared once and is observable by the user.

## Non-Goals

- Changing anything in the engine, including the engine's own installer and its version reporting
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together
- Any user-facing option, setting or configuration that skips or lowers the confirmation
- Changing what a client operation asks the engine, or what it prints, or its exit status, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository end-to-end verification
- Translating the messages; project artifacts are English

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it calls no model, reads no project files and runs no checks itself. | D-002, User, 2026-11-16 18:31 |
| — | The base parameterized command line stays in the engine; the client adds no capability of its own. | D-003, User, 2026-11-16 18:31 |
| — | The client is a Python client installed as forgel-code and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The work proceeds in order: machine-readable engine commands first, then the client, then removal of the replaced chat mode from the engine. | D-006, User accepted the proposal, 2026-11-16 18:34 |
| — | Every client-facing operation is a parameterized engine command with an optional single machine-readable object as its answer. | D-007, User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: The client declares exactly one minimum supported engine version as its own fixed value; that value cannot be overridden, lowered or skipped by any option, setting or configuration the user controls.
- **FR-2**: The client's own version report prints both the client version and the declared minimum engine version, succeeds, and works where no engine is installed.
- **FR-3**: The client's usage help is still produced and still succeeds where no engine is installed.
- **FR-4**: Before the first use of the engine in a client invocation, the client confirms that the engine is present and which version the engine reports about itself, and carries that result through the rest of the invocation.
- **FR-5**: When the engine cannot be found or cannot be started, the client fails with one message that names the engine, states that the client requires it, and contains a runnable instruction for installing the engine; the operation is not attempted and the user is never left with only the low-level operating-system text.
- **FR-6**: When the engine is present but reports a version below the declared minimum, the client fails with one message naming the required minimum version, the version found, and a runnable instruction for installing a newer engine; the requested operation is not attempted.
- **FR-7**: When the engine answers but no version can be confirmed from its answer, the client fails the same actionable way as for an engine below the minimum, stating that compatibility could not be confirmed and naming the required minimum; it never proceeds on an unconfirmed engine.
- **FR-8**: When the engine reports a version equal to the declared minimum or newer, the requested operation proceeds with the same engine requests, the same human-readable and machine-readable output, and the same exit status as before.
- **FR-9**: Versions are compared as sequences of numeric components, numerically, one component at a time from the first; a version with fewer components counts as equal to the same version with trailing zero components, and any non-numeric suffix after the numeric components does not affect the outcome; a larger later component therefore counts as newer even when its text is longer.
- **FR-10**: The engine's version is requested at most once per invocation; after a failed confirmation the operation sends no request of its own to the engine.
- **FR-11**: In the client's machine-readable output form, each of these failures surfaces the same message and a non-zero exit, exactly as the client already reports its other failures.
- **FR-12**: Starting the interactive session performs the same confirmation first, so with a missing or too-old engine the session prints the actionable message and exits with a non-zero status instead of opening a prompt.
- **FR-13**: The minimum engine version shown by the client's version report is the same single value enforced before use; the client holds no second copy that could differ.

## User Stories

- As a user who installed only the client, I want the client to name the engine and show me how to install it, so that I am not left with a low-level error text.
- As a user with an older engine, I want to be told the version the client requires and how to get a newer one, so that I can fix it in one step.
- As a user with a current engine, I want the client to behave exactly as before, so that this guard costs me nothing.
- As a user checking my setup, I want to see the client version and the engine version it requires without installing an engine, so that I can verify compatibility before installing anything.

## Acceptance Criteria

- **AC-1**: With no engine installed, asking the client for its version exits successfully and prints the client version and the declared minimum engine version.
- **AC-2**: With no engine installed, the client's usage help exits successfully and is printed.
- **AC-3**: With no engine installed, an operation that needs the engine exits non-zero and prints one message that names the engine, says the client requires it, and contains an install instruction that can be pasted and run as printed; that message is not the low-level operating-system error text standing alone.
- **AC-4**: With an engine below the declared minimum, an operation that needs the engine exits non-zero and prints one message naming the required minimum version, the version found, and an upgrade instruction that can be pasted and run as printed; no work is done through the engine.
- **AC-5**: With an engine that answers but reports no usable version, an operation that needs the engine exits non-zero with the same actionable shape as the too-old case and no work is done through the engine.
- **AC-6**: With an engine exactly at the declared minimum and with an engine newer than it, every engine-backed operation and the interactive session behave as before: the same requests reach the engine, the same human-readable output appears, and the exit status is unchanged.
- **AC-7**: An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0, and an engine reporting 0.9.0 is accepted against a declared minimum of 0.9.0.
- **AC-8**: An engine reporting the declared minimum with a non-numeric suffix is accepted as equal to the minimum.
- **AC-9**: An operation that uses the engine several times causes the engine's version to be requested at most once, and a failed confirmation leaves the engine with no request from the operation itself.
- **AC-10**: In the machine-readable output form, a missing-engine failure and a too-old-engine failure each yield exactly one failure result carrying the same message and a non-zero exit.
- **AC-11**: Starting the interactive session with no engine installed prints the install guidance and exits non-zero instead of opening a prompt.
- **AC-12**: The minimum engine version printed by the version report and the one enforced before use are identical.
- **AC-13**: The install and upgrade instructions printed in the failure messages are concrete enough to be pasted into a terminal and run unchanged.

## Scope Boundaries

- One declared minimum supported engine version owned by the client
- The client's own version report showing the client version together with the declared minimum engine version
- Confirming the engine's presence and self-reported version before the client first uses the engine in an invocation
- An actionable message for a missing or unstartable engine that names the engine and carries a runnable install instruction
- An actionable message for an engine below the declared minimum that names the required version, the version found, and carries a runnable upgrade instruction
- Treating an engine whose version cannot be confirmed as not compatible, reported the same actionable way
- Comparing versions by numeric components with an inclusive lower bound
- Keeping the client's version report and usage help usable with no engine installed
- The same confirmation before the interactive session opens
- The client's existing machine-readable output form carrying these failures
- Changing anything in the engine, including the engine's own installer and its version reporting
- Installing or upgrading the engine on the user's behalf; the client only shows the instruction
- A combined installation that installs engine and client together
- Any user-facing option, setting or configuration that skips or lowers the confirmation
- Changing what a client operation asks the engine, or what it prints, or its exit status, when the engine is compatible
- Updating user documentation and release notes, which the milestone plans separately
- Replacing or relaxing the project's existing cross-repository end-to-end verification
- Translating the messages; project artifacts are English

## Risks

- The engine's version answer may be absent or shaped differently than the client expects; because an unconfirmed engine is treated as too old, every engine-backed operation would then fail and the client would be unusable.
- The stand-in engines used by the existing client tests report a fixed old version and would be treated as incompatible; the test premises must be corrected instead of bypassing the confirmation.
- Treating an unconfirmed version as incompatible is strict; an engine that works but answers differently locks the user out.
- Choosing the declared minimum too high locks out engines that would otherwise work, and choosing it too low lets the client reach an engine missing the answers it depends on.
- A hard-coded install or upgrade instruction can drift from the engine's published install guidance and then be wrong for the user.
- The confirmation adds one engine call to every invocation; a slow engine version answer increases the delay the user sees before any work starts.
- A test-only bypass of the confirmation would leave the real startup path unproven.

## Open Questions

- None.

## Assumptions

- The engine reports its own version in its answer to the client, as part of the engine work planned before this task.
- The engine's version answer is cheap and stable, so requesting it once per invocation does not change what the user perceives.
- The concrete minimum version value is chosen by the developer as the first engine version that reports its version, since no engine release exists yet; the value is a client-owned constant, not a user setting.
- Non-numeric suffixes after the numeric components are ignored, so such an engine counts as equal to its numeric version.
- Because an engine that cannot confirm its version cannot be trusted for the client's contract, an unconfirmed engine is treated as too old.
- Documented install and upgrade instruction wording is taken from the engine's own published install guidance for the current release line.
- The client's existing machine-readable failure convention is reused for these failures rather than adding a second shape.
- Test selection keywords named in the checks identify tests the developer writes for these behaviors; the exact test names are the developer's choice.
- The project's cross-repository end-to-end verification, not the client's unit tests, remains the proof that the real engine and the real client work together.

## Related Documents

- README.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md

## Revision History

- v1 — initial specification of the engine-version confirmation at client startup, the declared minimum, and the actionable install and upgrade messages.
- v2 — removed implementation wording from the non-goals and the requirement and acceptance text, restated the machine-readable output requirement in product terms, and limited the checks to this repository.


## Summary

No code change in this session; the engine-version confirmation is implemented in forgel_code/compat.py (constant MIN_ENGINE_VERSION, version comparison and actionable install/upgrade messages), wired into the client's engine startup path, version report, usage help and interactive session, and the test suite passes.

## Files Changed

- `forgel_code/compat.py`

## Commands

- `["git", "status", "--porcelain"]` → exit 0
- `["python3", "-m", "pytest", "tests", "-q", "-x"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "status", "--porcelain", "--untracked-files=no"]` → exit 0
- `["python3", "-m", "pytest", "tests", "-q", "-x"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python3", "-m", "pytest", "tests", "-q"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python3", "-m", "pytest", "tests", "-q"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
...............................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 367 tests in 297.380s

OK

```

## Actions

- read_file: forgel_code/cli.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/commands.py
- read_file: tests/stub_engine.py
- read_file: tests/test_stub_contract.py
- read_file: README.md
- read_file: install.sh
- read_file: forgel_code/__init__.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_cli.py
- recall
- read_file: tests/stub_engine.py
- read_file: install.sh
- read_file: forgel_code/__init__.py
- run: ['git', 'status', '--porcelain']
- run: ['git', 'grep', '-n', 'MIN_ENGINE_VERSION']
- run: ['python3', '-m', 'pytest', 'tests', '-q', '-x']
- read_file: install.sh
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/engine.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/__init__.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/commands.py
- read_file: tests/stub_engine.py
- read_file: README.md
- run: ['git', 'status', '--porcelain', '--untracked-files=no']
- read_file: tests/test_stub_contract.py
- list_files
- read_file: forgel_code/compat.py
- read_file: tests/test_cli.py
- write_file: forgel_code/compat.py
- read_file: tests/test_cli.py
- run: ['python3', '-m', 'pytest', 'tests', '-q', '-x']
- read_file: tests/test_interactive.py
- run: ['grep', '-rn', 'MIN_ENGINE_VERSION', 'forgel_code', 'install.sh', 'tests', 'README.md', 'CHANGELOG.md', 'pyproject.toml']
- read_file: tests/test_interactive.py
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/compat.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/__init__.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/commands.py
- run: ['grep', '-rn', 'MIN_ENGINE_VERSION\\|compat\\|confirm(', 'forgel_code', 'install.sh', 'tests', 'README.md', 'CHANGELOG.md', 'pyproject.toml']
- read_file: install.sh
- read_file: forgel_code/__main__.py
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'pytest', 'tests', '-q']
- read_file: tests/test_stub_contract.py
- read_file: tests/test_stub_contract.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_cli.py
- run: ['git', 'status', '--porcelain']
- read_file: tests/test_cli.py
- read_file: tests/stub_engine_install.py
- read_file: README.md
- read_file: tests/test_cli_extra.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/compat.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/cli.py
- list_files
- run: ['python3', '-m', 'pytest', 'tests', '-q']
