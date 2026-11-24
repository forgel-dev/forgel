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
| Created | 2026-11-24T16:29:14+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

A user who follows the documented Forgel Code installation ends up with the client but no engine, or with an engine the client does not support, so the first interaction fails with an engine-not-found error instead of opening a session. The installation brings the client into place but not the engine it depends on, and the documented one-command installation still describes the client-only behaviour of an earlier release while implying the engine is the user's separate problem.

**Outcome:** The single documented one-command installation yields a working pair: the client is installed and an engine the client supports is in place. The run is safe to repeat — it installs an engine when none is present, keeps an installed engine that is at or above the version the configured engine source provides, replaces an engine only with a strictly newer one, and never finishes successfully unless the engine it leaves behind meets the client's declared minimum supported version. When it cannot reach that state it stops with a message that names the required minimum, the version it found and the action the user can take. Installing only the client remains available as a documented secondary route that never touches an engine.

## Product Intent

Forgel and Forgel Code must install and run as one working pair. The client stays a thin UI over the engine, so the engine is not optional for a usable installation; installing the pair is the product's front door and must not require the user to discover and install a second component by hand.

## User Experience

A user copies one documented command and afterwards both the client and a supported engine are present, with the run stating which engine version is in use and how it was obtained — installed, kept or replaced. Re-running the same command after an update keeps what is already good and replaces only what is out of date. If the pair cannot be completed, the user reads why — the required engine version, the version actually found, and the next step to take — instead of an opaque missing-executable error. A user who already has an engine, or who wants only the client, uses the documented client-only route and no engine is touched. Uninstalling removes the client and leaves the engine in place.

## Roadmap

—

## Goals

- One documented command installs a working client and engine pair
- The engine part of the installation is idempotent and never downgrades an installed engine
- The installation never finishes successfully with an engine below the declared minimum
- A failure tells the user the required minimum, the version found and what to do next
- The user can still install only the client through a documented secondary route
- The documentation describes the delivered behaviour and keeps every existing installation-documentation standard fully in force

## Non-Goals

- Defining or implementing the client's startup check of the minimum supported engine version (a separate task); this task only requires that the installation leaves an engine satisfying that same declared minimum
- Changing the engine's own installation mechanism, its version report or the way it installs a version
- Removing an engine during uninstall
- Changing any client command, session behaviour or machine-readable output
- Supporting Windows as a main installation path
- Selecting, promising or publishing a release version or tag

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The interactive client lives in its own public repository in the same organization as the engine, so installing the client reaches the engine through the engine project's own installation mechanism. | D-001, D-005 |
| — | The client is a thin UI over the engine's parameterized commands and does not call the model, read project files or run checks itself; model access, the sandbox, QA, review and release approval stay in the engine. | D-002 |
| — | The client's working name is Forgel Code, following a Pareto 20/80 scope and depending on nothing inside the engine. | D-004 |
| — | The work proceeds in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | D-006 |

## Functional Requirements

