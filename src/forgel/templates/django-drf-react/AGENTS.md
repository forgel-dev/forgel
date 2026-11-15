# AGENTS.md

Canonical instructions for agents working on __PROJECT_NAME__.

## Read First

1. `FORGEL.md` — native project instructions.
2. `forgel.toml` — QA, jurisdiction, model and budget settings.
3. `docs/program/features/` — acceptance criteria.

## Layout

- `api/` — the Django project (`manage.py`, `config/` settings, `health/` app, `tests/`).
- `compose.yaml` — the API with Postgres and MinIO, all wired through `.env`.
- `environment.yaml` — how Forgel runs `setup` and `test` (from `api/`).

## Rules

- Work autonomously: pre-release work proceeds without confirmation. Record
  assumptions in the task and report. Ask only for a material fork, an
  irreversible or production action, or missing access. Finish the result,
  show the evidence, then rework on feedback. Production data, payments,
  secrets and legal decisions stay human-gated.
- The runtime owns the context window: do not estimate tokens or ask to
  continue; a session may hand off durable state to the next one.
- Keep the `Dockerfile`, `compose.yaml` and `environment.yaml` working.
- Settings are read from the environment; add a variable to `.env.example`
  with a placeholder value, never a real credential.
- The Django tests must keep running without a Postgres server or object
  storage: without `DATABASE_URL`/`POSTGRES_*` settings fall back to SQLite.
- Do not add tool attribution lines to commits or pull requests.
- External edits are first-class; run `forgel sync` before continuing.
- Never weaken a test to make it pass; fix the product or the test's premise.
