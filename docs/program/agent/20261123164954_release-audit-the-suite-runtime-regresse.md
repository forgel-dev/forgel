# Agent Run: Release audit: The suite runtime regressed past the bound the release established. Task 2026112

- Task: `20261123164954_release-audit-the-suite-runtime-regresse`
- Status: `done`
- Repository: `code`
- Steps: 19
- Finished: 2026-11-23T18:44:30+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The README's client `--timeout` default (600 seconds) and the installer's bounded fresh-shell check stay as documented, because they describe product behaviour rather than the suite's completion time.
- The Unreleased CHANGELOG entry from the earlier suite-speed task was reworded instead of deleted, so the history still records the harness sharing and the test-configured bound without quoting a suite runtime or a budget.
- The documentation task needs no new test; verification is review of the text plus the existing suite run, per the repository rule that documentation is verified by review.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 19
- Estimated input tokens (all calls): 712292
- Provider input/output tokens: 748710 / 25203
- Provider cache hit/miss tokens: 693248 / 55462
- Estimated prompt at the end: 55882 tokens
- State: not needed

## Specification (`docs/program/specs/20261123164954_release-audit-the-suite-runtime-regresse.md`)

# Task Spec: Release audit: The suite runtime regressed past the bound the release established. Task 2026112

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The suite runtime regressed past the bound the release established. Task 2026112 |
| Project | — |
| Task | `20261123164954_release-audit-the-suite-runtime-regresse` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T17:23:39+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The project tells readers that its suite finishes in under 120 seconds, while a full run takes 163 seconds. The project's documentation rule forbids volatile runtime figures — timings, durations and runtime bounds — and says such a divergence is fixed by removing the detail, never by changing code or tuning a limit. The claim therefore misleads every reader and fails the audit's documentation consistency check.

**Outcome:** No project documentation states a suite completion time, duration or runtime bound any more. The guidance on running the project's suite still tells the reader what such a run proves: one documented command runs the whole suite, nothing leaves a part of it out, and the installer situations are included, performing a real installation into a throwaway home location with a real detected login shell, under the Python standard library alone and with no network access. Client and installer behaviour is documented exactly as before, no code changes, and the documentation now describes behaviour only and agrees with what the project actually does.

## Product Intent

A published release is only as trustworthy as its audit, and documentation that quotes a runtime figure goes stale the moment a machine or a piece of the product changes. The product needs documentation that describes what the suite covers and how to run it, never how long it takes, so documentation and reality cannot drift apart again.

## User Experience

A maintainer reading the guidance on running the suite learns what it covers and that the documented command runs all of it, including the real installer and login-shell situations, and is never told a completion time the project does not actually meet. A release auditor no longer finds a documented figure that contradicts the measured run.

## Roadmap

—

## Goals

- Every runtime figure about the suite is gone from the project's documentation.
- The guidance on running the suite stays complete and truthful about what it covers and how to run it.
- Nothing about the client's or the installer's documented behaviour changes.

## Non-Goals

- Changing how fast the suite runs, or altering any part of the product — this change removes a claim, it does not tune code or a limit.
- Raising a documented limit as the resolution: the project's documentation rule forbids runtime bounds in documentation entirely.
- Changing the release audit's own two-minute budget, which is owned outside this repository.
- Changing the client's commands, options, output form, session behaviour or the installer's install, update and uninstall behaviour.
- Adding any automated check that inspects a documentation document.
- Publishing, tagging or versioning a release.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | Documentation states behaviour and contracts, never volatile implementation details such as timings, runtime bounds or durations; a divergence between a document and reality is fixed by removing the detail, not by changing code or tuning a limit. | FORGEL.md native rules, D-109 |
| — | Documentation is text and is verified by review; no test, guard, assertion or automated check may read a documentation file, and a documentation task has review-only checks. | AGENTS.md project rules, D-106 |
| — | Never weaken a test to make it pass; fix the product or the test's premise. | Repository code AGENTS.md |

## Functional Requirements

- **FR-1**: No project documentation states a suite completion time, duration or runtime bound.
- **FR-2**: The guidance on running the suite still tells the reader that the single documented command runs the whole suite, with nothing configured or selected that leaves a part of it out.
- **FR-3**: That guidance still tells the reader that the installer situations are covered, that they perform a real installation into a throwaway home location and use a real detected login shell, and that a run from a source checkout needs nothing beyond the Python standard library and no network access.
- **FR-4**: Every statement the project makes about how to run its suite and about what such a run covers is true of the project as it stands.
- **FR-5**: The documented client commands, options, output form, session behaviour and the installer's install, update and uninstall behaviour are unchanged.
- **FR-6**: All project documentation is written in English.

## User Stories

- As a reader, I want the guidance on running the project's suite to tell me what such a run covers and that one documented command runs all of it, so that I am not misled by a completion time that goes stale.
- As a release auditor, I want no documented figure that contradicts the measured run, so that documentation consistency does not fail a release.
- As a maintainer, I want the documentation fix confined to the documentation, so that removing a claim never disturbs the product.

## Acceptance Criteria

