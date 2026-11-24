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
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

Installing Forgel Code today yields a client without an engine, so the first run fails with a bare execution error. A user who wants a working pair must find, install and version-match the engine themselves, and nothing states which engine version the client needs. The client's installation path handles only the client, and it cannot tell whether the engine already present is good enough.

**Outcome:** Installing Forgel Code with no extra options installs the client and, when needed, an engine, so one documented command produces a working pair. The installation learns which engine version the configured engine source provides without installing it, compares that with the engine already present, installs nothing when the present engine is good enough, replaces a strictly older engine with a newer available one, and never finishes with an engine below the client's declared minimum supported engine version. When it cannot reach that end state it ends as a failure and says what is wrong, which version is required, which version was found and what the user can do, and every successful run states which engine version is in place and how it got there.

## Product Intent

Forgel and Forgel Code are one product pair: the client is a thin UI over the engine's parameterized commands, so a client without a usable engine is not a product. The installation must deliver a working pair in one step, stay safe to repeat, and turn a version mismatch into a self-explanatory message instead of a raw execution error.

## User Experience

A new user runs the single documented installation command and ends with both the client and the engine, then uses the client successfully. A returning user runs the same command again: if the engine present is at or above the available version it is left exactly as it was, and if a strictly newer engine exists it is picked up. A user whose engine is too old, or whose configured engine source cannot supply a satisfying engine, is told which engine version is required, which version was found and what to do about it, instead of seeing an execution error. A user who manages the engine themselves can install only the client.

## Roadmap

—

## Goals

- One documented installation command yields a working client and engine pair.
- The engine decision is repeat-safe and rests on the available engine version determined before installing.
- No successful run ever leaves an engine below the client's declared minimum supported engine version.
- A missing, too-old or unobtainable engine produces a clear, actionable message naming the required version and the action.
- The run tells the user which engine version it ended with and how it got there.

## Non-Goals

- Implementing the engine's own installer or its version reporting; that belongs to the engine
- The client's startup check of the minimum supported engine version; a separate task covers it
- Rewriting the client's user documentation or changelog; separate documentation tasks cover them
- Publishing an engine release or choosing release versions
- Downgrading, uninstalling or repairing an engine that a user manages
- Changing what the client does after it starts, or how it finds the engine when it runs
- Installing any other companion tool, plugin or extension

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself, so it needs a working engine to be useful (D-002). | User decision log, D-002, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code, it installs as its own distribution, follows a Pareto scope and imports nothing from the engine (D-004). | User decision log, D-004, 2026-11-16 18:34 |
| — | The client is public and lives in the same organization as the engine (D-005), so the default installation must work from public sources without private access. | User decision log, D-005, 2026-11-16 21:14 |
| — | The work proceeds engine command line first, then the client and the console move (D-006); the engine side is therefore ahead of this client-side task. | User decision log, D-006, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: A run of the Forgel Code installation with no extra options installs the client and also ensures an engine is installed, so one command produces a working pair.
- **FR-2**: An explicit, documented option installs only the client and leaves any engine present untouched; it is not the default and it is not needed to obtain the pair.
- **FR-3**: Before deciding whether to install an engine, the run determines the engine version that the configured engine source provides, without installing it and without changing any engine that is already present.
- **FR-4**: The client declares one minimum supported engine version, and the installation enforces exactly that same minimum.
- **FR-5**: When no engine is present and the available engine version satisfies the declared minimum, the run installs that version.
- **FR-6**: When an engine is present, its version is at or above the available version, and it satisfies the declared minimum, the run installs no engine and leaves the present engine untouched.
- **FR-7**: When an engine is present and the available version is strictly newer than the present version and satisfies the declared minimum, the run replaces the present engine with the available version.
- **FR-8**: When the available version does not satisfy the declared minimum, the run installs no engine, keeps any present engine in place, ends as a failure, and reports the required minimum and the available version.
- **FR-9**: When a present engine is below the declared minimum and the available version is not strictly newer than it, the run keeps the present engine, does not place a lower version over it, ends as a failure, and reports the required minimum and the present version.
- **FR-10**: Every failure of the engine part of the run reports what is wrong, the required minimum engine version, the version that was available or present when known, and the concrete action the user can take to supply a satisfying engine.
- **FR-11**: Every successful run ends by reporting the engine version in place after the run and how it was obtained: newly installed, kept, or replaced.
- **FR-12**: Repeating the run against an unchanged engine source installs no engine after the first successful run and reports the same engine version.
- **FR-13**: The engine source and the location of the engine's own installer are configurable settings with documented project defaults, so a user can point the run at a different engine source.
- **FR-14**: When the engine source cannot be reached or the available version cannot be determined, the run installs no engine, leaves any present engine untouched, ends as a failure, and reports an actionable message.
- **FR-15**: When the engine installation itself fails, the run ends as a failure with an actionable message, and a client that was already installed remains installed and usable.
- **FR-16**: Version comparison follows the version ordering the project uses for its releases, ignores a leading version marker and trailing zero components, and treats a version it cannot parse as not satisfying the declared minimum.
- **FR-17**: An engine that is present but cannot report its version is treated the same as a missing engine.
- **FR-18**: A run is reported as successful only when its end state satisfies the declared minimum, or when the client-only option was used; every other end state is reported as a failure.
- **FR-19**: Everything the client installation did before this change keeps working: its options, its messages, its handling of the user's shell environment and its removal path.

## User Stories

