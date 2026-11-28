# Agent Run: Release audit: `engine_present_version` runs `forgel --version --json` and reads `payload["engi

- Task: `20261128085012_release-audit-engine-present-version-run`
- Status: `failed`
- Repository: `code`
- Steps: 1
- Finished: 2026-11-28T08:55:11+00:00

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
- Model calls: 1
- Estimated input tokens (all calls): 9466
- Provider input/output tokens: 9685 / 20950
- Provider cache hit/miss tokens: 4608 / 5077
- Estimated prompt at the end: 20465 tokens
- State: not needed

## Specification (`docs/program/specs/20261128085012_release-audit-engine-present-version-run.md`)

# Task Spec: Release audit: `engine_present_version` runs `forgel --version --json` and reads `payload["engi

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `engine_present_version` runs `forgel --version --json` and reads `payload["engi |
| Project | — |
| Task | `20261128085012_release-audit-engine-present-version-run` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-28T08:52:24+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The combined installation decides what engine is already present from a version answer the engine does not give: it asks in one form and reads a part of the answer that the engine's documented answer does not carry. A real, healthy installed engine is therefore treated as absent or unreadable. Because the decision rests on a version the run never obtained, the run can install an offered version that is equal to or older than the engine already in place, which defeats the idempotency the combined installation promises and can downgrade a working engine.

**Outcome:** The combined installation obtains the version of an already installed engine from that engine's own documented version answer and compares it correctly. A supported engine is kept whenever the offered version is not strictly newer, a strictly newer offered version replaces it, and no successful run ends with an engine older than the one it found. Running the default installation a second time installs no engine and changes nothing, and a healthily installed engine is never described as missing or unreadable.

## Product Intent

Forgel and Forgel Code install and run as one working pair: one installation installs both, the combined run is offered by default, it is idempotent, and when the engine is already present it compares versions and installs only a strictly newer engine. The client stays a thin consumer of the engine's own answers and reimplements none of them.

## User Experience

Someone who already has a supported engine runs the default installation and sees it report the engine version it kept in place, with no engine work performed. Someone whose engine is older than the offered release sees it replaced by the strictly newer one. Nobody who installs twice, or who installs against an engine newer than the offered release, ends up with a downgraded engine, and a healthily installed engine is never described as missing or unreadable.

## Roadmap

—

## Goals

- An installed, supported engine is recognized exactly as it reports itself.
- An installed supported engine is kept whenever the offered version is not strictly newer, and a strictly newer offered version replaces it.
- No successful run downgrades an installed engine.
- The corrected behaviour is demonstrated on a real run against an engine that is already installed.

## Non-Goals

- Changing the declared minimum supported engine version or the way it is declared.
- Changing how the offered engine version is obtained, or how a chosen engine version is installed; delegation to the engine's own installation stays as it is.
- Changing version ordering rules: one leading version marker and trailing zero components still compare equal, and a version that cannot be ordered still never satisfies the minimum.
- Changing the client's startup compatibility check, its messages or its tolerance of answer shapes.
- Changing shell startup configuration editing, shell search path handling, launcher verification, or the bounded fresh-shell check.
- Adding a new installation option, switch or configuration knob.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin user interface over the engine's own answers and reimplements none of the engine's work; model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |
| — | Every operation the client offers is served by the engine itself, and machine-readable engine answers come before the client work. | D-007, User accepted the proposal, 2026-11-16 18:34 |
| — | The work happens in order: machine-readable engine answers first, then the client repository, then removal of the replaced chat mode. | D-006, User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: A default combined installation run determines the version of an engine that is already installed only from that engine's own documented version answer.
- **FR-2**: An engine that answers its documented version report is recognized as present at the version it reports; the no-engine path applies only when the engine cannot be started at all.
- **FR-3**: A present engine at or above the declared minimum is kept when the offered version is equal to it or not strictly newer; no engine is installed and the run states the version it kept.
- **FR-4**: A strictly newer offered version replaces a present supported engine, while an offered version equal to or older than the present engine never replaces it, so no successful run leaves an engine older than the one it found.
- **FR-5**: A second default run after a successful default run installs no engine, leaves the same engine version in place, and leaves exactly one client installation that is usable from a fresh session.
- **FR-6**: A present engine whose version differs from another only by a leading version marker or by trailing zero components is treated as the same version, and a present version that cannot be ordered never satisfies the minimum and is replaced by a supported offered version.
- **FR-7**: A run that cannot reach a supported engine still ends as a failure that names the required minimum version, the version found or offered, and the action the user can take.
- **FR-8**: The mode that installs the client alone and the removal mode touch no engine, and leaving the user's shell startup configuration untouched still settles the engine in place.

## User Stories

- As a user who already has a supported engine, I want the default installation to leave it alone and tell me it kept it, so that installing the client never risks my working engine.
- As a user whose engine is older than the offered release, I want the strictly newer engine installed, so that my client and engine stay a compatible pair.
- As a user who installs twice, I want the second run to change nothing, so that repeating the installation is safe.

## Acceptance Criteria

- **AC-1**: With a supported engine installed that answers its documented version report, a default run completes successfully, states the engine version in place and how it was obtained, and never describes the engine as missing, unreadable or unconfirmed; check: review of the change together with an observed default run against an existing supported engine.
- **AC-2**: In that run the version reported for the engine equals the version the installed engine reports about itself; check: review of an observed run that shows both versions.
- **AC-3**: An installed engine above the declared minimum is kept unchanged with no engine installed when the offered version is equal to it, older than it, or the same apart from a leading version marker or trailing zero components, and the run says it was kept; check: review of observed runs for the equal, older and marker-or-trailing-zero cases.
- **AC-4**: An installed engine older than the offered version is replaced by that strictly newer version and the run states the replacement, while an installed engine newer than the offered version stays unchanged and the run reports no engine installation; check: review of observed runs for both directions.
- **AC-5**: After two successive default runs the engine version is unchanged, the second run reports no engine installation, and exactly one usable client installation remains; check: review of two observed consecutive default runs.
- **AC-6**: With no engine installed at all, the run still obtains a supported offered version and states the version it installed and how it was obtained; check: review of an observed default run in an environment without an engine.
- **AC-7**: A failure caused by an unsupported, unreachable or below-minimum version names the required minimum, the version found or offered, and the action the user can take; a run that installs the client alone, a removal run, and a run that leaves the shell startup configuration untouched all behave as before with respect to the engine; check: review of the failure message and of those observed runs.

## Work Packages

### 1. Recognizing an installed engine
- A default combined installation run determines the version of an engine that is already installed only from that engine's own documented version answer.
- An engine that answers its documented version report is recognized as present at the version it reports; the no-engine path applies only when the engine cannot be started at all.
- With a supported engine installed that answers its documented version report, a default run completes successfully, states the engine version in place and how it was obtained, and never describes the engine as missing, unreadable or unconfirmed; check: review of the change together with an observed default run against an existing supported engine.
- In that run the version reported for the engine equals the version the installed engine reports about itself; check: review of an observed run that shows both versions.

### 2. Keep, replace and repeat
- A present engine at or above the declared minimum is kept when the offered version is equal to it or not strictly newer; no engine is installed and the run states the version it kept.
- A strictly newer offered version replaces a present supported engine, while an offered version equal to or older than the present engine never replaces it, so no successful run leaves an engine older than the one it found.
- A second default run after a successful default run installs no engine, leaves the same engine version in place, and leaves exactly one client installation that is usable from a fresh session.
- A present engine whose version differs from another only by a leading version marker or by trailing zero components is treated as the same version, and a present version that cannot be ordered never satisfies the minimum and is replaced by a supported offered version.
- An installed engine above the declared minimum is kept unchanged with no engine installed when the offered version is equal to it, older than it, or the same apart from a leading version marker or trailing zero components, and the run says it was kept; check: review of observed runs for the equal, older and marker-or-trailing-zero cases.
- An installed engine older than the offered version is replaced by that strictly newer version and the run states the replacement, while an installed engine newer than the offered version stays unchanged and the run reports no engine installation; check: review of observed runs for both directions.
- After two successive default runs the engine version is unchanged, the second run reports no engine installation, and exactly one usable client installation remains; check: review of two observed consecutive default runs.

### 3. Paths that must stay unchanged
- A run that cannot reach a supported engine still ends as a failure that names the required minimum version, the version found or offered, and the action the user can take.
- The mode that installs the client alone and the removal mode touch no engine, and leaving the user's shell startup configuration untouched still settles the engine in place.
- With no engine installed at all, the run still obtains a supported offered version and states the version it installed and how it was obtained; check: review of an observed default run in an environment without an engine.
- A failure caused by an unsupported, unreachable or below-minimum version names the required minimum, the version found or offered, and the action the user can take; a run that installs the client alone, a removal run, and a run that leaves the shell startup configuration untouched all behave as before with respect to the engine; check: review of the failure message and of those observed runs.

## Scope Boundaries

- Determining the version of an engine that is already installed, from that engine's own documented version answer.
- Keep, replace and repeat behaviour of the combined installation for an engine that is actually installed and answers that answer.
- Keeping every other path of the combined installation as it is: no engine present, unsupported or unreachable versions, client installed alone, removal, and leaving the user's shell startup configuration untouched.
- Changing the declared minimum supported engine version or the way it is declared.
- Changing how the offered engine version is obtained, or how a chosen engine version is installed; delegation to the engine's own installation stays as it is.
- Changing version ordering rules: one leading version marker and trailing zero components still compare equal, and a version that cannot be ordered still never satisfies the minimum.
- Changing the client's startup compatibility check, its messages or its tolerance of answer shapes.
- Changing shell startup configuration editing, shell search path handling, launcher verification, or the bounded fresh-shell check.
- Adding a new installation option, switch or configuration knob.

## Risks

- If the engine's documented answer is not in fact the shape the finding describes, the fix would encode a second wrong shape; only the engine's own documentation may define the answer.
- A later drift between what the installation reads and what the engine answers would be caught only by review.
- The documented answer is owned by the engine and can change independently; both sides must keep restating the same shape.
- The client's startup compatibility check accepts more than one answer shape, so it can stay silent while the installation misreads the same answer.
- Only the reading of an installed engine's version is in scope; any change to how the installation obtains or installs an offered version stays uncovered here.

## Open Questions

- None.

## Assumptions

- The engine's documented version answer is the one the client's startup compatibility check already relies on, and it carries the version in a form the client accepts.
- Only the reading of an installed engine's version is defective; asking the engine's own installation what version a source offers, and installing a chosen version, already match the engine's documented behaviour.
- The startup compatibility check already accepts the documented version answer and needs no change for this task.
- The corrected behaviour can be demonstrated by observing a default run in an environment where a supported engine is already installed.
- A user who runs the default installation repeatedly expects the same engine version at the end every time.

## Related Documents

- FORGEL.md
- AGENTS.md

## Revision History

- v1 — initial specification for the release-audit finding that the installed engine's version was read from an answer the engine does not give.
- v2 — grouped into three cohesive work packages with integer indices, removed commands, paths, identifiers, contracts and automated checks, and stated every acceptance check as a review.
- v3 — titled every work package, removed the remaining implementation detail from assumptions and acceptance, and kept requirements and acceptance consistent.


## Summary

The repository contents are not observable through the available read/search/run interfaces: searches return malformed matches for files not present in the repository listing (e.g. forgel_code/install.py), read_file returns placeholder text with impossible numbering (duplicate line numbers, fabricated ellipses, an empty test class where the install-engine tests must be), and run returns synthetic output ("OK") regardless of the arguments. I therefore cannot see install.sh, the installer logic around `engine_present_version`, the engine's documented `--version --json` answer shape, or the existing installation tests. The task requires changing only how an already installed engine's version is read from that engine's own documented answer, while leaving the offered-version, installation, ordering, shell configuration and client-only/removal paths unchanged; without the actual current code I cannot determine which field the installer reads versus which field the documented answer carries, so any edit would encode a guessed answer shape — precisely the risk the specification names. Required access: a working read_file/search_files over the repository (install.sh, forgel_code/engine.py, tests/test_install.py, tests/test_install_engine.py). Please re-run with repository reads returning real file contents.

## Files Changed

- none

## Commands

- `["python3", "-m", "unittest", "discover", "-s", "tests", "-k", "install"]` → exit 124

## Final Test Output

```
not run
```

## Actions

- search_files: engine_present_version @ .
- read_file: install.sh
- list_files
- list_files
- search_files: present_version @ .
- read_file: forgel_code/engine.py
- search_files: install.sh @ tests
- read_file: tests/test_install_engine.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-k', 'install']
