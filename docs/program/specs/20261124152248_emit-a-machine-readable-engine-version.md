# Task Spec: Emit a machine-readable engine version

## Document Information

| Field | Value |
|-------|-------|
| Feature | Emit a machine-readable engine version |
| Project | — |
| Task | `20261124152248_emit-a-machine-readable-engine-version` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `main` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T19:17:16+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

To install, upgrade or refuse to run, a program must first learn which Forgel engine is installed. Today the engine offers no report of its own version that another program can read directly, so the only way to compare versions is to interpret human-readable text. A later part of the milestone needs a strictly-newer comparison and a startup minimum-version decision, and both depend on the engine stating its version in a form a program can read.

**Outcome:** Another program can obtain the engine's own version directly, without interpreting human-readable text, and that value is the version the release declares; the report works on a machine with nothing set up and leaves nothing behind, and every other check and test still passes unchanged.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: the engine must state its own identity so the Forgel Code installer can compare versions, install only a strictly newer engine, and refuse a missing or too-old one with a clear message instead of an unexplained executable-not-found failure.

## User Experience

A person pairing the two tools never has to read the engine's version as prose and interpret it: the installer reads it and decides, and a missing or too-old engine becomes an explicit decision.

## Roadmap

—

## Goals

- Another program can obtain the engine's version directly and compare it with another version without interpreting human-readable text.
- The version a caller obtains is the one the release declares.
- The engine states its version on a machine with nothing set up, without side effects and without model or network access.
- Every other check and output keeps its current, unchanged behaviour.

## Non-Goals

- The Forgel Code installer's combined install mode, its idempotent comparison and its strictly-newer rule.
- The declared minimum supported engine version and the startup check that turns a missing or too-old engine into an actionable message.
- Rewording, correcting or extending the install instructions in the user documentation.
- Automated checking of documentation text and any change to how documentation is verified.
- Changing the behaviour of the installer or of the client.
- Changing any existing program-facing report or any human-readable output of the engine.
- Deciding a new human-readable rendering of the version.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The base parameterized command line stays in the engine; the separate client replaces only the interactive chat mode. | User decision log, D-003 (accepted proposal, 2026-11-16 18:34) |
| — | The client imports nothing from the engine, so anything the client needs from the engine must be obtainable as the result of an engine command. | User decision log, D-004 (accepted proposal, 2026-11-16 18:34) |
| — | The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User decision log, D-006 (accepted proposal, 2026-11-16 18:34) |
| — | Every client-facing operation is a parameterized engine command whose result another program can read; the single free-text entry point stays the say operation. | User decision log, D-007 (accepted proposal, 2026-11-16 18:34) |

## Functional Requirements

- **FR-1**: FR-1: On request, the engine states its own version in a form another program reads directly, without interpreting human-readable text.
- **FR-2**: FR-2: The stated version is the version the release declares; the engine does not keep a second, independently editable statement of that version that can disagree with it.
- **FR-3**: FR-3: The version is expressed so that two versions can be compared component by component.
- **FR-4**: FR-4: The version can be obtained on a machine with no project, no stored configuration, no model credential, no pre-existing user data and no network, from any working directory, and obtaining it leaves no state behind.
- **FR-5**: FR-5: Obtaining the version neither starts model work nor reads or changes project, task or account records.
- **FR-6**: FR-6: When the version cannot be stated, the failure is signalled to the caller as a failure and carries its reason in the same place as the engine's other program-facing reports.
- **FR-7**: FR-7: The engine's other program-facing reports and its human-readable outputs keep their current behaviour.
- **FR-8**: FR-8: No other check or test is removed, weakened or relaxed; the behaviour of the installer and of the client stays as it is.

## User Stories

- As the Forgel Code installer I want to learn the installed engine's version directly so that I can compare versions and install only a strictly newer engine.
- As the Forgel Code client I want the engine's version to come from an engine command result so that I keep importing nothing from the engine.
- As a Forgel Code user I want the pairing decision to rest on the engine's real version so that a too-old engine is reported clearly instead of failing with an unexplained executable-not-found error.
- As a maintainer I want every existing check to stay exactly as strict as before so that adding the new report hides no real regression.

## Acceptance Criteria

- **AC-1**: AC-1: A program obtains the engine's own version directly, without interpreting human-readable text, and the value equals the version the release declares.
- **AC-2**: AC-2: The version is obtainable on a machine with no project, no stored configuration, no model access and no network, from any working directory, and obtaining it leaves nothing behind.
- **AC-3**: AC-3: All remaining checks pass unchanged.

## Scope Boundaries

- The engine states its own version in a form another program reads directly and compares.
- The stated version is the version the release declares, not a second statement kept separately that can drift.
- Versions are expressed so that two of them can be compared component by component.
- Obtaining the version works with nothing set up: no project, no stored configuration, no model access, no network, any working directory, and no state left behind.
- Obtaining the version neither starts model work nor reads or changes project, task or account records.
- The existing program-facing reports and human-readable outputs keep their current behaviour and wording.
- Assurance that no other check or test was removed, weakened or relaxed.
- The Forgel Code installer's combined install mode, its idempotent comparison and its strictly-newer rule.
- The declared minimum supported engine version and the startup check that turns a missing or too-old engine into an actionable message.
- Rewording, correcting or extending the install instructions in the user documentation.
- Automated checking of documentation text and any change to how documentation is verified.
- Changing the behaviour of the installer or of the client.
- Changing any existing program-facing report or any human-readable output of the engine.
- Deciding a new human-readable rendering of the version.

## Risks

- The engine states its version in more than one place today; if the report and the release disagree, the installer compares against the wrong value and the pairing decision is wrong.
- Obtaining the version that loads configuration, touches stored data or waits on anything would fail before a machine has been set up, which is exactly where the installer needs it.
- Adding the report on the path that already handles other requests could change the behaviour of those requests, which this task forbids.
- Tightening or loosening any existing check to make the new one fit would hide a real regression.
- This task alone does not deliver the pairing behaviour the milestone promises: the combined install mode, the strictly-newer comparison and the startup minimum-version message remain in later tasks.

## Open Questions

- None.

## Assumptions

- The version statement is one of the engine's program-facing reports, so it follows their existing conventions instead of inventing new ones.
- A caller may also ask for the version in the human-readable form the engine already uses, unchanged in behaviour.
- The version the release declares is the single authority; everything that reports or compares a version takes it from there.
- The request is issued the way the engine's other program-facing requests are issued; no new calling convention is introduced by this task.

## Related Documents

- README.md
- PLAN.md
- FORGEL.md
- AGENTS.md
- CONTRIBUTING.md

## Revision History

- v4 - owner correction applied: the requirement to remove an automated check that reads a documentation file, together with the helper data reproducing that text, and the statements that documentation correctness is established only by reading, are removed; those belonged to another task in another repository. Every other requirement, acceptance criterion and constraint is kept as it was and no new requirement is added; the verification of the remaining criteria is expressed as commands again.
- v3 - validator feedback applied: every technical detail (output shapes, naming, packaging, code and paths) removed from requirements, acceptance, constraints, goals, stories, risks and assumptions.
- v2 - owner correction applied at the time: an automated check of install instructions and the helper data reproducing that text were to be removed.
- v1 - initial specification of the machine-readable engine version report.
