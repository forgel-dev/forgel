# Agent Run: Record M0 and M0.5 completion status in PLAN.md and README

- Task: `20261115105954_record-m0-and-m0-5-completion-status-in-`
- Status: `done`
- Repository: `main`
- Steps: 39
- Finished: 2026-11-15T11:24:37+00:00

## Requirements

- In PLAN.md §10 Roadmap add an explicit status marker line directly under the M0 — Skeleton and M0.5 — Self-Hosting headings, in the form '**Status:** done — <evidence>' or '**Status:** partial — <what remains>', with concrete evidence references (make demo, telegram gateway, planner, task QA, peak policy, sandbox).
- Do not delete or renumber existing roadmap items; only add status markers and, where a stated deliverable is missing, list it under 'partial' with the remaining item.
- In README.md update the '**Status:** pre-alpha' section to name M0 and M0.5 as complete (or partial with the same wording as PLAN.md) and link to PLAN.md §10.
- Keep the wording in English (D-025) and factual: do not claim a state that the repository does not show.
- Add tests/test_docs_status.py, a unittest that reads PLAN.md and README.md from the repository root and asserts: under each of the '### M0 — Skeleton' and '### M0.5 — Self-Hosting' headings there is a '**Status:**' line, and README.md contains the same M0/M0.5 status wording.

## Acceptance Criteria

- tests/test_docs_status.py exists and passes, proving PLAN.md has a Status line under both the M0 and M0.5 roadmap headings and README.md carries the matching status.
- The repository documentation claims only evidence that exists in the tree (make demo target, telegram module, planner module, task QA, peak policy, sandbox); a human confirms each claim is backed by a file or Makefile target.

## Constraints

- Documentation-only change plus one test file; do not change product code.
- Public documents in English.
- Do not mention internal working documents or sessions in the text.

## Assumptions

- Marked M0 as done: every M0 deliverable has a backing file or Makefile target in the tree.
- Marked M0.5 as partial rather than done because its exit criterion (a real Forgel change accepted through Forgel itself) has not happened and post-merge smoke/auto-revert is still a reserved config field, both stated in README and PLAN §11.
- Listed the missing M0.5 deliverables in the status line instead of adding new roadmap bullets, so existing items are neither deleted nor renumbered.
- Used the exact existing M0/M0.5 headings (including the durations in parentheses) as the anchors for the status lines and the test lookups.
- Kept the documentation in English per D-025 and wrote no internal-work references.

## Test Removals

- none

## Context

- Window: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Estimated prompt at the end: 184498 tokens
- State: not needed

## Summary

Recorded M0 and M0.5 completion status. PLAN.md §10 now carries a '**Status:** done — <evidence>' line directly under '### M0 — Skeleton (2–3 weeks)' citing concrete artifacts (Makefile/make demo, src/forgel/cli.py, orchestrator.py, ledger.py, telegram.py, approvals.py, registry/recipes.json, jurisdiction/generic.json and ru.json, Dockerfile + compose.yaml + hello-web template, context.py + forgel.toml, LICENSE/CONTRIBUTING.md), and a '**Status:** partial — <what remains>' line directly under '### M0.5 — Self-Hosting (immediate goal)' citing the existing telegram gateway, planner, task QA, task review, peak policy, sandbox, adoption, GitHub provider and deploy utility, and naming the remaining items (the self-hosting exit criterion and post-merge smoke with auto-revert). No existing roadmap item was deleted or renumbered; later milestones are untouched. README.md's '**Status:** pre-alpha' section now names M0 (done) and M0.5 (partial with the same remaining-work wording) and links to PLAN.md §10 (PLAN.md#10-roadmap). Added tests/test_docs_status.py, a stdlib unittest that reads both files from the repository root and asserts the status lines exist under each heading, that the evidence paths exist on disk, that make's demo target exists, that later milestone headings are unchanged, and that README repeats the same M0/M0.5 status and link. Full suite: python -m unittest discover -s tests — 425 tests, OK.

## Files Changed

- `PLAN.md`
- `README.md`
- `tests/test_docs_status.py`

## Commands

- `["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_docs_status.py", "-v"]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_docs_status.py", "-v"]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_docs_status.py", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115112351_inspect-and-finish: step cap, handoff to session 2
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
.........................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 425 tests in 53.573s

OK

```

## Actions

- read_file: PLAN.md
- read_file: README.md
- read_file: Makefile
- read_file: docs/program/agent/20261115004702_readme.state.md
- write_file: PLAN.md
- read_file: PLAN.md
- read_file: README.md
- write_file: tests/test_docs_status.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_docs_status.py', '-v']
- write_file: README.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_docs_status.py', '-v']
- write_file: tests/test_docs_status.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_docs_status.py', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
