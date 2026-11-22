# FORGEL.md

Native context file for Forgel. Forgel reads this file first, then `AGENTS.md`,
then `CLAUDE.md` if it is present.

## What Forgel Is

Forgel is an open-source autonomous software studio. The product plan and
decisions live in `PLAN.md`.

## Instruction Files

The project-level `FORGEL.md` and `AGENTS.md` apply to every repository. A
repository may add its own `FORGEL.md` and `AGENTS.md`; those rules are more
specific and take precedence on conflict. Forgel reads both layers.

## Language

All project documents and artifacts are English, regardless of the chat
language: task titles, task descriptions, specifications, plans, QA and
review reports, documentation and commit messages. Chat replies and
clarifying questions follow the user's language. Repository instruction files
may add conventions, but the artifact language stays English.

## Prompts

A prompt is role, state, task, constraints and context provenance. It never
carries a concrete scenario: no failure example, incident, named provider,
tool, credential, environment or step sequence. A fix for one observed case
belongs in the context builder, the role boundary or the runtime, never in
prompt prose.

Each agent receives its own capabilities as structured state. Another run's
report is not this agent's state. The conversation stores the user's dialogue,
this agent's own turns and the user-visible reports, each labeled by producer.

This applies to every prompt: project agent, planner, spec writer, coder,
reviewer, QA, release audit, outcome explainer and conversation compaction.
See [AGENTS.md](AGENTS.md) **Prompt Rules** and [docs/prompts.md](docs/prompts.md).

## Native Rules

- The source of truth for agent instructions is `AGENTS.md`. This file adds
  Forgel-specific rules and the read order.
- Generated projects carry `FORGEL.md` and `AGENTS.md`. Forgel does not generate
  `CLAUDE.md`.
- Jurisdiction packs are advisory. Never claim legal compliance; the user is
  responsible. Production requires the compliance acknowledgement.
- Generated project code belongs to the user.
- All committed project artifacts are English; local working notes outside
  the repository may be Russian.

## Read Order

1. `FORGEL.md` (this file)
2. `AGENTS.md`
3. `CLAUDE.md` (local compatibility shim, not committed)

## Start Here

Read `PLAN.md`, then `CONTRIBUTING.md`. For a significant change, open an RFC.
