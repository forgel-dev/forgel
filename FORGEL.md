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

## Releases

A published tag is immutable: a change after a release is a new version, never
a rewrite of the released tag. The runtime release train computes the next
version from the repository's tags and `CHANGELOG.md` and publishes it; it
never moves an existing tag. Agents do not assign, promise or rewrite release
versions or tags. The release report is the source of truth for the version
and publication. A release without its audit is not published.

## Runtime Process Model

The main chat agent receives the runtime process model from
`src/forgel/runtime_model.py` on every prompt: the pipeline, the owner of each
stage, control and human gates, the release policy and the current releases.
A main-chat prompt without this block is incomplete. The model is code-owned
and tested; the agent must know how work moves and who owns each stage,
otherwise it invents a process. Update the model when a stage, owner, gate or
the release policy changes.

## Native Rules

- The source of truth for agent instructions is `AGENTS.md`. This file adds
  Forgel-specific rules and the read order.
- Generated projects carry `FORGEL.md` and `AGENTS.md`. Forgel does not generate
  `CLAUDE.md`.
- Jurisdiction packs are advisory. Never claim legal compliance; the user is
  responsible. Production requires the compliance acknowledgement.
- Generated project code belongs to the user.
- **Never commit the whole working tree.** A task commit contains only the
  change set selected for that task (D-097). Unrelated changes are never
  staged, committed or attributed to a task. Committing everything makes the
  reviewer reject the extra file and the runtime commit again, forever. This
  has been tried and rejected repeatedly; do not do it, ever.
- **A specification states behavior, never an implementation file list.**
  There is no "Affected Files" section. The developer and the reviewer judge
  the change as a whole: every file the task needs is present, the change is
  internally consistent, and unrelated, temporary, debug or generated files
  are excluded (D-104).
- All committed project artifacts are English; local working notes outside
  the repository may be Russian.

## Read Order

1. `FORGEL.md` (this file)
2. `AGENTS.md`
3. `CLAUDE.md` (local compatibility shim, not committed)

## Start Here

Read `PLAN.md`, then `CONTRIBUTING.md`. For a significant change, open an RFC.
