# Agent Run: Document the engine installer and version contract

- Task: `20261124152248_document-the-engine-installer-and-versio`
- Status: `failed`
- Repository: `main`
- Steps: 107
- Finished: 2026-11-25T15:27:39+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- none

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 107
- Estimated input tokens (all calls): 5675067
- Provider input/output tokens: 5890695 / 43940
- Provider cache hit/miss tokens: 5800960 / 89735
- Estimated prompt at the end: 81798 tokens
- State: not needed

## Specification (`docs/program/specs/20261124152248_document-the-engine-installer-and-versio.md`)

# Task Spec: Document the engine installer and version contract

## Document Information

| Field | Value |
|-------|-------|
| Feature | Document the engine installer and version contract |
| Project | — |
| Task | `20261124152248_document-the-engine-installer-and-versio` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `main` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The engine project has no user-facing statement of how the engine is obtained in one install step, where its entry point is placed and how the user reaches it from the shell, how it is removed, how it reports the version it is in a form another program consumes directly, or how the version that a configured source or release ref would provide is determined before anything is installed. A user cannot obtain the engine without reading the source, and the companion client's combined install mode and its declared minimum supported engine version have no documented version contract to rely on, so the pair's install story and its compatibility judgement rest on undocumented behaviour.

**Outcome:** The engine project's user-facing introduction and its user-visible release notes describe, in agreement with what the shipped installer and engine actually do: the single install step and its prerequisites; where the engine's entry point is placed and how the engine becomes reachable from the shell; how a user confirms the install by reading the reported version; the version inquiry that another program consumes directly; how the version provided by a configured source or release ref is determined without installing anything and how an installed engine is compared against it; and how to remove the engine, including what is kept.

## Product Intent

The milestone makes Forgel and Forgel Code install and run as one working pair. The engine gets its own installer, the client gets a combined install mode and a declared minimum supported engine version checked at startup. For that to work a user must be able to obtain the engine from a single documented install step, and any tool deciding whether the installed engine is good enough must have a documented, directly consumable version report and a documented rule for determining and comparing available versions.

## User Experience

A user who wants only the engine finds the install step at the start of the project's user-facing introduction, satisfies the listed prerequisites, performs one install step, and ends up with a working engine they can run; the text also tells them what to do when the installed location is not yet reachable from the shell they are in. They can confirm success by asking the engine for its version, and another program can read that answer without interpreting prose. A user installing the pair, or another tool checking compatibility, reads the same text and learns how the available engine version is determined from the configured source or release ref before installing, and that only a strictly newer available version replaces what is already there. When they want the engine gone, the removal instructions remove it and say what is kept.

## Roadmap

—

## Goals

- Give the engine a documented single install step with its prerequisites, so a user obtains it without reading the source.
- Make entry point placement, shell reachability and post-install version confirmation explicit so a user can tell whether the install worked and how to run the engine.
- Document the directly consumable version inquiry as the supported compatibility judgement for another tool.
- Document how the version a configured source or release ref would provide is determined without installing, and how it is compared against an installed engine, including the strictly-newer rule.
- Document removal, including what is kept and what is removed.
- Record the new user-visible capabilities in the release notes.
- Correct contradicting statements so the user-facing introduction agrees with the shipped installer and version behaviour.

## Non-Goals

- Documenting Forgel Code, its combined install mode or its declared minimum supported engine version; that belongs to the client repository's documentation.
- Assigning, promising, publishing or rewriting a release version or tag.
- Changing installer, entry point, version reporting or removal behaviour; this task changes documentation text only.
- Describing internal structure, timings, runtime bounds, test durations or local environment details.
- Introducing any automated check, guard or assertion that inspects documentation text.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | Documentation is text and is verified by review: no test, guard or assertion that inspects a documentation file may be added, required or accepted, and a documentation task carries review-only checks. | FORGEL.md Native Rules (D-106); AGENTS.md Project Rules (D-106) |
| — | Documentation states behaviour and contracts and never volatile implementation details such as internal structure, timings, runtime bounds, test durations or local environment; a divergence is fixed by removing the detail. | FORGEL.md Native Rules (D-109) |
| — | All committed project artefacts, including documentation and commit messages, are English. | FORGEL.md Language section (D-025) |
| — | The client is a thin UI over the engine's parameterized commands and does not do the engine's work itself; model access, checks and process live in the engine. | User decision log D-002 |
| — | The base parameterized engine command line stays in the engine, and the separate client replaces the interactive chat mode. | User decision log D-003 |

