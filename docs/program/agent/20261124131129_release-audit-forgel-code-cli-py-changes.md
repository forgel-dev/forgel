# Agent Run: Release audit: `forgel_code/cli.py` changes the argparse description to include `Run it without

- Task: `20261124131129_release-audit-forgel-code-cli-py-changes`
- Status: `done`
- Repository: `code`
- Steps: 38
- Finished: 2026-11-24T13:27:51+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The previous-release description is recoverable from repository history (`5db4519` shows the pre-change text), so it was restored verbatim rather than approximated.
- No existing test asserted the removed interactive-session sentence, so no test adjustment was required; a new test pinning the restored description and the absence of the sentence was added instead.
- The module docstring in `forgel_code/cli.py` and the README's interactive-session section were left unchanged: the requirement covers the command line help output, and the interactive session must still be reachable with no command.
- Files were left for the runtime to commit; only the two files named here are part of this change set.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 38
- Estimated input tokens (all calls): 1822344
- Provider input/output tokens: 1926636 / 41261
- Provider cache hit/miss tokens: 1851648 / 74988
- Estimated prompt at the end: 71966 tokens
- State: not needed

## Specification (`docs/program/specs/20261124131129_release-audit-forgel-code-cli-py-changes.md`)

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


## Summary

Restored the argparse description in `forgel_code/cli.py` to the previous release's exact wording (`Thin console client for Forgel over the engine's machine-readable commands.`) by dropping only the added sentence `Run it without a command to open the interactive session.` Nothing else in the file, the parser, the commands, the fall-through into the interactive session on an empty argv, or the one-shot output/exit-status paths was touched. Added `tests/test_cli_help_description.py`, which pins the released description text in the parser and in `--help` (both in-process and as a real `python -m forgel_code --help` process) and asserts the help output no longer mentions the interactive session; no existing test asserted the removed sentence, so none was weakened or deleted. Verified with `git diff forgel_code/cli.py` (single-line description change), `python -m forgel_code --help` (prints the released description, no interactive sentence), and the full suite `python -m pytest`: 382 passed.

## Files Changed

- `forgel_code/cli.py`
- `tests/test_cli_help_description.py`

## Commands

- `["git", "log", "--oneline", "-n", "15", "--", "forgel_code/cli.py"]` → exit 0
- `["git", "show", "5db4519", "--", "forgel_code/cli.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "--ignore=tests/test_install.py", "--ignore=tests/test_install_timeout_verdict.py", "--ignore=tests/test_extras.py", "--ignore=tests/test_packaging.py", "--ignore=tests/test_packaging_types.py"]` → exit 0
- `["python", "-m", "pytest"]` → exit 0
- `["python", "-m", "forgel_code", "--help"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["python", "-m", "pytest", "tests/test_cli_help_description.py", "tests/test_cli.py", "-q"]` → exit 0
- `["python", "-m", "pytest", "tests/test_cli.py", "tests/test_cli_extra.py", "tests/test_interactive.py", "tests/test_stub_contract.py", "-q"]` → exit 0
- `["python", "-m", "pytest"]` → exit 0
- `["git", "status", "--short", "--untracked-files=all"]` → exit 0
- `["git", "diff", "--", "forgel_code/cli.py"]` → exit 0
- `["python", "-m", "pytest"]` → exit 0

## Final Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/okalistratov/Documents/sites/code
configfile: pyproject.toml
collected 382 items

tests/test_check_cleanup.py ..                                           [  0%]
tests/test_cli.py ...................................................... [ 14%]
.................                                                        [ 19%]
tests/test_cli_extra.py .........                                        [ 21%]
tests/test_cli_help_description.py ....                                  [ 22%]
tests/test_extras.py ......................                              [ 28%]
tests/test_idle_refresh.py ....                                          [ 29%]
tests/test_install.py .................................................. [ 42%]
......                                                                   [ 43%]
tests/test_install_timeout_verdict.py ....                               [ 45%]
tests/test_interactive.py .....................................          [ 54%]
tests/test_localization.py ..........................                    [ 61%]
tests/test_packaging.py ..............                                   [ 65%]
tests/test_packaging_types.py ..                                         [ 65%]
tests/test_readme_install.py ..................................          [ 74%]
tests/test_redact.py ..................................                  [ 83%]
tests/test_redact_descriptor.py ..........                               [ 86%]
tests/test_redact_french_joined.py .........                             [ 88%]
tests/test_redact_french_spanish.py ........................             [ 94%]
tests/test_redact_quoted_bare.py ..........                              [ 97%]
tests/test_retained_text.py ......                                       [ 98%]
tests/test_stub_contract.py ....                                         [100%]

======================= 382 passed in 197.34s (0:03:17) ========================

```

## Actions

- read_file: forgel_code/cli.py
- read_file: forgel_code/cli.py
- read_file: tests/test_cli.py
- read_file: releases/0.1.1/release.md
- read_file: CHANGELOG.md
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_interactive.py
- read_file: tests/test_cli_extra.py
- read_file: tests/test_extras.py
- read_file: tests/test_packaging.py
- read_file: tests/test_interactive.py
- run: ['git', 'log', '--oneline', '-n', '15', '--', 'forgel_code/cli.py']
- run: ['git', 'show', '5db4519', '--', 'forgel_code/cli.py']
- write_file: forgel_code/cli.py
- write_file: forgel_code/cli.py
- run: ['python', '-m', 'pytest', '-q', '--ignore=tests/test_install.py', '--ignore=tests/test_install_timeout_verdict.py', '--ignore=tests/test_extras.py', '--ignore=tests/test_packaging.py', '--ignore=tests/test_packaging_types.py']
- run: ['python', '-m', 'pytest']
- run: ['python', '-m', 'forgel_code', '--help']
- run: ['git', 'grep', '-n', 'Run it without a command']
- read_file: README.md
- write_file: tests/test_cli.py
- run: ['git', 'status', '--short']
- run: ['git', 'checkout', '--', 'tests/test_cli.py']
- write_file: tests/test_cli.py
- run: ['git', 'diff', '--stat']
- read_file: tests/test_cli.py
- run: ['git', 'status', '--short']
- write_file: tests/test_cli_help_description.py
- run: ['python', '-m', 'pytest', 'tests/test_cli_help_description.py', 'tests/test_cli.py', '-q']
- run: ['python', '-m', 'pytest', 'tests/test_cli.py', 'tests/test_cli_extra.py', 'tests/test_interactive.py', 'tests/test_stub_contract.py', '-q']
- read_file: README.md
- run: ['python', '-m', 'pytest']
- run: ['git', 'status', '--short', '--untracked-files=all']
- run: ['git', 'diff', '--', 'forgel_code/cli.py']
