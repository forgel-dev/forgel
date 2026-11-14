# AGENTS.md

Canonical instructions for agents working on __PROJECT_NAME__.

## Read First

1. `FORGEL.md` — native project instructions.
2. `forgel.toml` — QA, jurisdiction, model and budget settings.
3. `docs/program/features/` — acceptance criteria.

## Rules

- Work autonomously: pre-release work proceeds without confirmation. Record
  assumptions in the task and report. Ask only for a material fork, an
  irreversible or production action, or missing access. Finish the result,
  show the evidence, then rework on feedback. Production data, payments,
  secrets and legal decisions stay human-gated.
- The runtime owns the context window: do not estimate tokens or ask to
  continue; a session may hand off durable state to the next one.
- Keep the `Dockerfile` and `docker/docker-compose.qa.yml` working.
- Add a QA scenario for every automatically checkable change.
- Do not add tool attribution lines to commits or pull requests.
- External edits are first-class; run `forgel sync` before continuing.
- Never weaken a test to make it pass; fix the product or the test's premise.
