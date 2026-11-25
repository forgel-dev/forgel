# Agent Run: Document the combined install and minimum engine version

- Task: `20261124152248_document-the-combined-install-and-minimu`
- Status: `failed`
- Repository: `code`
- Steps: 2
- Finished: 2026-11-25T15:28:25+00:00

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
- Estimated input tokens (all calls): 17129
- Provider input/output tokens: 8676 / 108
- Provider cache hit/miss tokens: 4608 / 4068
- Estimated prompt at the end: 8658 tokens
- State: not needed

## Specification (`docs/program/specs/20261124152248_document-the-combined-install-and-minimu.md`)

# Task Spec: Document the combined install and minimum engine version

## Document Information

| Field | Value |
|-------|-------|
| Feature | Document the combined install and minimum engine version |
| Project | — |
| Task | `20261124152248_document-the-combined-install-and-minimu` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The client's user documentation describes only how to install Forgel Code and leaves the engine to the reader: it states that the engine must already be available, offers no way to obtain it, names no minimum engine version, says nothing about what happens when the engine is missing or too old, and says nothing about how a second install treats an engine that is already present. A reader who follows the documented install on a machine without the engine ends up with a client that fails on every engine-backed command with a bare not-found error about a missing engine program, and no guidance.

**Outcome:** The Forgel Code user documentation presents one default install action that brings the engine and the client in as one pair, documents the engine's own standalone install as the alternative, states the minimum supported engine version as one concrete version, describes the repeat-install behaviour that installs the engine only when it is missing or strictly older and never takes an equal or newer engine backwards, and describes the message a user sees when the engine is missing or too old, including the fact that version and diagnostic output still work without an engine. The changelog records the same set of user-visible changes.

## Product Intent

Forgel and Forgel Code must install and run as one working pair: a user who wants the agent client should not have to discover, install and version-match the engine on their own, and a user whose engine is missing or too old should be told what to do instead of being shown a bare not-found error.

## User Experience

A reader of the client's front page copies the first install action they see and, with no second step, ends up with a working pair: engine and client present and ready to run. Running the same install action later upgrades the client and upgrades the engine only when the available engine is strictly newer than the installed one, so a machine that already has a newer engine is never taken backwards. A user who wants only the engine, or already has one, finds the engine's standalone install stated separately. When the client finds no engine, or an engine below the declared minimum, its first engine-backed use produces a message that names what is wrong and how to fix it — install the engine, or upgrade it — rather than a bare not-found error; asking the client for its version or a diagnostic still answers.

## Roadmap

—

## Goals

- Make the documented default install produce a working engine-and-client pair with no second step.
- Make the engine's standalone install discoverable from the client's front page.
- Make the supported engine range, and the consequence of falling outside it, explicit before the reader installs.
- Make the repeat-install behaviour predictable, in particular that an equal or newer engine is never taken backwards.
- Make the failure a user sees without a usable engine actionable instead of a bare not-found error, while keeping version and diagnostics usable.

## Non-Goals

- Changing the behaviour of the install action, the client's version check or the engine's own install.
- Describing internal structure, steps, ordering, timings or the local environment.
- Documenting the engine's command surface beyond what the install story needs.
- Documenting Windows-specific routes beyond what the page already says.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin user interface over the engine's parameterized commands and does not call the model, read project files or run checks itself; model access, the sandbox, QA, review and release approval stay in the engine. | D-002, user decision log |
| — | The client's working name is Forgel Code. | D-004, user decision log |
| — | Documentation is text and is verified by review: never add, require or accept a test, guard or automated check that reads a documentation file. | D-106, project rules (FORGEL.md / AGENTS.md) |
| — | Documentation states behaviour and contracts, never volatile implementation details such as internal structure, timings, runtime bounds or local environment. | D-109, project rules (FORGEL.md) |

## Functional Requirements

- **FR-1**: The install part of the client's front page presents exactly one default install action, placed before any other installation route, and states that it installs the engine and the client together.
- **FR-2**: That default install is documented as needing no additional option, flag or follow-up step: running the documented action as shown yields both programs.
- **FR-3**: The page no longer requires the reader to obtain the engine themselves before installing the client; any remaining statement that an engine must already be present is presented as the situation of an existing installation, not as a precondition.
- **FR-4**: The page documents the engine's standalone install as a separate single-action path, for a reader who wants the engine without the client or who already has the client.
- **FR-5**: The page states the minimum supported engine version as one concrete version, and states that the client refuses engine-backed work when the engine it finds is older than that minimum.
- **FR-6**: The page states the repeat-install behaviour: running the same documented install again replaces the client, compares the engine version already present with the engine version that install would provide, installs the engine when it is missing or strictly older, and leaves an equal or newer engine exactly as it is, so an existing newer engine is never taken backwards.
- **FR-7**: The page describes the message shown when the engine is missing: it states that no engine was found, names the minimum supported engine version, and points at the install a reader can run to obtain the engine, the combined install and the standalone engine install both being acceptable pointers.
- **FR-8**: The page describes the message shown when the engine is too old: it states that an engine was found but is below the supported minimum, names the version found and the minimum supported version, and points at the upgrade a reader can run.
- **FR-9**: The page states that a missing or too-old engine does not block version and diagnostic output: asking the client for its version, or for a diagnostic answer, works without an engine, while the commands that need the engine fail with the message above.
- **FR-10**: These statements are presented as behaviour of the shipped product, not as a description of how it is built: no internal structure, no step ordering, no timing, duration or runtime bound, no local environment detail, and no promise about a release that has not been published.
- **FR-11**: Everything added is in English and agrees with what the shipped product actually does; where documentation and product disagree, the documentation is corrected.
- **FR-12**: The client's changelog gains an entry, under the changes not yet released, recording as user-visible changes the combined default install of engine and client, the engine's standalone install, the declared minimum supported engine version with its startup message, and the repeat-install behaviour that never takes an equal or newer engine backwards.

