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
| Created | 2026-11-24T18:08:23+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

To install, upgrade or refuse to run, a program must first learn which Forgel engine is installed. Today the engine offers no report of its own version that another program can read directly, so the only way to compare versions is to interpret human-readable text. A later part of the milestone needs a strictly-newer comparison and a startup minimum-version decision, and both depend on the engine stating its version in a form a program can read. At the same time, the correctness of the install instructions in the user documentation is currently decided by an automated check that reads that text; the project treats documentation as text judged by reading, so that check goes and nothing replaces it.

**Outcome:** Another program can obtain the engine's own version directly, without interpreting human-readable text, and that value is the version the release declares; the report works on a machine with nothing set up and leaves nothing behind. The verification run no longer contains any automated check of the documentation text about installation, no such check replaced it, and every other check and test still passes unchanged.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: the engine must state its own identity so the Forgel Code installer can compare versions, install only a strictly newer engine, and refuse a missing or too-old one with a clear message instead of an unexplained executable-not-found failure. Documentation stays text, judged by reading, so a wording change in the install instructions can never break the verification run.

## User Experience

A person pairing the two tools never has to read the engine's version as prose and interpret it: the installer reads it and decides, and a missing or too-old engine becomes an explicit decision. Nobody has to keep the install instructions and an automated check of those instructions in step; the instructions are accepted by reading them, and a correction to their wording is a documentation decision, not a build failure.

## Roadmap

—

## Goals

- Another program can obtain the engine's version directly and compare it with another version without interpreting human-readable text.
- The version a caller obtains is the one the release declares.
- The engine states its version on a machine with nothing set up, without side effects and without model or network access.
- The verification run contains no automated check of the documentation text, and every other check still passes unchanged.

## Non-Goals

- The Forgel Code installer's combined install mode, its idempotent comparison and its strictly-newer rule.
- The declared minimum supported engine version and the startup check that turns a missing or too-old engine into an actionable message.
- Rewording, correcting or extending the install instructions in the user documentation.
- Changing the behaviour of the installer or of the client.
- Changing any existing program-facing report or any human-readable output of the engine.
- Deciding a new human-readable rendering of the version.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | Every client-facing operation is a parameterized engine command whose result another program can read; the single free-text entry point stays the say operation. | User decision log, D-007 (accepted proposal, 2026-11-16 18:34) |
| — | The base parameterized command line stays in the engine; the separate client replaces only the interactive chat mode. | User decision log, D-003 (accepted proposal, 2026-11-16 18:34) |
| — | The client imports nothing from the engine, so anything the client needs from the engine must be obtainable as the result of an engine command. | User decision log, D-004 (accepted proposal, 2026-11-16 18:34) |
| — | The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User decision log, D-006 (accepted proposal, 2026-11-16 18:34) |

## Functional Requirements

- **FR-1**: On request, the engine states its own version in a form another program reads directly, without interpreting human-readable text.
- **FR-2**: The stated version is the version the release declares; the engine does not keep a second, independently editable statement of that version that can disagree with it.
- **FR-3**: The version is expressed so that two versions can be compared component by component.
- **FR-4**: The version can be obtained on a machine with no project, no stored configuration, no model credential, no pre-existing user data and no network, from any working directory, and obtaining it leaves no state behind.
- **FR-5**: Obtaining the version neither starts model work nor reads or changes project, task or account records.
- **FR-6**: When the version cannot be stated, the failure is signalled to the caller as a failure and carries its reason in the same place as the engine's other program-facing reports.
- **FR-7**: The engine's other program-facing reports and its human-readable outputs keep their current behaviour.
- **FR-8**: The automated check that reads the install instructions in the user documentation is removed, together with any helper data that reproduces the documentation text for that check.
- **FR-9**: No other automated check of the documentation text is added in its place: whether the documented install instructions are correct is decided by reading the text, not by an automated check.
- **FR-10**: No other check or test is removed, weakened or relaxed; the behaviour of the installer and of the client stays as it is.

## User Stories

