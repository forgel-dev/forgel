# Agent Run: Persist and report cost and acceptance records per task

- Task: `20261115105954_persist-and-report-cost-and-acceptance-r`
- Status: `done`
- Repository: `main`
- Steps: 74
- Finished: 2026-11-15T19:51:18+00:00

## Requirements

- Ledger: add a query that aggregates event cost per project, per generation and per stage, and a query that returns acceptance decisions derived from the approvals table.
- Record task acceptance and rejection as ledger entries with actor, task id and reason, so an acceptance is durable and queryable rather than only printed.
- Add a CLI/report path (forgel cost and the console equivalent) printing total cost, cost per stage and the acceptance count for a project, reading only from the ledger.
- Extend tests/test_ledger.py or add tests/test_costs.py covering aggregation with recorded events, acceptance recording, and the report output on a scripted-model demo home.

## Acceptance Criteria

- Cost and acceptance tests pass.
- For a project with recorded events, the cost report prints totals that equal the sum of event costs in the ledger, asserted by a test.
- Accepting a task adds an acceptance record with the actor name and the reason field, asserted by a test.

## Constraints

- Read-only over existing artifacts; do not migrate or delete ledger data.
- No wall-clock or random values in assertions; fix times or use injected values.
- Report output in English.

## Assumptions

- Ledger `events` were the only cost source available, so aggregation groups the existing `cost` column by project, generation and stage; no new cost fields were added to the schema.
- Acceptance/rejection already wrote `task_accept` / `task_reject` events with actor, task id and reason; these are now mirrored into the `approvals` table (scope `task:<id>`, notes = reason) so `acceptances()` is a pure approvals-table query, keeping the old event timeline intact.
- The console equivalent of `forgel cost` is the `/cost` command in the local console (the shared chat router was left unused for this command to keep the Telegram surface unchanged); the report text is identical because both call `costs.cost_report`.
- `forgel cost` is wired through a new thin console-script entry point (`forgel.entry:main`) that dispatches only the `cost` subcommand and delegates everything else to `forgel.cli.main`, so the large CLI module was not restructured.
- The report prints money as `$0.00` with two decimals and stays in English regardless of console language.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 74
- Estimated input tokens (all calls): 4753525
- Provider input/output tokens: 4983049 / 134211
- Estimated prompt at the end: 125496 tokens
- State: not needed

## Summary

Implemented durable cost and acceptance reporting that reads only from the ledger.

What changed:
1. src/forgel/ledger.py
   - Added aggregation queries over recorded events: total_cost(), cost_by_stage(), cost_by_generation() and cost_summary() (total, per stage, per generation, event count).
   - Added acceptances() which derives task acceptance/rejection decisions from the approvals table (scope `task:<id>`), returning task id, decision, actor, reason and generation.
   - Task acceptance/rejection events are now also mirrored into the approvals table on append, so a decision is durable and queryable instead of only printed. Existing rows are untouched: no migration, deletion or rewrite of ledger data.
2. src/forgel/costs.py (new) — English report builder and the `forgel cost` command implementation. Prints total cost, cost per stage, cost per generation, the acceptance count and each decision with actor and reason.
3. src/forgel/entry.py (new) + pyproject console script + __main__.py — `forgel cost <project> [--home DIR]` routes to the ledger-only report; every other argv goes to the existing CLI unchanged.
4. src/forgel/console.py — the local console handles `/cost [project]` (falls back to the selected project), added to tab completion, and prints the same report.
5. tests/test_costs.py (new, 8 tests) — aggregation of recorded events, empty project, report total equals the sum of event costs, CLI report, acceptance with actor+reason, rejection with reason plus count in the report, the console report on a scripted-model demo home, and the `forgel cost` entry point. All costs and times are injected, no wall-clock or random values.

Testing: full suite `python -m unittest discover -s tests` — 496 tests, OK (the previous run before adding the entry-point test was 495, also OK).

## Files Changed

- `pyproject.toml`
- `src/forgel/__main__.py`
- `src/forgel/console.py`
- `src/forgel/costs.py`
- `src/forgel/entry.py`
- `src/forgel/ledger.py`
- `tests/test_costs.py`

## Commands

- `["python", "-m", "unittest", "tests.test_ledger", "tests.test_task_review", "-v"]` → exit 0
- `["python", "-m", "unittest", "tests.test_costs", "-v"]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_costs.py", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_costs.py", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115195027_inspect-and-finish: context handoff to session 2 (~4816/3072 tokens)
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
................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 496 tests in 60.149s

OK

```

## Actions

- read_file: src/forgel/ledger.py
- read_file: src/forgel/ledger.py
- read_file: src/forgel/approvals.py
- read_file: src/forgel/cli.py
- read_file: tests/test_ledger.py
- read_file: src/forgel/console.py
- read_file: src/forgel/chat.py
- read_file: src/forgel/chat.py
- read_file: src/forgel/model.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/cli.py
- read_file: tests/test_task_review.py
- read_file: tests/test_task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/cli.py
- read_file: tests/test_cli.py
- list_files
- read_file: tests/test_console.py
- read_file: tests/test_orchestrator.py
- read_file: src/forgel/model.py
- read_file: src/forgel/model.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/task_review.py
- read_file: pyproject.toml
- read_file: src/forgel/coding_agent.py
- read_file: src/forgel/task_review.py
- run: ['python', '-m', 'unittest', 'tests.test_ledger', 'tests.test_task_review', '-v']
- read_file: src/forgel/task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/console.py
- read_file: src/forgel/console.py
- read_file: src/forgel/cli.py
- write_file: src/forgel/ledger.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/console.py
- read_file: tests/test_console.py
- write_file: src/forgel/costs.py
- read_file: src/forgel/console.py
- read_file: src/forgel/__main__.py
- write_file: src/forgel/costs.py
- write_file: src/forgel/entry.py
- read_file: src/forgel/console.py
- read_file: pyproject.toml
- write_file: src/forgel/console.py
- read_file: src/forgel/config.py
- write_file: src/forgel/costs.py
- run: ['python', '-m', 'unittest', 'tests.test_costs', '-v']
- write_file: tests/test_costs.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_costs.py', '-v']
- write_file: pyproject.toml
- write_file: src/forgel/__main__.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- write_file: tests/test_costs.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_costs.py', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
