# Task Spec: Add the combined engine and client install mode

## Document Information

| Field | Value |
|-------|-------|
| Feature | Add the combined engine and client install mode |
| Project | — |
| Task | `20261124152248_add-the-combined-engine-and-client-insta` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T19:20:30+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The repository currently keeps an automated check that reads the installation instructions and asserts their exact wording and command text. The project forbids any automated check that reads documentation text: documentation is text and is accepted or returned by review only. That check, together with the helper data that reproduces the documented text, therefore has to go — without a replacement and without touching any other check or any program behaviour — while the installation instructions themselves must still tell the owner that one command installs the client together with a supported engine.

**Outcome:** The change set no longer contains any automated check that reads documentation text and no helper data reproducing that text; nothing was added in its place; every other automated check is still present, none was weakened, and they all pass. The installation instructions, read by a person, state that the one documented command installs the client together with an engine the client supports, name the default engine source and how a run can be pointed elsewhere, describe the client-only option and that it leaves any engine untouched, and state that a successful run reports which engine version is in place and how it was obtained. The installer and the client behave exactly as before outside that text.

## Product Intent

Forgel Code is a thin client over the engine and cannot work without it, so its documented installation must be understood as installing a supported pair, not a lone client. At the same time, documentation is text in this project and is judged by reading it, never by a machine that re-reads it; the installation instructions stay honest through review, and no other guarantee is traded away to get there.

## User Experience

An owner who reads the installation instructions understands that the single documented command leaves them with a client and a supported engine that work together, knows which engine source is used by default and how to point the run elsewhere, knows there is a client-only option that leaves an existing engine untouched, and knows that the run will tell them which engine version they ended up with and how it was obtained. A maintainer reviewing a change to those instructions reads the text and accepts or returns it; nothing in the automated suite re-reads the documentation, and every behavioural guarantee the suite already gave stays exactly as strong as it was.

## Roadmap

—

## Goals

- No automated check reads documentation text anywhere in the change set
- No helper data reproducing documentation text remains
- No replacement check of documentation text is introduced
- Every other automated check stays present and passes
- Installer and client behaviour is unchanged
- The installation instructions, read by a person, describe the pair installation, the default engine source, the client-only option and the engine version report

## Non-Goals

- Adding, keeping or substituting any automated check that reads a documentation file
- Changing the version comparison, the ordering rules or the fallback behaviour of the installation
- Changing the declared minimum engine version
- Changing the client's commands, output forms or interactive session
- Changing the engine project, its releases or its installer
- Rewriting documentation outside the installation instructions

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | Documentation is text and is verified by review: never add, require or accept a test, guard or automated check that reads a documentation file; a documentation task has review-only checks and no test command. | D-106, FORGEL.md native rules and AGENTS.md project rules |
| — | The client is a thin UI over the engine's parameterized commands and does not call the model, read project files or run checks itself; model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, user decision log |
| — | The client's working name is Forgel Code; it is a Python client installed as a separate distribution that imports nothing from the engine. | D-004, user decision log |

## Functional Requirements

- **FR-1**: The change set contains no automated check that reads documentation text.
- **FR-2**: The helper data that reproduced the documented installation text is gone, so no automated check can compare the instructions against a stored copy.
- **FR-3**: The check that previously read the installation instructions no longer exists and no replacement check of documentation text is introduced in its place.
- **FR-4**: Every other automated check remains present, its premise is unchanged, and none is removed or weakened by this change.
- **FR-5**: The installer and the client keep their previous behaviour: this change alters no program behaviour outside the wording of the installation instructions.
- **FR-6**: The installation instructions state, as text, that the single documented command installs the client together with an engine the client supports, so the result is a working pair.
- **FR-7**: The installation instructions name the default engine source and state how a run can be pointed at another source.
- **FR-8**: The installation instructions describe the client-only installation option and state that it leaves any engine untouched.
- **FR-9**: The installation instructions state that a successful run reports which engine version is in place and how it was obtained.
- **FR-10**: The installation instructions no longer present an already installed engine as a precondition the owner must satisfy before running the documented command.
- **FR-11**: The installation instructions are accepted or returned only by reviewing their text.

## User Stories

