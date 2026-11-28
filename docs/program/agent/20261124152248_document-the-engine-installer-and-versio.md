# Agent Run: Document the engine installer and version contract

- Task: `20261124152248_document-the-engine-installer-and-versio`
- Status: `done`
- Repository: `main`
- Steps: 278
- Finished: 2026-11-28T08:45:52+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The existing documentation task was continued rather than restarted: the installer, entry point, uninstall path and pre-install version determination are now shipped by install.sh on this branch, so the guidance describes that shipped behaviour instead of the earlier blocked state.
- The strictly-newer comparison is documented as the rule the caller driving the installer applies (the engine installer installs the target it resolved), matching the shipped installer, which offers `--resolve` for the available version and no downgrade check of its own.
- Removal is documented as removing the engine tree, the entry point and the installer's start-up block while keeping the user's configuration and project material under `~/.forgel`, which is what the shipped uninstall does.
- Documentation was verified by reading it against the shipped installer and version report only; per the repository rules no automated check that reads documentation was added.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 278
- Estimated input tokens (all calls): 14532658
- Provider input/output tokens: 15016993 / 257138
- Provider cache hit/miss tokens: 14766592 / 250401
- Estimated prompt at the end: 65429 tokens
- State: `docs/program/agent/20261124152248_document-the-engine-installer-and-versio.state.md`

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

Documented the engine installer and version contract in the user-facing introduction, the detailed install guide, and the release notes, consistent with the shipped installer and the shipped version report. README's Install section is now the first thing a user reads: prerequisites (checkout plus Python 3.11 or newer on PATH), the single step `sh install.sh`, where the engine and the `forgel` entry point land (`~/.local/share/forgel`, `~/.local/bin/forgel`, or the `FORGEL_INSTALL_ROOT`/`FORGEL_BIN_DIR` overrides), the delimited start-up block that puts the command directory ahead on PATH, starting a new terminal session, and what to do when the name is still unreachable in the user's own shell. It states how the install is confirmed with the engine's `version --json` report, that the report is one JSON object a program consumes directly as the supported compatibility judgement and needs no project, model credential or particular working directory, that `sh install.sh --resolve` determines the version a configured source and reference would provide before anything is installed and that this value is what an installed engine is compared against, that only a strictly newer available version replaces an installed engine while an equal or older one leaves it untouched, and what `--uninstall` removes and which configuration and project material under `~/.forgel` it keeps. docs/install.md was brought in line with the same shipped behaviour: prerequisites and the single step, a new section on placement, shell reachability and the remedy for an unreachable location, a new section on confirming the install and the directly consumable report, the pre-install determination and the strictly-newer comparison rule, and removal rewritten to name the engine tree, the entry point, the start-up block and the kept user data. CHANGELOG.md gains entries for the single install step with entry point and shell reachability, pre-install version determination, the comparison rule, removal that keeps user data, and the directly consumable version report. No installer, entry point, version-reporting or removal behaviour was changed, no release version or tag was named, and no test, guard or assertion inspecting documentation was added. Verified by running the repository gate, `python3 -m unittest discover -s tests`, which passed (820 tests), plus the installer and version suites specifically; every documented name, option, default location and output shape was read from install.sh, src/forgel/engine_version.py, src/forgel/entry.py and tests/test_install.py.

## Files Changed

- `CHANGELOG.md`
- `README.md`
- `docs/install.md`

## Commands

- `["git", "show", "--stat", "92fdf31"]` → exit 0
- `["git", "show", "--stat", "0320f4d"]` → exit 0
- `["git", "show", "--stat", "106a30f"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-q"]` → exit 124
- `["git", "status", "--short"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "README.md", "docs/install.md"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_engine_version", "tests.test_install", "-q"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261128084305_inspect-and-finish: context handoff to session 2 (~6504/3072 tokens)
[agent] 20261128084312_record-the-handoff: context handoff to session 2 (~2752/3072 tokens)
[agent] 20261128084312_record-the-handoff: context handoff to session 3 (~7027/3072 tokens)
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[github] GitHub API is unreachable; the branch is pushed without pull-request checks
[github] demo-622f47ec: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
.........................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
...[model] script mode: /private/var/folders/2g/9_qkdxhs6hx0fm8bm1wtlshr0000gq/T/tmp5ktwy_s5/model-script.json does not exist
.....error: say needs text: --text "..." or a trailing argument
.................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 820 tests in 180.337s

OK

```

## Actions

