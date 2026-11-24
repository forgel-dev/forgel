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
| Created | 2026-11-24T21:24:37+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The documented one-command installation of Forgel Code installs only the client, so on a machine without the engine the first client request fails with an unhelpful missing-engine error. A user who follows the installation exactly still does not get a working pair, and the installation names no origin for a supported engine. In addition, the correctness of the installation instructions is currently enforced by an automated check that reads the documentation text, which the project rules forbid: documentation is text and is verified by review.

**Outcome:** The documented default installation of Forgel Code yields a working client together with a supported engine. The installation is idempotent: it obtains an engine only when none is present or when the version the configured engine source offers is strictly newer than the present one; an engine at or above the offered version is left untouched. The finished state always satisfies the client's declared minimum supported engine version, and when it cannot, the installation fails with a message naming the required minimum, the version that was found or offered, and the action the user can take. A successful installation states which engine version is in place and how it was obtained, and the engine source it depends on is documented configuration. No automated check reads documentation text any more and none replaces it: the installation instructions are accepted or returned solely by review of their text, while every other check and the installer and client behavior outside the combined installation remain unchanged.

## Product Intent

Make Forgel and Forgel Code install and run as one working pair: the client is a thin UI over the engine's parameterized commands, so a client without a supported engine is useless. The client's own documented installation therefore brings a supported engine onto the machine, while the engine's lifecycle stays with the engine. Documentation states behavior and is judged by people reading it, never by automated checks over its text.

## User Experience

The user performs the single documented installation and afterwards has a working client and a supported engine, without a second setup guide and without hunting for an engine. The installation reads like a short report of what it ended with: the engine version in place and whether it was installed, kept or replaced. A user who cannot reach a supported engine never sees a raw process error; the installation stops and says which minimum is required, which version was found or offered, and what to do next. A user who manages the engine themselves, or who only wants the client side, chooses the documented client-only installation and no engine is queried or touched. A contributor experiences no automated verdict on documentation wording: the instructions are read and judged by a reviewer.

## Roadmap

—

## Goals

- A user who follows the documented installation obtains a working client-and-engine pair.
- The combined installation is safe to repeat: no engine churn when nothing newer is offered, and no duplicate client artifacts.
- A user who cannot reach a supported engine gets a clear, actionable failure instead of a raw process error.
- A user who does not want the installation to manage the engine keeps a documented way to install the client alone.
- The engine source the installation depends on is documented configuration rather than hidden behavior.
- The automated checks no longer contain any check that reads documentation text, while every other check and the installer and client behavior outside the combined installation stay unchanged, and the installation instructions are accepted or returned by reading them.

## Non-Goals

- Building or changing the engine's own installation facility
- Uninstalling or downgrading an engine
- Changing the client's startup check of the engine version
- Changing any client request or its output
- Changing the client's installation location, launcher, startup entry, fresh-session verification or removal behavior beyond what the engine decision needs
- Removing the replaced chat mode from the engine
- Installation on Windows
- Managing engine credentials, projects or model configuration
- Adding any automated check of the documentation text in place of the removed one
- Changing, weakening or removing any other check, or changing installer and client behavior outside the combined installation

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself, so it is only useful with a supported engine beside it. | D-002, User, 2026-11-16 18:31 |
| — | The client is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The work proceeds in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | D-006, User accepted the proposal, 2026-11-16 18:34 |
| — | Documentation is text and is verified by review: never add, require or accept a test, guard or automated check that reads a documentation file. A documentation task has review-only checks and no test command. | Project rules FORGEL.md and AGENTS.md (D-106); restated by the owner for this task |

## Functional Requirements