- As the Forgel Code installer I want to learn the installed engine's version directly so that I can compare versions and install only a strictly newer engine.
- As the Forgel Code client I want the engine's version to come from an engine command result so that I keep importing nothing from the engine.
- As a Forgel Code user I want the pairing decision to rest on the engine's real version so that a too-old engine is reported clearly instead of failing with an unexplained executable-not-found error.
- As a maintainer I want the install instructions judged by reading them so that a wording change never breaks the verification run.
- As a maintainer I want every other check to stay exactly as strict as before so that removing the documentation check hides no real regression.

## Acceptance Criteria

- **AC-1**: A program obtains the engine's own version directly, without interpreting human-readable text, and the value equals the version the release declares.
- **AC-2**: The version is obtainable on a machine with no project, no stored configuration, no model access and no network, from any working directory, and obtaining it leaves nothing behind.
- **AC-3**: The verification run contains no check that reads the documentation text about installation.
- **AC-4**: All remaining checks pass unchanged.
- **AC-5**: The documented install instructions are accepted or returned for correction on the basis of reading their text.

## Scope Boundaries

- The engine states its own version in a form another program reads directly and compares.
- The stated version is the version the release declares, not a second statement kept separately that can drift.
- Versions are expressed so that two of them can be compared component by component.
- Obtaining the version works with nothing set up: no project, no stored configuration, no model access, no network, any working directory, and no state left behind.
- Obtaining the version neither starts model work nor reads or changes project, task or account records.
- The existing program-facing reports and human-readable outputs keep their current behaviour and wording.
- Removal of the automated check that reads the install instructions in the user documentation, together with any helper data that reproduced that text for the check.
- Assurance that no automated check of the documentation text replaced it, and that no other check or test was removed, weakened or relaxed.
- The Forgel Code installer's combined install mode, its idempotent comparison and its strictly-newer rule.
- The declared minimum supported engine version and the startup check that turns a missing or too-old engine into an actionable message.
- Rewording, correcting or extending the install instructions in the user documentation.
- Changing the behaviour of the installer or of the client.
- Changing any existing program-facing report or any human-readable output of the engine.
- Deciding a new human-readable rendering of the version.

## Risks

- The engine states its version in more than one place today; if the report and the release disagree, the installer compares against the wrong value and the pairing decision is wrong.
- The automated check of the install instructions may be entangled with unrelated assertions; removing it carelessly can remove or weaken other verification, which this task forbids.
- Obtaining the version that loads configuration, touches stored data or waits on anything would fail before a machine has been set up, which is exactly where the installer needs it.
- Judging the install instructions by reading is slower and less mechanical than a check; a reviewer may accept text an automated check would have caught, and the project accepts that trade deliberately.
- This task alone does not deliver the pairing behaviour the milestone promises: the combined install mode, the strictly-newer comparison and the startup minimum-version message remain in later tasks.

## Open Questions

- None.

## Assumptions

- The owner's correction is binding for this task: removing the automated check of the install instructions belongs to this change even though the task is about the engine's version.
- The version statement is one of the engine's program-facing reports, so it follows their existing conventions instead of inventing new ones.
- A caller may also ask for the version in the human-readable form the engine already uses, unchanged in behaviour.
- The version the release declares is the single authority; everything that reports or compares a version takes it from there.
- The documentation criteria are judged by reading, as the project requires, so they are review-only and carry no automated check.

## Related Documents

- README.md
- PLAN.md
- FORGEL.md
- AGENTS.md
- CONTRIBUTING.md
- docs/program/commands.md

## Revision History

- v3 - validator feedback applied: the specification is treated as documentation-bearing, so every acceptance criterion carries a review-only check and the task declares no test command; every technical detail (output shapes, naming, packaging, code and paths) removed from requirements, acceptance, constraints, goals, stories, risks and assumptions.
- v2 - owner correction applied: the automated check that reads the install instructions in the user documentation, and the helper data that reproduced that text for it, are removed; no automated check of documentation text replaces it; every other check stays untouched.
- v1 - initial specification of the machine-readable engine version report.
