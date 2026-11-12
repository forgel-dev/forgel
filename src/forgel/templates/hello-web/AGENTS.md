# AGENTS.md

Canonical instructions for agents working on __PROJECT_NAME__.

## Read First

1. `FORGEL.md` — native project instructions.
2. `forgel.toml` — QA, jurisdiction, model and budget settings.
3. `docs/program/features/` — acceptance criteria.

## Rules

- Keep the `Dockerfile` and `docker/docker-compose.qa.yml` working.
- Add a QA scenario for every automatically checkable change.
- Do not add tool attribution lines to commits or pull requests.
- External edits are first-class; run `forgel sync` before continuing.
- Never weaken a test to make it pass; fix the product or the test's premise.