- As a new user, I want the single documented installation command to give me both the client and the engine, so that my first client run works.
- As a returning user, I want re-running the installation to leave a good engine alone and only pick up a strictly newer one, so that installing is predictable.
- As a user with an outdated engine, I want the installation to tell me which engine version is required and what to do, so that I can fix it without reading source code.
- As a user who manages the engine myself, I want an option that installs only the client, so that the installation does not touch my setup.
- As a user whose engine source is unreachable, I want a clear failure that leaves my installation intact, so that I can retry knowingly.

## Acceptance Criteria

- **AC-1**: A run with no extra options against a source with no engine present ends successfully, leaves the client and the available engine installed, and states the engine version as newly installed.
- **AC-2**: A run with the client-only option installs no engine and states that no engine was installed.
- **AC-3**: Before any engine is installed, the run already knows the version the configured source provides, and the decision it makes matches that version.
- **AC-4**: With a present engine at or above the available version that satisfies the declared minimum, a run installs no engine and the present engine is unchanged afterwards.
- **AC-5**: With a present engine older than a strictly newer available version that satisfies the declared minimum, a run replaces it and states the newer version as the result.
- **AC-6**: With an available version below the declared minimum, the run installs no engine, ends as a failure, and its message contains the required minimum and the available version.
- **AC-7**: With a present engine below the declared minimum and no strictly newer available version, the run installs no engine, ends as a failure, and its message contains the required minimum and the present version.
- **AC-8**: Every failure message names the required minimum engine version and an action the user can take, so a reader can act without further investigation.
- **AC-9**: Running the no-option installation twice in a row against an unchanged source installs the engine only on the first run and states the same engine version both times.
- **AC-10**: Pointing the configurable engine source at a different source changes which engine version the run treats as available.
- **AC-11**: An unreachable engine source produces a failing outcome with an actionable message and does not disturb a present engine.
- **AC-12**: A failing engine installation produces a failing outcome with an actionable message while the client remains installed.
- **AC-13**: A present engine that cannot report its version is treated as missing and the run proceeds accordingly.
- **AC-14**: The behavior the client installation had before this change is preserved, including its existing options, its handling of the user's shell environment and its removal path.

## Scope Boundaries

- Installing the client and the engine together when the installation runs with no extra options
- Determining the engine version the configured engine source provides before deciding whether to install
- Comparing the engine present against the available engine version and against the client's declared minimum supported engine version
- Deciding per case whether to install, keep untouched, replace, or end as a failure with an actionable message
- Stating, at the end of a successful run, which engine version is in place and how it got there
- Making the engine source and the location of the engine's own installer configurable settings with project defaults
- An explicit documented option that installs only the client
- Automated coverage of every decision case and of the content of the messages
- Implementing the engine's own installer or its version reporting; that belongs to the engine
- The client's startup check of the minimum supported engine version; a separate task covers it
- Rewriting the client's user documentation or changelog; separate documentation tasks cover them
- Publishing an engine release or choosing release versions
- Downgrading, uninstalling or repairing an engine that a user manages
- Changing what the client does after it starts, or how it finds the engine when it runs
- Installing any other companion tool, plugin or extension

## Risks

- The engine's ability to report the version a configured source provides before installing belongs to separate work that is currently blocked; without it the client cannot decide without installing, and the goal of repeat-safe installation is missed.
- No released engine version exists yet, so the available version comes from configured sources whose declared version may be missing or stale; a run could then always fail the minimum check.
- The declared minimum is introduced on both sides of the pair; if its value or meaning diverges between installation and the client's startup, the two behave inconsistently.
- Replacing a present engine whenever a strictly newer version appears can overwrite an engine the user manages themselves; only the client-only option protects that case.
- Installing depends on reaching the engine source, so a restricted network turns the default installation into a failing outcome.
- The default meaning of the installation, the documented installation command and the client's startup check all move at once, so for a time the documentation can describe behavior that does not yet exist, or the reverse.
- Treating an engine that cannot report its version as missing may reinstall an engine that is actually healthy but damaged in its version reporting.
- An available version that satisfies the minimum can still fail while actually being installed, leaving a user who expected a pair with a failure and no engine.

## Open Questions

- None.

## Assumptions

- The engine's own installation can report the version its configured source provides without installing, and can install a requested available version; this task consumes that capability instead of reimplementing it.
- Installing the pair becomes the default behavior; a client-only path survives as an explicit documented option for users who manage the engine themselves.
- The client's declared minimum supported engine version is defined once by the client and shared by the installation and the future startup check; this task does not choose the value.
- A run that cannot reach a satisfying end state fails rather than finishing with an engine below the minimum, even when a usable engine is already present.
- A failing engine step does not roll back a client that was already installed.
- The client-only option is exempt from the minimum check during installation; the client's startup check covers that path.
- A version carrying a leading marker or trailing zero components compares equal to its normalized form.
- Reporting happens in the run's own output, without an extra option.
- The client's user documentation and changelog updates belong to separate documentation tasks, which make the combined installation the documented one.

## Related Documents

- README.md
- CHANGELOG.md
- install.sh
- pyproject.toml
- tests/test_install.py
- tests/test_readme_install.py
- releases/0.2.0/plan.md

## Revision History

- 1.0 — initial specification for the combined engine and client installation.
- 1.1 — removed process and repository mechanics from the constraints, restated acceptance as observable outcomes only, and dropped the acceptance item about a test run in favor of a preserved-behavior criterion.