- As an owner reading the installation instructions, I want to know that one command gives me a client and a supported engine, so that I understand what the command does before I run it.
- As an owner who already has an engine, I want the instructions to tell me about the client-only option, so that I can install the client without touching the engine.
- As an owner reading the instructions, I want to know which engine source is used and how to change it, so that I can point the run at the engine I trust.
- As a maintainer, I want the installation instructions judged by reading them, so that no automated check depends on documentation wording and nothing else is weakened in exchange.

## Acceptance Criteria

- **AC-1**: Reading the change set finds no automated check that reads documentation text and no stored copy of documented text.
- **AC-2**: The check that previously asserted the installation instructions' wording and command text is absent, and nothing equivalent was added.
- **AC-3**: Every other automated check is still present with its original premise, and a full run of the suite passes.
- **AC-4**: The installer and the client behave as they did before this change; no behavioural check was altered, relaxed or deleted.
- **AC-5**: Reading the installation instructions shows that one documented command installs the client together with a supported engine.
- **AC-6**: Reading the installation instructions shows the default engine source and how to point a run at another one.
- **AC-7**: Reading the installation instructions shows the client-only option and that it leaves any engine untouched.
- **AC-8**: Reading the installation instructions shows that a successful run reports the engine version in place and how it was obtained.
- **AC-9**: Reading the installation instructions finds no statement that an engine must already be installed before the documented command is run.
- **AC-10**: The installation instructions are accepted or returned by a person reading them, with no automated check involved.

## Scope Boundaries

- Removing the automated check that read the installation instructions and asserted their wording and command text
- Removing the helper data that reproduced the documented installation text
- Introducing no replacement automated check over documentation text of any kind
- Keeping every other automated check present, unweakened and passing
- Keeping the installer's and the client's behaviour unchanged
- Updating the installation instructions, as text, to state the pair installation, the default engine source and how to point a run elsewhere, the client-only option, and the engine version report of a successful run
- Adding, keeping or substituting any automated check that reads a documentation file
- Changing the version comparison, the ordering rules or the fallback behaviour of the installation
- Changing the declared minimum engine version
- Changing the client's commands, output forms or interactive session
- Changing the engine project, its releases or its installer
- Rewriting documentation outside the installation instructions

## Risks

- Removing the documentation-reading check drops the only automation that caught a stale or divergent installation command in the instructions; a divergence now survives until a reader notices it, which the owner has accepted.
- A developer may be tempted to reintroduce an equivalent check over documentation text, for example a narrower one, which the change explicitly forbids.
- The helper data that reproduced the documented text may be spread across more than one place, so a partial removal leaves a stored copy behind.
- Removing the check may accidentally remove or weaken a neighbouring behavioural check, which would fail the requirement that all others stay intact.
- The installation instructions may be corrected in one place while an older sentence elsewhere still requires an already installed engine, leaving the text self-contradictory under review.
- Documentation review is subjective; a reviewer with a different reading of the engine source or of the client-only option may return the text, costing another cycle.

## Open Questions

- None.

## Assumptions

- The single automated check that read documentation text is the one over the installation instructions; no other automated check is known to read documentation, and the review confirms it.
- The helper data to remove is the stored wording and command text that check compared against; no other file reproduces that text.
- The installation already places a supported engine alongside the client, so the instructions can be corrected without changing any program behaviour.
- The installation instructions are the repository's install, update and uninstall text; no other document is in scope.
- The owner accepts that a stale instruction now survives until a reader notices it, because no automated check may read the documentation.
- Writing about the pairing is documentation work, so its verification is review; the behaviour it describes is already covered by the existing behavioural checks.

## Related Documents

- README.md
- CHANGELOG.md
- install.sh

## Revision History

- 1.0 — initial specification of the combined engine and client installation mode.
- 1.1 — per the owner's change request, the automated check that read the installation instructions is removed together with the helper data that reproduced that text, no replacement check over documentation text is added, every other check and every other installer and client behaviour stays unchanged, and the installation instructions are accepted or returned by text review only.
- 1.2 — rewritten as a documentation change: all checks are review-only and there is no test command; the requirements and acceptance state only observable outcomes and contain no command, path, tool name or other implementation detail.