- **FR-1**: Running the client installation with no mode selection installs the client and, in the same run, brings an engine the client supports into place.
- **FR-2**: The engine source used by the run is a configuration with a documented default; when the configuration is unset the project's own public engine source is used.
- **FR-3**: The run determines, without installing anything, which engine version the configured engine source provides, and determines which version of an engine is already in place if one is.
- **FR-4**: When no engine is in place, the run installs the available engine.
- **FR-5**: When an engine is in place at a version equal to or above the available one and satisfies the declared minimum, the run keeps it untouched and reports it as kept.
- **FR-6**: When the available version is strictly newer than the engine in place, the run replaces it with the available version.
- **FR-7**: A successful run never leaves an engine below the client's declared minimum supported engine version.
- **FR-8**: When the finished state cannot satisfy the declared minimum, the run exits with a non-zero status and prints one message that names the required minimum, the engine version found and the action the user can take.
- **FR-9**: A successful run states the engine version left in place and how it was obtained: installed, kept or replaced.
- **FR-10**: The client installation has a mode that installs the client alone; in that mode it never installs, replaces or otherwise touches an engine and succeeds whether or not an engine or the engine project's installation mechanism is available.
- **FR-11**: When the engine project's installation mechanism cannot be found or fails, a default run exits with a non-zero status and an actionable message that names the client-only mode as the way to proceed without an engine, rather than silently installing only the client.
- **FR-12**: Uninstalling removes the client installation and its path entry and leaves any installed engine in place.
- **FR-13**: Re-running the default installation is idempotent: the client installation is replaced rather than duplicated, exactly one path entry remains, and an engine that is kept is not reinstalled.
- **FR-14**: The declared minimum supported engine version has exactly one source, which both the installation and the client's startup check honour.
- **FR-15**: Two engine versions are ordered numerically component by component; one leading version marker and trailing zero components do not affect the comparison; a version that cannot be ordered numerically is treated as not satisfying the minimum.
- **FR-16**: The installation's own usage text describes the combined mode as the default, the client-only mode, and the engine source with its default.
- **FR-17**: The user documentation presents exactly one one-command installation as the main path, and that path installs the client and the engine together.
- **FR-18**: The one-command installation the documentation presents is served by the release of this project that contains the combined mode, not by an earlier release that installed the client alone; the update and uninstall instructions name the same release location.
- **FR-19**: The documentation shows how to install only the client, states that this route touches no engine and that the user then supplies an engine meeting the declared minimum, and states that uninstalling leaves the engine in place.
- **FR-20**: The documentation states the engine source default and how to point the run at another engine source, states that an already installed supported engine is kept and a strictly older one replaced, and states that the run reports the engine version it leaves in place.
- **FR-21**: The documentation no longer tells the user that a working engine must already be present before the one-command installation.
- **FR-22**: The project's existing installation-documentation standards keep their full strength: the main path is still led by the one-command installation, the update and uninstall routes are still documented, exactly one current-release location is named, no alternative main installation route is introduced, and no editable installation is proposed. Any disagreement with those standards is resolved by bringing the documentation in line with the delivered behaviour, never by dropping, loosening or rephrasing a standard into a weaker one; the only change permitted to the documented current-release location is its advance to the release that carries the combined mode.
- **FR-23**: The changelog records the combined installation, the client-only mode, the keep/replace behaviour and the reported engine version.

## User Stories

- As a new user I want one documented command to give me both the client and a supported engine, so that my first interaction works instead of failing with a missing engine.
- As a returning user I want to re-run the same command after an update so that my already supported engine is left alone and only a strictly newer one replaces it.
- As a user who already maintains an engine I want a documented way to install only the client so that my engine is never touched.
- As a user whose installation cannot be completed I want the failure to tell me the required engine version, the version found and what to do next, so that I can fix it without guessing.
- As a user reading the documentation I want to be told which engine version the installation leaves in place, where the engine comes from and that uninstalling keeps it, so that I know what is on my machine.

## Acceptance Criteria

- **AC-1**: On a machine with no engine, a default run against a configured engine source that provides a supported version leaves an installed client and an installed engine at that version, and reports the version and that it was installed.
- **AC-2**: On a machine whose engine is at or above the available version and satisfies the minimum, a default run leaves the installed engine untouched and reports it as kept.
- **AC-3**: On a machine whose engine is older than the available version, a default run replaces it and reports the new version as installed.
- **AC-4**: When the run cannot leave an engine meeting the declared minimum, it exits non-zero and its single message names the required minimum, the version found and the action the user can take.
- **AC-5**: A client-only run succeeds with no engine and no engine installation mechanism available, installs the client, and leaves an engine that is present unchanged.
- **AC-6**: A default run with no engine installation mechanism available exits non-zero with a message that names the client-only route as the way to proceed.
- **AC-7**: Running the default installation twice leaves the kept engine unchanged and exactly one path entry in the profile.
- **AC-8**: Engine versions that differ only by a leading marker or trailing zero components compare equal, a strictly newer available version wins, and a non-numeric version never satisfies the minimum.
- **AC-9**: Uninstalling removes the client installation and its path entry and leaves the installed engine in place.
- **AC-10**: The installation's usage text describes the combined default, the client-only mode and the engine source default.
- **AC-11**: The documentation's single main one-command installation installs the client and the engine together.
- **AC-12**: The documentation shows how to install only the client and says that route touches no engine.
- **AC-13**: The documentation names the default engine source and its override, the keep-supported and replace-strictly-older behaviour, the reported engine version and the fact that uninstalling keeps the engine; it no longer requires a pre-installed engine for the one-command installation.
- **AC-14**: The documented installation, update and uninstall instructions all name the release that carries the combined mode, and no earlier release that installed the client alone is named.
- **AC-15**: No existing installation-documentation standard has been dropped, loosened or rephrased into a weaker one; the only change to the documented current-release location is its advance to the release carrying the combined mode.
- **AC-16**: The changelog records the combined installation, the client-only mode, the comparison behaviour and the reported engine version.
- **AC-17**: The whole test suite passes, including the existing installation and packaging expectations.

