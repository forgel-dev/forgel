# Runtime Limits

A limit is a crash guard, never a work budget. It exists to stop a hung
process from blocking the runtime forever. Every limit is configured, has a
reason, is visible to the controlling agent, and can be raised at runtime.

## Principles

- A limit is justified by a real measurement or a stated bound, not a guess.
- It is configurable (environment, project override or the runtime command).
- The controlling agent and the chat agent know the limits and the command
  that raises them.
- When a limit is reached the failure names it, and the controller can raise
  it at the same place and continue the work.

## command_timeout

- Meaning: how long one repository command (build, test suite, probe) may run.
- Default: 3600 seconds (one hour). A deliberately slow suite fits; a hung
  process still ends within an hour.
- Configure: `FORGEL_COMMAND_TIMEOUT` at start, or the project override
  `docs/program/limits.json` (`{"command_timeout": 7200}`).
- Raise at runtime: the `set_limit` operation with
  `{"name": "command_timeout", "seconds": <n>}` is available to the
  controlling agent and to the chat agent through `runtime`. Raising it
  also puts the stopped task back to work.

## Model and release budgets

These are separate bounds with their own configuration; they are listed here
so no limit is hidden:

| Limit | Default | Configure | Why |
|---|---|---|---|
| model request timeout | 600 s | `FORGEL_MODEL_TIMEOUT` | one request cannot hang forever |
| model call total | 1500 s | `FORGEL_MODEL_TOTAL_TIMEOUT` | retries under one deadline |
| model retries | 5 | `FORGEL_MODEL_RETRIES` | transient provider failures |
| audit deadline | 900 s | `FORGEL_MODEL_TOTAL_TIMEOUT` at audit build | a whole-change-set audit is one long call |
| audit model errors | 15 | `MAX_AUDIT_ERRORS` in code | repeated provider failure stops with a clear message |
| review verdict retries | 10 | `MAX_REVIEW_RETRIES` in code | malformed reviewer output |
| spec retries | 5 | `MAX_SPEC_RETRIES` in code | malformed writer output |
| controller steps | 10 | `MAX_CONTROLLER_STEPS` in code | a controller that never reaches a terminal state |
| repeated action corrections | 5 | `MAX_REPEAT_CORRECTIONS` in code | a loop that makes no progress |

The controller knows the operation set and receives the current limits in its
context, so reaching one produces an explanation and a next step rather than
a silent stop.
