# Task Review: Persist and report cost and acceptance records per task

- Task: `20261115105954_persist-and-report-cost-and-acceptance-r`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-15T19:52:43+00:00

## Summary

The attributed change adds a read-only reporting layer over the existing SQLite ledger: Ledger.cost_summary/total_cost/cost_by_stage/cost_by_generation aggregate event cost per project, generation and stage, while Ledger.acceptances derives task decisions from the approvals table. Task acceptance and rejection events (stages task_accept/task_reject) are mirrored into approvals with project, generation, task scope, decision, actor and reason/notes, so a decision is durable and queryable instead of only printed. src/forgel/costs.py renders an English report (total, per-stage, per-generation, acceptance count plus per-decision lines) used by both the new `forgel cost <project> [--home]` command and the console `/cost` command; the console-script entry point was moved to forgel.entry so the reporting path never starts a model session, with cli.main still handling everything else. tests/test_costs.py covers aggregation over recorded events, the equality of the report's total with the sum of ledger event costs, acceptance recording with actor and reason, and the report on a scripted-model demo home, all without wall-clock or random assertions since times come from the ledger's own utcnow writes. No ledger data is migrated or deleted, no tests were removed, and the existing-behaviour check passes. Minor residual risk noted only as non-blocking: the approval mirror in record_event runs after the event insert, so an idempotent replay of the same acceptance event could in principle insert a second approval row if record_event were ever called twice with an identical idempotency key; the normal accept_task path records each decision once and the tests confirm a single record.

## Requirements

- Ledger query aggregating event cost per project, per generation and per stage: pass — Ledger.total_cost, cost_by_stage, cost_by_generation and cost_summary group the events table by project_id, generation and stage.
- Ledger query returning acceptance decisions derived from the approvals table: pass — Ledger.acceptances selects approvals with the task: scope prefix and returns task_id, decision, actor, reason, generation, created_at, optionally filtered by generation.
- Record task acceptance and rejection as ledger entries with actor, task id and reason: pass — record_event mirrors task_accept/task_reject stages into approvals rows storing the task id in the scope, the decision, the payload actor and the reason/notes text.
- CLI/report path (forgel cost and console equivalent) printing total cost, cost per stage and acceptance count, reading only from the ledger: pass — src/forgel/entry.py dispatches `forgel cost` to costs.cost_command, which opens the ledger read-only and prints cost_report; console.run_console answers `/cost [project]` with the same cost_report text and the command is listed in COMMANDS and completions.
- Tests covering aggregation with recorded events, acceptance recording, and the report output on a scripted-model demo home: pass — tests/test_costs.py is added with recorded-event aggregation, acceptance recording and a scripted-model demo-home report test using ScriptedModelClient.
- Acceptance criterion: for a project with recorded events the report prints totals equal to the sum of event costs in the ledger, asserted by a test: pass — The test parses the 'Total cost:' line and asserts it equals the sum of the recorded event costs.
- Acceptance criterion: accepting a task adds an acceptance record with the actor name and the reason field, asserted by a test: pass — The test accepts a task through the normal review path and asserts the resulting acceptance entry carries the actor and the supplied reason.
- Acceptance criteria: cost and acceptance tests pass: pass — The listed acceptance checks (cost aggregation and acceptance recording tests, existing ledger behaviour) all pass with exit 0.
- Review-only: read-only over existing artifacts, no migration or deletion of ledger data: pass — cost_report and cost_command only SELECT from events/approvals/projects; the only writes are new approval rows for newly recorded task decisions, and the existing idempotent migration only adds the approvals table/columns.
- Review-only: no wall-clock or random values in assertions; fixed or injected times: pass — Tests assert on report text and ledger-derived values; timestamps come from the ledger's own utcnow writes and are never compared against a wall clock.
- Review-only: report output in English: pass — cost_report emits fixed English strings (Cost report, Total cost, Cost per stage, Cost per generation, Acceptance count) regardless of console language setting.
- Review-only: no deleted tests and no unrequested features: pass — No test removals were detected; the entry-point split and the observation key rename from 'acceptance' to 'decision' are in scope (the latter avoids overwriting the acceptance-requirements list in _task_observation).

## Blocking

- none

## Test Removals

- none


