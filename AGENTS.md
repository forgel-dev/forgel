# AGENTS.md

Canonical instructions for AI agents working on Forgel. `FORGEL.md` adds
Forgel-specific rules and the read order. `CLAUDE.md` is a local compatibility
shim and is not part of the public repository.

## Read First

1. `PLAN.md` — product, architecture, decisions, process, roadmap.
2. `FORGEL.md` — native context file and read order.
3. `CONTRIBUTING.md` — contribution, DCO, tests.
4. `jurisdiction/README.md` — jurisdiction packs and the compliance disclaimer.

## Project Rules

- Public artifacts are in English (D-025). Code identifiers are English.
- The core, SDK, official plugins, templates and schemas are Apache-2.0.
  Generated project code belongs to the user.
- The orchestrator is deterministic; the LLM works only inside a step.
- Roles have clean context: spec writer, developer, reviewer, QA, acceptor.
- Artifacts in git are the source of truth; memory is an index.
- Process prohibitions live in code (gates, ledger, runners), not only in prose.
- Prompts describe the state, the task and the constraints. Never embed
  concrete scenarios, expected failures or step-by-step scripts; pass the
  evidence and let the model reason from it.
- Work autonomously (D-075). Pre-release work proceeds without confirmation;
  record every assumption in the task and report. Ask only for a material
  fork, an irreversible or production action, or missing access. Finish the
  result, show the evidence, then rework on feedback.
- The runtime owns the context window (D-078). Do not estimate tokens, warn
  about context limits or ask to continue; a session may hand off durable
  state and a new session continues from it.
- Jurisdiction packs are advisory. Never claim legal compliance; the user is
  responsible. The production gate requires the compliance acknowledgement.
- Do not add tool attribution lines or session references to commits, pull
  requests or issues. Keep public history about the product.

## Change Workflow

1. Read the relevant decision and feature documents.
2. For a significant change, open an RFC issue first.
3. Implement one logical change; add a test.
4. Run `make test` and `make lint`.
5. Update `PLAN.md` and related docs when a decision changes.
6. Commit in English, imperative mood, with `git commit -s`.

## Layout

| Path | Purpose |
|---|---|
| `src/forgel/` | Core: orchestrator, ledger, state, registry, CLI |
| `src/forgel/templates/` | Project templates |
| `environment.yaml` | Environment contract for Forgel itself: build, commands, env |
| `environment/` | Dockerfile for Forgel's own sandbox environment |
| `registry/` | Recipe registry data |
| `jurisdiction/` | Jurisdiction pack data |
| `brand/` | Brand assets: mark, palette, ASCII wordmark, GitHub fields |
| `tests/` | `unittest` suite |
| `PLAN.md` | Product and architecture plan |
| `FORGEL.md` | Native Forgel instructions |
| `INTERNAL.md` | Internal notes — gitignored, never commit |

## Guardrails

- Never commit secrets, private project names, customer data or internal docs.
- Do not start external services or cloud resources in tests.
- Do not weaken a test to make it pass; fix the product or the test's premise.
- Do not claim a state you did not verify in this session.
