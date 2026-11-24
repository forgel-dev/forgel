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
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The engine knows its own version only as human-readable text, so an installer or the Forgel Code client cannot reliably read and compare the installed engine version against another version without parsing prose. This blocks the later version-comparison and startup-check work.

**Outcome:** On request the engine reports its own version as stable machine-readable output that a program can read and order-compare directly, without a project, a session, a model, a sandbox or a network connection; the value agrees with the version the engine declares elsewhere, and every existing human-readable report is unchanged.

## Product Intent

Forgel (the engine) and Forgel Code (the client) must install and run as one working pair: the pair needs a trustworthy way to compare engine versions so the client can refuse a too-old engine and the combined installer can decide whether an installed engine is worth replacing.

## User Experience

A person installing or updating the pair never has to read a version string out of prose: the installer and the client obtain the engine's version as data, compare it, and act on the comparison, so the eventual messages about a missing or out-of-date engine are actionable rather than an unexplained failure.

## Roadmap

—

## Goals

- Give the engine a stable machine-readable version report that a program, not a human, consumes.
- Keep the reported version identical to the version the engine already declares and shows.
- Make the report usable off a fresh machine, with no configuration, project or network.

## Non-Goals

- Installing anything, including the engine installer.
- Comparing two engine versions or enforcing a minimum engine version.
- Any change in the client repository, the combined install mode or the startup check.
- Changing the declared version value, tagging, releasing or promising a release version.
- Adding new machine-readable reports for commands other than the version.
- Changing the existing human-readable output of any command.
- Documentation work beyond what the changed behaviour requires.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The base parameterized command line (`forgel <command>`) stays in the engine. | D-003, user 2026-11-16 18:31 |
| — | The single free-text engine entry point is free-text `say`; every client-facing operation is a parameterized command with an optional single JSON object on stdout; the active project is an engine-side session with the default key `local`. | D-007, user 2026-11-16 18:34 |
| — | The work happens in order: machine-readable engine commands first, then the client repository, then removal of the replaced chat mode from the engine. | D-006, user 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: On request the engine reports its own version in a machine-readable form and exits successfully.
- **FR-2**: The machine-readable form is a single JSON object on standard output, in the same convention the engine's other client-facing commands use, and standard output carries no other content.
- **FR-3**: On a successful report nothing is written to standard error and nothing is written to the user's project, home or working tree.
- **FR-4**: The machine-readable report is obtainable in an otherwise unconfigured environment with no project, no session, no model access, no sandbox and no network, and succeeds there.
- **FR-5**: The version value carried by the machine-readable report is identical to the version the engine declares for itself and to the version shown by the human-readable reports; the task makes these agree and does not change the declared value.
- **FR-6**: The version value is a dotted sequence of at least three non-negative integers, optionally followed by a pre-release or build suffix, so that two engine versions can be ordered by their numeric components alone.
- **FR-7**: The machine-readable report names the engine whose version it is, so a reader cannot mistake a client version for an engine version.
- **FR-8**: Asking for the version the human-readable way continues to work and shows the same version value as before this change.
- **FR-9**: The report is repeatable: two consecutive requests in the same environment produce the same version value, and the second one behaves identically to the first.
- **FR-10**: The report needs no new third-party dependency.

## User Stories

- As the Forgel Code installer or client, I want to obtain the engine's version as data, so that I can compare versions without parsing prose.
- As a maintainer, I want one source of truth for the version, so that the human-readable and machine-readable reports never disagree.
- As an operator on a fresh machine, I want the version report to work before anything is configured, so that install and diagnosis do not depend on project state.

## Acceptance Criteria

- **AC-1**: A single request to the engine for its version in machine-readable form yields one JSON object on standard output, parseable without preprocessing, with nothing else emitted on standard output, nothing on standard error, and a successful exit status.
- **AC-2**: A reader taking the version value from that object obtains the same string as the engine's own declared version and as the human-readable version report.
- **AC-3**: The version value splits into at least three numeric components and can be ordered against another value of the same shape without reading prose.
- **AC-4**: The same request run in a clean environment with no project, no session, no model configuration and no network access still yields the version report and succeeds.
- **AC-5**: After the request, no file was created or modified in the working directory, the project artifacts or the user's Forgel home.
- **AC-6**: The existing human-readable version output is unchanged in content and exit status.
- **AC-7**: Automated tests exercise the machine-readable report's shape, its value agreement and its availability without configuration; the project test suite passes.

## Scope Boundaries

- A stable machine-readable report of the engine's own version, produced on request.
- The reported version agrees with the version the engine declares for itself and with what the human-readable reports show.
- The report is available in a fresh, unconfigured environment and needs no project, session, model, sandbox, ledger content or network access.
- The report writes nothing to the user's project, home or working tree and produces no partial or duplicated output.
- Automated coverage of the machine-readable report's shape and value.
- Installing anything, including the engine installer.
- Comparing two engine versions or enforcing a minimum engine version.
- Any change in the client repository, the combined install mode or the startup check.
- Changing the declared version value, tagging, releasing or promising a release version.
- Adding new machine-readable reports for commands other than the version.
- Changing the existing human-readable output of any command.
- Documentation work beyond what the changed behaviour requires.

## Risks

- The machine-readable report may be built from a second version literal that drifts from the declared one, making the installer's comparison wrong; the single-source requirement and its acceptance criterion guard against this.
- The engine has no published tag yet, so a consumer cannot rely on a released version string; this task makes the local report reliable and does not solve the distribution question, which belongs to the installer tasks.
- The request could accidentally take the configured startup path and fail in a clean environment; the acceptance criterion for the clean environment exposes this.
- If the machine-readable variant is added without keeping the existing human-readable output intact, installed scripts that grep the old text break.
- A version suffix convention beyond dotted integers could make ordering ambiguous for a client that assumes plain numeric components; this is recorded as an assumption and left to the comparison tasks.

## Open Questions

- None.

## Assumptions

- The machine-readable form is requested by the same flag convention the engine already uses for its other client-facing commands, so the version report has a machine-readable variant of the version request rather than a new top-level command family.
- The version is carried as the value of a top-level member named "version" inside the single JSON object, and the object also carries a success indication and the identity of the engine; the remaining members follow the existing client-facing shape.
- The request is served by the installed engine binary itself, not by a separate helper program.
- The existing human-readable version output is already produced by the engine and only needs to stay unchanged.
- Version ordering is by numeric components; suffix handling beyond treating a suffixed version as ordered relative to its unsuffixed core is left for the tasks that compare versions.

## Related Documents

- README.md
- pyproject.toml
- FORGEL.md
- AGENTS.md

## Revision History

- 1 — initial specification for emitting a machine-readable engine version.