- **AC-1**: Review of the project's documentation finds no statement of a suite completion time, duration or runtime bound anywhere.
- **AC-2**: Review of the guidance on running the suite finds it still telling the reader that one documented command runs the whole suite with nothing left out, that the installer situations are covered and perform a real installation into a throwaway home location with a real detected login shell, and that a run from a source checkout needs only the Python standard library and no network access.
- **AC-3**: Review finds every remaining statement about how to run the suite and about the coverage of such a run consistent with what the project actually does.
- **AC-4**: Review finds the documented client commands, options, output form, session behaviour and the installer's install, update and uninstall behaviour unchanged.
- **AC-5**: Review finds the documentation written in English.

## Scope Boundaries

- Remove every statement of a suite completion time, duration or runtime bound from the project's documentation.
- Keep the guidance on running the suite behaviourally accurate: one documented command runs the whole suite with nothing leaving a part out, the installer situations are included and they perform a real installation with a real detected login shell, and a run from a source checkout needs only the Python standard library and no network access.
- Make every remaining statement about how to run the suite and about what such a run covers true of the project as it stands.
- Leave the client's and the installer's documented behaviour untouched.
- Changing how fast the suite runs, or altering any part of the product — this change removes a claim, it does not tune code or a limit.
- Raising a documented limit as the resolution: the project's documentation rule forbids runtime bounds in documentation entirely.
- Changing the release audit's own two-minute budget, which is owned outside this repository.
- Changing the client's commands, options, output form, session behaviour or the installer's install, update and uninstall behaviour.
- Adding any automated check that inspects a documentation document.
- Publishing, tagging or versioning a release.

## Risks

- Removing the false claim does not make the run shorter, so the audit's timing stage may still block a release; that work belongs to a separate task.
- An existing automated guard may insist that a documentation document quote a runtime bound; such a guard contradicts the project's documentation rule and its premise would need correcting, which a reviewer may read as a weakened check.
- Removing the figure without checking the neighbouring sentences can leave the guidance describing coverage the project does not have, so the coverage statements must be checked against what the project does.
- Any other project text still hinting at a duration keeps the contradiction alive for readers.

## Open Questions

- None.

## Assumptions

- The audit's reported 163 seconds and its two-minute whole-suite budget are the authoritative measurements.
- The project's documentation rule makes removing the runtime figure the correct resolution rather than restating or raising a limit.
- The guidance keeps its current structure and wording except where a statement about timing, duration or a runtime bound has to go.
- How fast the suite runs is not changed by this task; if the release gate still needs a shorter run, that is separate work.

## Related Documents

- README.md
- CHANGELOG.md
- FORGEL.md
- AGENTS.md

## Revision History

- v1 — initial specification covering suite runtime and the documented runtime bound.
- v2 — removed implementation detail from problem, outcome, requirements, acceptance, constraints and risks.
- v3 — resolved as a documentation change: the runtime figure is removed rather than a limit raised or the suite tuned; verification is review-only and no test command is carried.
- v4 — reworded so that no requirement or acceptance mixes documentation with running or judging the suite; every criterion is verified by review.
- v5 — removed the remaining constraint that referenced product scenarios and assertions, so the whole specification stays documentation-only and review-verified.


## Summary

Documentation-only change that removes the volatile suite runtime figure from the project's documentation while keeping the guidance about how the suite is run and what a run covers behaviourally accurate. README.md `## Tests` now states that a run from a source checkout needs only the Python standard library and no network access, that the single documented command (`python -m unittest discover -s tests`) runs the whole suite with no environment variable, marker or default option leaving a test out, and that the installer situations are covered — a real installation through pip into a temporary home directory with a real detected login shell. The sentence promising the run completes in under 120 seconds (about two minutes) and the following budget claim were deleted; nothing else in the install, options, commands, output, active-project or timeout guidance changed. CHANGELOG.md was edited so the existing Unreleased entry no longer quotes the release audit's two-minute suite bound nor claims the README states a runtime bound, and it gained an entry recording the removal of the runtime figure from the documentation. No product code, installer, client behaviour or test was changed and no automated documentation check was added. Verified by reading the documentation and by running the full suite (`python -m unittest discover -s tests`, 218 tests, all pass) plus the documentation guard test module (34 tests, all pass) to confirm the retained coverage and installer statements still match the project.

## Files Changed

- `CHANGELOG.md`
- `README.md`

## Commands

- `["python", "-m", "unittest", "tests.test_readme_install", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
not run
```

## Actions

- read_file: README.md
- read_file: FORGEL.md
- read_file: AGENTS.md
- read_file: CHANGELOG.md
- read_file: releases/0.1.0/release.md
- read_file: releases/0.1.0/plan.md
- read_file: CONTRIBUTING.md
- list_files
- read_file: tests/test_readme_install.py
- read_file: pyproject.toml
- read_file: tests/test_install.py
- read_file: tests/test_install.py
- read_file: tests/test_extras.py
- write_file: README.md
- read_file: tests/test_install.py
- write_file: CHANGELOG.md
- read_file: tests/test_check_cleanup.py
- write_file: CHANGELOG.md
- run: ['python', '-m', 'unittest', 'tests.test_readme_install', '-v']
- read_file: tests/test_packaging.py
- write_file: CHANGELOG.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: tests/test_install_timeout_verdict.py