## Functional Requirements

- **FR-1**: The installation guidance presents one install step as the complete way to obtain a working engine on a supported machine and names the prerequisites the user must satisfy first.
- **FR-2**: The installation guidance states where the engine's entry point is placed, how the user runs the engine afterwards, and what the user does when that location is not reachable from the shell the user is in.
- **FR-3**: The installation guidance states how the user confirms a successful install by asking the engine which version it is.
- **FR-4**: The guidance states that the engine can be asked for its version in a form another program consumes directly without interpreting human-oriented text, that this is the supported way for another tool to judge compatibility, and that it works with no project present, no model credential configured and from any working directory.
- **FR-5**: The guidance states how the version that a configured source or release ref would provide is determined before anything is installed on the machine, and that this value is what an already installed engine is compared against.
- **FR-6**: The guidance states the comparison rule: an engine already present is replaced only when the available version is strictly newer, and an equal or older available version leaves the installed engine untouched.
- **FR-7**: The guidance states how to remove the engine and its entry point and which of the user's configuration and project material are kept.
- **FR-8**: Every name, option, location and example in the new text matches what the shipped engine and its installer do; nothing is described that they do not do.
- **FR-9**: The user-visible release notes carry an entry covering the single install step, the entry point and shell reachability, removal, the directly consumable version inquiry and pre-install version determination.
- **FR-10**: The new text states behaviour and stable contracts only, with no internal structure, timing, runtime bound, test duration or local environment detail.
- **FR-11**: After the change, no statement in the project's user-facing introduction contradicts the shipped installer or the shipped version behaviour.

## User Stories

- As a user who wants only the engine, I want a documented single install step with its prerequisites so that I obtain a working engine without reading the source.
- As a user, I want the documentation to tell me where the engine's entry point is placed and how to reach it from my shell so that the engine actually runs instead of being reported as missing.
- As a user, I want a documented way to read the engine's version so that I can confirm the install succeeded.
- As a user, I want documented removal steps that say what is kept so that I can remove the engine cleanly without losing my configuration and projects.
- As the author of another tool, I want a documented version inquiry that my program consumes directly so that I judge engine compatibility without parsing prose.
- As a maintainer of the pair, I want the documented rule for how an available version is determined and compared so that an already present equal or newer engine is left alone and the combined install stays idempotent.

## Acceptance Criteria

- **AC-1**: A reader with no prior knowledge of the repository can obtain a working engine by satisfying the listed prerequisites and performing the one presented install step, and the section names no second step required for that result.
- **AC-2**: The text says where the engine's entry point is placed, how the engine is run afterwards, and what the user does when that location is not reachable from the shell the user is in.
- **AC-3**: The text shows how the user confirms the install by reading the version the engine reports.
- **AC-4**: The text states that the engine reports its version in a form another program consumes directly without interpreting human-oriented text, that this is the supported compatibility judgement for other tools, and that it needs no project, no model credential and no particular working directory.
- **AC-5**: The text states how the version that a configured source or release ref would provide is determined before anything is installed, and that this value is what an installed engine is compared against.
- **AC-6**: The text states that only a strictly newer available version replaces an installed engine, and that an equal or older available version leaves the installed engine untouched.
- **AC-7**: The text states how to remove the engine and its entry point and which of the user's configuration and project material are kept.
- **AC-8**: A reviewer finds no documented behaviour that the shipped installer and engine do not perform, and no shipped install, version or removal behaviour that the text contradicts.
- **AC-9**: The user-visible release notes contain an entry covering the single install step, the entry point and shell reachability, removal, the directly consumable version inquiry and pre-install version determination.
- **AC-10**: No internal structure, timing, runtime bound, test duration or local environment detail appears in the new text.
- **AC-11**: Reading the project's user-facing introduction end to end after the change yields no statement that contradicts the shipped installer or the shipped version behaviour, and no previously accurate section is weakened.

