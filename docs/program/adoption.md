# Adoption

- Project: `forgel`
- Mode: brownfield
- Recorded: 2026-11-14T23:33:25+00:00

## Repositories

| Id | Provider | URL | Depends on |
|---|---|---|---|
| main | github | git@github.com:forgel-dev/forgel.git | — |

## Why group repositories

A project groups repositories whose code depends on each other: for example a
frontend consumes a backend contract, or an E2E suite exercises both. The
dependency edges in `program.yaml` are what make the grouping meaningful.

An independent repository can be added to a project; nothing breaks, but Forgel
will maintain it separately. The grouping then adds no coupling.

Forgel does not regenerate adopted repositories. External edits are reconciled
and recorded.