- recall
- recall
- recall
- recall
- recall
- recall
- recall
- read_file: install.sh
- recall
- recall
- recall
- read_file: install.sh
- search_files: newer|newer than|strictly @ . *.py
- read_file: docs/program/plans/20261124145600_make-forgel-and-forgel-code-install-and-.md
- read_file: src/forgel/release_train.py
- recall
- run: ['git', 'show', '--stat', '92fdf31']
- read_file: tests/test_install.py
- read_file: src/forgel/release_train.py
- search_files: Changelog @ . CHANGELOG.md
- search_files: Unreleased @ . *.py
- search_files: def write|def envelope @ src/forgel/client_cli.py *.py
- read_file: src/forgel/release_train.py
- read_file: README.md
- recall
- search_files: version @ README.md README.md
- search_files: forgel version @ . README.md
- search_files: def envelope|def write @ src/forgel *.py
- read_file: src/forgel/client_cli.py
- run: ['git', 'show', '--stat', '0320f4d']
- search_files: install|Install @ README.md README.md
- read_file: pyproject.toml
- read_file: src/forgel/entry.py
- read_file: tests/test_engine_version.py
- search_files: installed|INSTALLED @ install.sh *.sh
- search_files: Install|install @ INTERNAL.md INTERNAL.md
- run: ['git', 'show', '--stat', '106a30f']
- recall
- search_files: version @ src/forgel/cli.py *.py
- search_files: FORGEL_HOME @ src/forgel *.py
- search_files: git clone|clone the @ . README.md
- search_files: forgel version|engine version|version report|__version__ @ . *.md
- list_files
- search_files: ^##  @ README.md README.md
- recall
- search_files: README|docs/install @ tests *.py
- search_files: home|HOME @ src/forgel/layout.py *.py
- read_file: README.md
- edit_file: README.md
- read_file: src/forgel/release_train.py
- read_file: README.md
- read_file: README.md
- search_files: 20261124152248_document-the-engine-installer @ docs/program *
- search_files: release.md @ releases *
- edit_file: README.md
- write_file: CHANGELOG.md
- edit_file: README.md
- read_file: README.md
- read_file: README.md
- edit_file: README.md
- edit_file: README.md
- read_file: README.md
- edit_file: docs/install.md
- read_file: docs/install.md
- edit_file: docs/install.md
- read_file: README.md
- edit_file: README.md
- read_file: README.md
- edit_file: README.md
- read_file: README.md
- read_file: docs/install.md
- edit_file: docs/install.md
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-q']
- edit_file: README.md
- read_file: README.md
- edit_file: README.md
- read_file: README.md
- edit_file: README.md
- edit_file: docs/install.md
- read_file: docs/install.md
- edit_file: docs/install.md
- edit_file: docs/install.md
- read_file: docs/install.md
- run: ['git', 'status', '--short']
- run: ['git', 'status', '--short']
- run: ['git', 'status', '--short']
- run: ['git', 'status', '--short']
- run: ['git', 'diff', 'README.md', 'docs/install.md']
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: src/forgel/engine_version.py
- search_files: strictly|newer|ordering\(|installed_version @ . *.py
- read_file: tests/test_install.py
- search_files: def envelope @ src/forgel/client_cli.py *.py
- search_files: def envelope @ src/forgel *.py
- read_file: src/forgel/client_cli.py
- search_files: installed|same version|already @ install.sh *.sh
- search_files: strictly newer|idempotent|available version|installed engine @ docs/program/plans *.md
- search_files: install\.sh|--resolve @ src *.py
- read_file: docs/install.md
- read_file: docs/install.md
- search_files: README|docs/install @ tests *.py
- read_file: README.md
- read_file: CHANGELOG.md
- search_files: forgel_home|\.forgel|FORGEL_HOME @ src/forgel/layout.py *.py
- search_files: def home|home\( @ src/forgel/layout.py *.py
- search_files: forgel @ src/forgel/layout.py *.py
- search_files: FORGEL_HOME @ src *.py
- search_files: repos @ src/forgel/layout.py *.py
- search_files: CHANGELOG @ src/forgel *.py
- search_files: install|Install|version|pip @ README.md README.md
- search_files: sh install|forgel version|uninstall @ . *.md
- edit_file: README.md
- run: ['python3', '-m', 'unittest', 'tests.test_engine_version', 'tests.test_install', '-q']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: README.md
- recall
- search_files: install|pip |PATH @ README.md README.md
- read_file: README.md
- run: ['git', 'ls-files', 'install.sh', 'tests/test_install.py', 'src/forgel/engine_version.py', 'tests/test_engine_version.py', 'CHANGELOG.md']
- search_files: version_command|version @ src/forgel/entry.py entry.py
- search_files: version @ src entry.py
- search_files: version @ . entry.py
- recall
- recall
- search_files: installer|sh install|pip install|forgel version @ . README.md
- read_file: src/forgel/release_train.py
- edit_file: docs/install.md
- read_file: docs/install.md
- edit_file: docs/install.md
- read_file: docs/install.md
- read_file: README.md
- read_file: docs/install.md
- read_file: tests/test_install.py
- read_file: src/forgel/release_train.py
- read_file: README.md
- read_file: CHANGELOG.md
- read_file: docs/install.md