## Scope Boundaries

- The engine project's user-facing introduction: installation, entry point placement and shell reachability, post-install version confirmation, the directly consumable version inquiry, determination of the version a configured source or release ref would provide, the strictly-newer comparison rule, and removal.
- The engine project's user-visible release notes for the new install step, entry point and shell reachability, removal, the directly consumable version inquiry and pre-install version determination.
- Correction of existing user-facing statements that contradict the shipped installer or the shipped version reporting.
- Keeping every documented name, option, location and example identical to the shipped implementation.
- Documenting Forgel Code, its combined install mode or its declared minimum supported engine version; that belongs to the client repository's documentation.
- Assigning, promising, publishing or rewriting a release version or tag.
- Changing installer, entry point, version reporting or removal behaviour; this task changes documentation text only.
- Describing internal structure, timings, runtime bounds, test durations or local environment details.
- Introducing any automated check, guard or assertion that inspects documentation text.

## Risks

- The engine installer implementation was blocked earlier; if it is not finished first, this task has nothing truthful to describe and would either invent behaviour or document behaviour that is not shipped, missing the milestone goal.
- The names and locations chosen during implementation may differ from those the companion client's documentation uses, leaving the pair's documentation mutually inconsistent and the combined install story wrong.
- The project's user-facing introduction is long; installation guidance placed deep inside it leaves the single install step hard to find and undercuts the intent of a simple entry.
- A wrong statement about where the entry point is placed or how it becomes reachable produces exactly the failure the milestone exists to remove, now caused by documentation instead of by code.
- Naming a concrete version anywhere makes the text stale immediately, because no engine release is published yet.
- A reviewer may accept prose that describes intended behaviour rather than shipped behaviour, which would leave the client's declared minimum supported engine version without a truthful contract.
- Removing accurate existing statements while tidying could break guidance unrelated to this task.

## Open Questions

- None.

## Assumptions

- The engine installer, its entry point and its version reporting are implemented before this documentation task runs, so the documented names, options, locations and version answer can be read from the shipped code.
- The version inquiry answers with a value a program consumes directly, and it fails visibly rather than answering with a partial value when the engine cannot be used.
- The install step installs for the current user without elevated privileges, and the documented guidance for an unreachable location is something the user can act on in their own shell.
- Removing the engine removes the engine and its entry point while keeping the user's configuration and project material.
- The documentation lives in the engine project's user-facing introduction and user-visible release notes, and the change is additive apart from correcting contradicting statements.
- The companion client's documentation separately describes the combined install mode and the declared minimum supported engine version.

## Related Documents

- README.md
- PLAN.md
- AGENTS.md
- FORGEL.md
- docs/deploy.md

## Revision History

- 0.1 — initial specification for the engine documentation task covering the installer, entry point, removal, the directly consumable version inquiry and the version determination and comparison contract.
- 0.2 — restated in behaviour terms: verification mechanics, file paths and runtime steps removed from requirements, acceptance, constraints, goals, user stories, risks and assumptions; every acceptance criterion now carries a review-only check and the task has no test command.


## Summary

The shipped engine has no installer to document. The plan docs/program/plans/20261124145600_make-forgel-and-forgel-code-install-and-.md marks backlog item 2, 'Add the engine's one-command installer with pre-install version resolution', as blocked ('the dependency scout exceeded its step limit'), and that task's spec (docs/program/specs/20261124152248_add-the-engine-s-one-command-installer-w.md) states 'The owner decides this task's scope before it can be implemented'. In this repository there is no install script (no install.sh anywhere; only deploy/entrypoint.sh and Django template scripts), no uninstall path, no private prefix, no launcher placed on PATH, no marked profile block or shell-reachability handling (no 'export PATH' in the tree), and no determination of the version a configured source or release ref would provide. The only shipped piece is the version inquiry in src/forgel/engine_version.py ('forgel version [--json]', dispatched from src/forgel/entry.py), which alone cannot satisfy FR-1, FR-2, FR-3, FR-5, FR-6, FR-7, AC-1, AC-2, AC-3, AC-5, AC-6, AC-7 and AC-9. Writing the installation, entry point, pre-install version determination, strictly-newer comparison and removal text would document behaviour the shipped installer and engine do not perform, which FR-8, AC-8 and the specification's own Risks section forbid. Decision needed: unblock and implement the engine installer task first, then re-run this documentation task against the shipped behaviour.