## Scope Boundaries

- The default run of the client installation brings an engine the client supports into place together with the client
- Deciding what to do with the engine by comparing the version an already installed engine reports against the version the configured engine source provides
- A configurable engine source with a documented default
- A successful run reporting the engine version in place and how it was obtained
- An actionable failure when the finished state cannot satisfy the client's declared minimum supported engine version
- A client-only mode of the same installation that installs the client and leaves any engine untouched
- The installation's own usage text describing the combined and client-only modes and the engine source
- User documentation: the one-command combined installation as the main path, the client-only route, the engine source default and override, the keep/replace behaviour, the reported engine version and the fact that uninstalling keeps the engine
- The changelog entry describing the combined installation
- Defining or implementing the client's startup check of the minimum supported engine version (a separate task); this task only requires that the installation leaves an engine satisfying that same declared minimum
- Changing the engine's own installation mechanism, its version report or the way it installs a version
- Removing an engine during uninstall
- Changing any client command, session behaviour or machine-readable output
- Supporting Windows as a main installation path
- Selecting, promising or publishing a release version or tag

## Risks

- The release identifier the documentation must name is decided by the project's release process, so a change merged before that release names a location that is not yet published; the documented location must advance together with the release, and the milestone's release step must publish the combined installation at exactly that location.
- Failing to advance the documented current-release location consistently leaves either the documentation describing the earlier client-only installation or documentation that the project's standards reject.
- Loosening the project's existing documentation standards so the new text passes would weaken a project expectation; this specification forbids it explicitly.
- A default run that now fails when the engine project's installation mechanism is missing could break users who previously installed the client alone; the actionable message that names the client-only mode is the mitigation.
- The real engine installation mechanism may behave differently from the stand-in used during verification, so a passing suite is not proof of the real contract.
- If the engine is replaced while another client or process uses it, that other user is affected; the strict-newer rule bounds the change but does not eliminate it.

## Open Questions

- None.

## Assumptions

- The client already states its minimum supported engine version in one place, and this task uses that value rather than redefining it.
- The engine project's installation mechanism is delivered by a sibling task and offers exactly two abilities the run needs: reporting which version a source provides without installing anything, and installing a requested version.
- An installed engine answers a version query in a machine-readable form the run can read.
- Uninstalling keeps the engine in place, because an engine may serve several clients and removing it is the engine project's own decision.
- A run that cannot reach the engine project's installation mechanism fails actionably instead of degrading silently to a client-only installation.
- Version ordering ignores one leading marker and trailing zero components, so a release tag and a plain version denoting the same release compare equal; a version that is not a sequence of numeric components satisfies no minimum.
- This change is published in the next release of this project, so the documentation and the documented current-release location advance to that release; the release process, not the developer, decides the release identifier.
- The project keeps its existing documentation standards as they are and only advances the notion of the current release.
- Documentation content is judged by review; no new automated check that reads a documentation file is introduced.

## Related Documents

- README.md
- CHANGELOG.md

## Revision History

- v1 initial specification of the combined installation mode
- v2 rewritten after the rejected version: the user-facing installation documentation is now in scope; the single documented installation command must be the combined client-and-engine command, the documentation must show how to install only the client, it must name the release that carries the combined mode instead of an earlier client-only one, and any disagreement with the existing installation-documentation standards is resolved by correcting the documentation while keeping every standard at full strength.
- v3 removed remaining implementation wording from the behavioural fields; every command check now runs inside the client repository and the documentation criteria are judged by review only.