## User Stories

- As someone who wants the agent client, I want the install I am shown first to bring in the engine as well, so that I do not have to find, install and version-match a second program before the client works.
- As someone who already has a newer engine, I want a repeat install to leave it alone, so that installing the client again never takes my engine backwards.
- As someone who wants only the engine, I want its own install stated separately, so that I do not have to install a client I will not use to get it.
- As someone whose engine is missing or too old, I want to be told which version is supported and how to get it, so that I can fix it instead of reading a bare not-found error.
- As someone with no engine yet, I want the client's version and diagnostic answers to still work, so that I can inspect what I have while I sort the engine out.

## Acceptance Criteria

- **AC-1**: Reviewing the install part of the page, its first installation route is a single action that the text says installs the engine and the client together, and no other installation route appears before it.
- **AC-2**: Reviewing the install part of the page, nothing tells the reader they must first obtain or pre-install the engine in order to install the client.
- **AC-3**: Reviewing the install part of the page, the engine's standalone install is documented as its own separate path.
- **AC-4**: Reviewing the install part of the page, exactly one concrete minimum supported engine version is stated, together with the statement that an older engine is refused.
- **AC-5**: Reviewing the install part of the page, the repeat-install paragraph states that the engine is installed only when missing or strictly older and that an equal or newer installed engine is left untouched, so it is never taken backwards.
- **AC-6**: Reviewing the install part of the page, both the missing-engine message and the too-old-engine message are described, and each is actionable: the missing one names the minimum version and points at an install, the too-old one names both the found and the minimum versions and points at an upgrade.
- **AC-7**: Reviewing the page as a whole, it states that version and diagnostic output work without an engine while engine-backed commands fail with the actionable message.
- **AC-8**: Reviewing the page as a whole, the added prose contains no internal structure, step ordering, timing, duration, runtime bound or local environment detail, and no reference to a release that has not been published.
- **AC-9**: Reviewing the client's changelog, its entry for changes not yet released covers the combined default install, the standalone engine install, the minimum supported engine version with the startup message, and the repeat-install behaviour that never takes an equal or newer engine backwards.
- **AC-10**: Reviewing the whole change, every documented statement agrees with the behaviour of the shipped product, and no previously correct statement about installing the client was made false.

## Scope Boundaries

- The client's user-facing front page: how installation is presented, the engine requirement, the upgrade statement and the startup-failure statement.
- The client's changelog entry for the combined install, the standalone engine install, the minimum supported engine version, the never-downgrade repeat-install behaviour and the startup message.
- Stating the declared minimum supported engine version as one concrete version.
- Changing the behaviour of the install action, the client's version check or the engine's own install.
- Describing internal structure, steps, ordering, timings or the local environment.
- Documenting the engine's command surface beyond what the install story needs.
- Documenting Windows-specific routes beyond what the page already says.

## Risks

- The combined default install and the declared minimum engine version are delivered by other work in the same milestone; if their naming or behaviour differs from what is written here, the documentation misleads the reader and must be reconciled with the shipped product before it is accepted.
- The page already names a specific published location for obtaining the client; if the new install story is written while that statement is left stale, the page contradicts itself.
- Documenting a minimum supported engine version that drifts from the value the client actually enforces turns a clear startup message into a misleading one.
- It is easy to slip into describing how installation works internally — steps, ordering, timing — which the documentation rules forbid.
- If the standalone engine install is documented with a location that later moves, the documented upgrade path becomes a dead end.

## Open Questions

- None.

## Assumptions

- The combined install is the default behaviour of the install action the page already leads with, so the literal text a reader copies does not change and this task is prose plus a changelog entry.
- The concrete minimum supported engine version is decided by the work that introduces it; the documentation states whatever concrete minimum the shipped client enforces and deliberately does not fix the number here.
- The output that must work without an engine is the client's own version output and its diagnostic output; every other command counts as engine-backed.
- The documentation lives on the client's front page and in the client's changelog; no new document is introduced.
- The engine's standalone install is a single documented action of its own by the time this documentation is written, and the client page describes it rather than restating the engine's own install text in full.

## Related Documents

- README.md
- CHANGELOG.md

## Revision History

- 1.0 — initial specification for this documentation task
- 1.1 — removed implementation wording from constraints, risks and assumptions; all checks are review-only with no test command
- 1.2 — restated the review-only constraint as a plain statement that the deliverable is text


## Summary

model call failed: model endpoint returned an empty answer

## Files Changed

- none

## Commands

- none

## Final Test Output

```
not run
```

## Actions

- none
