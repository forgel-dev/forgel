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

- All committed project artifacts are in English (D-025): task titles, task
  descriptions, specifications, plans, reports, documentation and commit
  messages. Chat replies follow the user's language. Code identifiers are
  English.
- Conventions live in plain-text `FORGEL.md` and `AGENTS.md`. Project-level
  files apply to every repository; a repository may add its own files, which
  are more specific and take precedence on conflict.
- The core, SDK, official plugins, templates and schemas are Apache-2.0.
  Generated project code belongs to the user.
- The orchestrator is deterministic; the LLM works only inside a step.
- Roles have clean context: spec writer, developer, reviewer, QA, acceptor.
- Artifacts in git are the source of truth; memory is an index.
- Process prohibitions live in code (gates, ledger, runners), not only in prose.
- Prompts describe the role, the state, the task, the constraints and the
  provenance of the context. Never embed concrete scenarios, expected
  failures, incidents, named providers/tools/credentials/environments or
  step-by-step scripts; pass structured evidence and let the model reason
  from it. See **Prompt Rules** below; they are non-negotiable.
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

## Prompt Rules (Non-Negotiable)

A prompt carries only: role, state, task, constraints and the provenance of
its context. Nothing else. This applies to every prompt: project agent,
planner, spec writer, coder, reviewer, QA, release audit, outcome explainer
and conversation compaction.

1. Never put a concrete scenario in a prompt: no failure example, incident,
   bug, named provider, tool, credential, environment or sequence of steps.
2. Never turn one observed case into prompt prose. Fix the context
   construction, the role boundary or the runtime instead. A prompt is not a
   patch surface.
3. Capabilities are structured state passed to that agent, not text inferred
   from another agent's report.
4. Context is scoped by producer: a run, report or artifact describes the
   agent and environment that produced it, not the current agent.
5. The conversation stores the user's dialogue, this agent's own turns and
   the user-visible reports, each labeled by producer. A report is never
   relabeled as this agent's own state.
6. If a rule cannot be stated without an example, it is not a rule yet.
   Design the data and the boundary.
7. A prompt change that adds a scenario, incident, named
   provider/tool/credential/environment or step-by-step script is rejected in
   review.

The same rule, in longer form, is in [docs/prompts.md](docs/prompts.md).

## Release Rules

- A published tag is immutable. A change after a release is a new version,
  never a rewrite of the released tag.
- The runtime release train computes the next version from the repository's
  tags and `CHANGELOG.md` and publishes it; it never moves an existing tag.
- Agents do not assign, promise or rewrite release versions or tags. The
  release report is the source of truth for the version and publication.
- A release without its audit is not published.

## Runtime Process Model

The main chat agent receives the runtime process model from
`src/forgel/runtime_model.py` on every prompt: the pipeline, the owner of each
stage, control and human gates, the release policy and the current releases.
A main-chat prompt without this block is incomplete.

- The model is code-owned and tested. Do not duplicate it in prompt prose and
  do not describe the runtime from memory.
- The agent must know how work moves and who owns each stage. Without the map
  it invents a process and gives harmful instructions.
- When a stage, an owner, a gate or the release policy changes, update the
  model and its test in the same change.

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
- Scenario replays (`make scenario`, `make scenario-execute`, `forgel
  scenario`) use the configured real model and spend tokens. They are outside
  `make test` and run only on an explicit request. `make scenario-test` is the
  scripted, token-free sandbox suite.
- Do not weaken a test to make it pass; fix the product or the test's premise.
- Do not claim a state you did not verify in this session.