## Files Changed

- none

## Commands

- none

## Final Test Output

```
not run
```

## Actions

- list_files
- list_files
- search_files: forgel @ scripts *
- search_files: install @ . *.sh
- search_files: install\.sh @ .
- read_file: README.md
- search_files: install @ README.md
- search_files: forgel-code|forgel_code @ . *.sh
- list_files
- search_files: __version__|--version|engine_version @ src *.py
- read_file: src/forgel/engine_version.py
- read_file: src/forgel/entry.py
- search_files: pipx|uv tool install|releases/latest @ . *.md
- search_files: forgel version @ .
- list_files
- search_files: installer @ . *.md
- search_files: 20261124145600 @ .
- search_files: console_scripts|\[project\.scripts\]|\[project\] @ . *.toml
- read_file: pyproject.toml
- search_files: uninstall|\bsh\b|curl @ README.md
- search_files: uninstall @ . *.py
- list_files
- search_files: CHANGELOG|changelog @ . *.md
- search_files: install @ docs *.md
- search_files: installer|install step|single install @ docs/program *.md
- list_files
- search_files: install @ tests *.py
- list_files
- search_files: combined install|one install step|install and run @ docs *.md
- search_files: make-forgel-and-forgel-code @ .
- search_files: install @ PLAN.md
- read_file: README.md
- search_files: get\.forgel|forgel-dev/forgel/.*install|releases/latest|installer @ . *
- search_files: pipx|venv|PyPI|pypi|bin_dir|\.local/bin @ src *.py
- search_files: release ref|release_ref|source ref|FORGEL_SOURCE|FORGEL_REPO @ . *.py
- search_files: ^##  @ README.md
- read_file: install.sh
- search_files: PATH @ . *.sh
- search_files: install and run @ docs/program/plans
- list_files
- search_files: single install step @ .
- read_file: docs/program/agent/20261122062911_make-install-sh-put-forgel-code-on-path-.md
- search_files: def .*_command\(|install_command|tool_install @ src *.py
- read_file: registry/recipes.json
- search_files: uninstall @ .
- read_file: Makefile
- search_files: pip install|uv tool|pipx|install-sh|get\.forgel @ . *.md
- search_files: install @ . *.yml
- search_files: forgel version|version --json|version_command @ . *
- search_files: ^#!/ @ .
- search_files: https://forgel|raw.githubusercontent|install @ . install*
- search_files: Make Forgel and Forgel Code install @ .
- search_files: curl|download|github.com/forgel @ src *.py
- search_files: install @ docs/program/plans
- read_file: docs/program/plans/20261124145600_make-forgel-and-forgel-code-install-and-.md
- search_files: launcher|marked block|prefix @ src/forgel *.py
- search_files: \| *sh|sh -s|--uninstall @ .
- search_files: export PATH @ .
- search_files: one-command installer @ .
- search_files: available @ src *.py
- search_files: 20261124 @ docs/program/agent
- search_files: 20261124152248_emit-a-machine-readable-engine-version @ docs/program/specs
- search_files: engine_version @ tests *.py
- search_files: instal @ . src/forgel/*.sh
- search_files: profile|PATH @ src/forgel *.py
- search_files: one-command-installer|marked profile block|private prefix @ .
- search_files: install @ src *install*
- search_files: one-command @ .
- read_file: tests/test_engine_version.py
- search_files: 20261124152248_document-the-engine-installer @ docs/program/agent
- search_files: #! @ . *.sh
- search_files: set -eu|set -euo @ .
- search_files: install|PATH|profile @ INTERNAL.md
- read_file: docs/program/specs/20261124152248_add-the-engine-s-one-command-installer-w.md
- search_files: FORGEL_PREFIX|forgel-launcher|bin/forgel|get-forgel @ .