- **FR-1**: The default client installation also ensures a supported engine is in place in the same run.
- **FR-2**: The installation learns which engine version the configured engine source offers without changing anything on the machine.
- **FR-3**: When no engine is present, the installation obtains the offered engine version.
- **FR-4**: When an engine is present and the offered version is not strictly newer, the installation keeps the present engine and changes nothing about the engine installation.
- **FR-5**: When the offered version is strictly newer than the present engine, the installation replaces the present engine with that newer one.
- **FR-6**: The installation never installs an engine older than, or equal to, the one already present.
- **FR-7**: The finished state always satisfies the client's declared minimum supported engine version; when it cannot, the installation ends as a failure instead of reporting the pair as installed.
- **FR-8**: A failed engine outcome reports the required minimum version, the version that was found or offered, and a concrete action the user can take, and is clearly distinguishable from a successful run.
- **FR-9**: A successful installation states the engine version in place and how it was obtained: installed, kept or replaced.
- **FR-10**: Engine versions are ordered numerically component by component, tolerating one leading version prefix and trailing zero components; a version that cannot be ordered never counts as satisfying the minimum.
- **FR-11**: The documented client-only installation installs the client and neither queries nor changes any engine.
- **FR-12**: Removing the client installs nothing and leaves any engine in place.
- **FR-13**: The documented option that keeps the user's startup configuration unchanged does not disable the engine part of the installation.
- **FR-14**: The engine source the installation resolves against is documented configuration with a stated default and a documented way to point it elsewhere.
- **FR-15**: Repeating the default installation changes nothing about an engine that needs no change, and leaves exactly one client installation and one startup entry.
- **FR-16**: The user documentation presents the default installation as the way to obtain a working client-and-engine pair, documents the client-only installation and the engine source configuration, and no longer instructs the user to supply an engine separately.
- **FR-17**: The project's automated checks contain no check that reads documentation text, and no automated check of documentation text is added in its place.
- **FR-18**: The correctness of the installation instructions is accepted or returned solely by review of their text.
- **FR-19**: Every other automated check stays in place and unchanged, and the installer and client behavior outside the combined installation is unchanged.

## User Stories

- As a new user, I want the documented installation to give me both the client and a supported engine, so that the first thing I type works instead of failing with a missing-engine error.
- As a returning user, I want repeating the installation to leave my current engine alone unless a strictly newer one is offered, so that an update never downgrades or churns my engine.
- As a user whose engine cannot be brought to a supported version, I want to be told the required minimum, what was found and what to do, so that I can fix it without guessing.
- As a user who manages the engine myself, I want a documented client-only installation, so that the installation never touches my engine.
- As a contributor, I want the installation instructions judged by a person reading them, so that a wording change is never blocked or forced by an automated check over documentation text.

## Acceptance Criteria

- **AC-1**: Starting the default installation on a machine with no engine ends successfully, leaves a usable client, leaves an engine at or above the declared minimum, and reports that version and that it was installed.
- **AC-2**: Starting the default installation with an engine already present at exactly the offered version ends successfully, leaves the engine installation unchanged, and reports the engine as kept with its version.
- **AC-3**: Starting the default installation with an engine present below the offered version ends successfully, leaves the strictly newer offered engine in place, and reports it as replaced.
- **AC-4**: Starting the default installation with an engine present above the offered version and at or above the declared minimum ends successfully, leaves the engine installation unchanged, and reports the engine as kept.
- **AC-5**: When the offered version is below the declared minimum and no suitable engine is present, the installation ends as a failure whose message names the required minimum, the version found or offered, and the action the user can take.
- **AC-6**: When obtaining the engine fails, the installation ends as a failure with a message naming what went wrong and the next action, and never reports the pair as installed.
- **AC-7**: Choosing the documented client-only installation installs the client, performs no engine version query, and leaves an engine present beforehand unchanged.
- **AC-8**: Running the default installation twice in a row leaves exactly one client installation and one startup entry, and the second run does not change the engine the first run left.
- **AC-9**: Versions differing only by a leading version prefix or by trailing zero components are treated as the same version, and a version that cannot be ordered never satisfies the minimum.
- **AC-10**: Removing a client installed with an engine leaves the engine in place and leaves no client artifacts behind.
- **AC-11**: The documentation presents the default installation as producing a working client alongside a supported engine, states that the engine version in place and how it was obtained are reported, and describes what a successful installation reports.
- **AC-12**: The documentation states that an absent engine is obtained, that a present engine is kept when the offered version is not strictly newer, that a strictly newer offered engine replaces it, and that the finished state always satisfies the declared minimum or the installation fails with an actionable message naming the minimum and the version found or offered.
- **AC-13**: The documentation documents the client-only installation, the engine source with its default and how to point it elsewhere, and the option that keeps the user's startup configuration unchanged; it no longer instructs the user to supply an engine separately for the default installation.
- **AC-14**: The automated checks contain no check that reads documentation text, and no automated check of documentation text replaces the removed one.
- **AC-15**: All other automated checks run unchanged and pass, and installer and client behavior outside the combined installation is unchanged.
- **AC-16**: The installation instructions are accepted or returned solely by review of their text; a passing or failing verdict on their wording comes from a person reading them, never from an automated check.

