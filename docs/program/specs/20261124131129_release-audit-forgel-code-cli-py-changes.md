# Task Spec: Release audit: `forgel_code/cli.py` changes the argparse description to include `Run it without

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `forgel_code/cli.py` changes the argparse description to include `Run it without |
| Project | — |
| Task | `20261124131129_release-audit-forgel-code-cli-py-changes` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T13:11:45+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit found that the interactive-client change also altered the wording of the command line program's description, so the help output of the existing non-interactive usage differs from the previous release. The task's requirements and acceptance promise that every existing one-shot usage keeps its previous output, and the review claim that help output is unchanged is contradicted by the actual change. The release record is therefore inconsistent with the shipped behavior.

**Outcome:** The help output of the published command line program is identical to the previous release: the interactive-session advertising sentence is gone and no other wording of the description changed. The interactive session itself is still reachable by running the program with no command, and all previously supported one-shot usages behave and print exactly as before. The release record no longer claims a help-output change that did not happen, and no automated test asserts the removed sentence.

## Product Intent

Forgel Code is a thin interactive client over the engine's parameterized commands, and it must not disturb the stability of the engine-side command line that existing users and scripts depend on. Adding the interactive client must not change what existing non-interactive usage prints.

## User Experience

A user who runs the program's help sees exactly the same text as in the previous release, with no new sentence about an interactive session. A user who runs the program with no command still enters the interactive session. Scripts and users relying on any one-shot usage see byte-identical output to the previous release.

## Roadmap

—

## Goals

- Make the command line program's help output identical to the previous release while keeping the interactive session available with no command.
- Resolve the release audit finding so the release record is consistent with the shipped behavior.

## Non-Goals

- Removing or changing the interactive session itself.
- Adding new options, subcommands, flags or aliases to the command line program.
- Changing the output of any other existing usage, including error messages, version output and one-shot command results.
- Adding help text, documentation pages or discoverability affordances for the interactive session.
- Changing the engine, the client's other behavior, packaging or release versioning.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | User decision log D-002 |
| — | The base parameterized command line stays in the engine; the separate client replaces the interactive chat mode. | User decision log D-003 |
| — | The client's working name is Forgel Code, a Python client installed as a separate command, following a Pareto 20/80 scope and importing nothing from the engine. | User decision log D-004 |
| — | Work proceeds in order: machine-readable engine commands first, then the client repository and console move, then removal of the replaced chat mode from the engine. | User decision log D-006 |

## Functional Requirements

- **FR-1**: The help output of the command line program contains the same description text as the previous release, with no added sentence about an interactive session and no other wording change.
- **FR-2**: Running the command line program with no command still opens the interactive session.
- **FR-3**: Every existing one-shot usage produces the same output as in the previous release, including successful runs, failure messages and exit statuses.
- **FR-4**: No automated test asserts the presence of the removed interactive-session sentence in the help output.
- **FR-5**: The change set contains no unrelated, temporary or generated files.

## User Stories

- As a user of the existing command line, I want the help output to stay exactly as before, so that my scripts and habits are not broken by the new interactive client.
- As a user of the interactive client, I want running the program with no command to still open the session, so that I can work interactively.
- As a release auditor, I want the shipped behavior to match the recorded acceptance, so that the release record is trustworthy.

## Acceptance Criteria

- **AC-1**: The help output of the command line program no longer contains the sentence advertising the interactive session.
- **AC-2**: The help output's description text is identical to the previous release, confirmed by comparison with the previously released text and by review that no other wording was touched.
- **AC-3**: Running the program with no command still opens the interactive session.
- **AC-4**: All tests in the project's test suite pass.
- **AC-5**: The change set contains only the restoration of the description wording and any test adjustment needed by it.

## Scope Boundaries

- Restore the program description used in the help output to its exact previous-release wording.
- Remove the sentence advertising the interactive session from that description.
- Keep the interactive session available when the program is invoked with no command.
- Keep every other existing one-shot usage's output unchanged.
- Bring any test that asserts the removed sentence in line with the restored help output.
- Removing or changing the interactive session itself.
- Adding new options, subcommands, flags or aliases to the command line program.
- Changing the output of any other existing usage, including error messages, version output and one-shot command results.
- Adding help text, documentation pages or discoverability affordances for the interactive session.
- Changing the engine, the client's other behavior, packaging or release versioning.

## Risks

- The previous description text may not be exactly recoverable, in which case an approximation would still change the help output and fail the promise of unchanged output.
- Other help-visible content (option descriptions, ordering) may have changed in the same edit without being noticed, so the help output could still differ from the previous release.
- Adjusting a test that asserts the added sentence could be mistaken for weakening a test and be rejected in review.
- If the milestone's user-facing intent was to advertise the interactive session, silently restoring the text hides the feature; that trade-off is accepted by the recorded requirement but should be visible in the report.

## Open Questions

- None.

## Assumptions

- The correct resolution is to restore the previous help text rather than to relax the requirement that existing usage output stays unchanged, because the recorded acceptance treats unchanged output as the promise and the review statement as the defect.
- Discoverability of the interactive session outside the help output is out of scope for this task; the session remains reachable by running the program with no command.
- The previously released description text is recoverable from the repository history of the command line program's description, so an exact restoration is possible.
- If any test currently asserts the added sentence, adjusting that assertion to the restored output is part of this task and does not count as weakening a test.

## Related Documents

- forgel_code/cli.py
- tests/test_cli.py
- releases/0.1.1/release.md
- CHANGELOG.md

## Revision History

- v1: initial specification resolving the release audit finding that the help output changed.