## Scope Boundaries

- The default client installation also ensures a supported engine is in place beside the client
- Deciding between obtaining an engine, keeping the present one and replacing it with a strictly newer one
- Enforcing the client's declared minimum supported engine version at the end of the installation
- A failure report naming the required minimum, the version found or offered, and the user action
- A success report naming the engine version in place and how it was obtained
- A documented client-only installation that leaves any engine untouched and unqueried
- The engine source as documented configuration with a documented way to point it elsewhere
- User documentation of the combined default installation, the client-only installation and the engine source
- Automated coverage of the combined installation against a deterministic stand-in for the engine's installation facility
- Removal of the automated check that reads the documentation text, together with the supporting data that reproduces that text
- Building or changing the engine's own installation facility
- Uninstalling or downgrading an engine
- Changing the client's startup check of the engine version
- Changing any client request or its output
- Changing the client's installation location, launcher, startup entry, fresh-session verification or removal behavior beyond what the engine decision needs
- Removing the replaced chat mode from the engine
- Installation on Windows
- Managing engine credentials, projects or model configuration
- Adding any automated check of the documentation text in place of the removed one
- Changing, weakening or removing any other check, or changing installer and client behavior outside the combined installation

## Risks

- The engine project may not yet provide an installation facility with the reporting and installation behavior this task relies on, in which case the default installation always fails and the milestone goal is not met.
- A deterministic stand-in for the engine's installation facility is not proof of the real one; if the real facility reports or installs differently, the combined installation fails outside the automated checks even though the checks pass.
- The default engine source is remote, so the automated checks cannot reach it and can only exercise the decision logic through the stand-in; the real dependency must be confirmed on a connected machine before this can be trusted.
- Careless version ordering could treat a pre-release or non-numeric version as satisfying or exceeding the minimum and silently leave an unsupported engine in place.
- Failing the installation after the client is already installed can leave a user with a client and no usable engine unless the failure message is unambiguous about the state and the next action.
- Extending the installation risks regressing the existing startup-entry, fresh-session verification and removal behavior that current coverage protects.
- Documenting the combined installation before the behavior exists would mislead users; the documentation and the behavior must change together.
- With the automated documentation check gone, drift between the documented installation instructions and the installer is caught only by reading the text, so a wrong instruction can reach users if that review is superficial.

## Open Questions

- None.

## Assumptions

- Removing the client leaves the engine in place, because the engine's lifecycle belongs to the engine and may be shared with other tools; this is recorded rather than asked.
- The offered version is whatever the configured engine source provides, as reported by the engine's own installation facility without installing anything.
- An engine whose version cannot be ordered is treated as not satisfying the minimum, and the installation falls through to the obtain-or-replace decision.
- The engine's own installation facility is taken from the machine unless the installation is pointed elsewhere, and the default engine source is the engine project's public source.
- The client-only installation is a positive choice; leaving the user's startup configuration unchanged still performs the engine part of the installation.
- When the installation fails after the client part already succeeded, the client installation stays in place and the message makes the state of the pair and the next action clear.
- Failed and successful installations are told apart by the outcome and by a message that names the minimum, the version and the action, while the success report instead states the version and how it was obtained.
- The engine's own installation facility is produced by the engine project in this same product, so its behavior is a contract between two parts of one product rather than a third-party service; its real behavior is exercised by the engine project's own checks, and this task verifies the client's decisions against a deterministic stand-in.
- The removed documentation check is not replaced by any other automated check of documentation text, and the installation instructions themselves are otherwise unchanged in what they must say.

## Related Documents

- README.md
- CHANGELOG.md
- releases/0.2.0/plan.md

## Revision History

- 1.0 — initial specification for the combined engine and client installation
- 1.1 — removed implementation detail from constraints and assumptions and moved environment-specific detail into the dependency record
- 1.2 — treated the task as documentation only; incorrect, because the task changes installation behavior
- 1.3 — restored behavior requirements and acceptance with executable checks in this repository, kept documentation criteria as review-only, and recorded the engine project's installation facility as an in-product contract rather than an external service
- 1.4 — removed the automated check that reads the documentation text together with the supporting data that reproduces that text, added no replacement automated documentation check, made the installation instructions review-only, and recorded that no other check is removed or weakened and that installer and client behavior outside the combined installation is unchanged
- 1.5 — removed implementation wording from the constraints and requirements; the language rule is stated as a plain artifact-language constraint without process steps
