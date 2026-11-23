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
- **NEVER commit the whole working tree.** A task commit contains only the
  change set selected for that task (D-097). Unrelated changes are never
  staged, committed or attributed to a task. Committing everything puts
  unrelated files into the task; the reviewer rejects the extra file; the
  runtime commits again; the cycle never ends. This has been tried and
  rejected repeatedly. Do not do it, ever.
- **A specification states behavior, never an implementation file list.**
  There is no "Affected Files" section. The developer and the reviewer judge
  the change as a whole: does it include every file the task needs to work,
  is it internally consistent, and does it exclude unrelated, temporary,
  debug or generated files? A hard file list was the root of endless
  rejections: a correct but unlisted file was dropped or rejected forever.
- **Every uncommitted product file gets one decision at completion (D-105):**
  commit (needed), revert (temporary or debug work made for the task),
  ignore (a useful artifact that must not be in the repository; add it to
  `.gitignore` and commit the rule), or escalate (unrelated; leave it
  uncommitted with a reason for the planner). No file is silently left or
  silently committed.
- **Documentation is text and is verified by review (D-106).** Never add,
  require or accept a test, guard, assertion or automated check that reads a
  documentation file. A documentation task has review-only checks and no test
  command.
- **A respec issue is binding (D-107).** The rewritten requirements and
  acceptance remove the option the issue rejected and cannot contradict each
  other; a requirement that permits an option the acceptance forbids is
  invalid. The writer decides the remaining details from the issue and the recorded
  decisions; it never leaves an open alternative or waits for an answer.
- **The project agent may run every runtime operation directly (D-108).**
  drive, task retry/restart/process/qa/review, release resume/audit/finalize
  and set_limit are all available; no stage-specific allowlist hides one. A
  task can be retried or restarted from its requirements in any status —
  running, review or finished — and the runtime does not lock it.

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

## Documentation Rules (Non-Negotiable)

Documentation describes the product's behavior and contracts: commands, API
endpoints, request and response formats, configuration and user-visible
behavior. These are stable interfaces a reader depends on.

Documentation never carries concrete implementation details that change with
the code: internal structure, file layout, algorithm steps, timing or runtime
bounds, test durations, local environment specifics, measurements and other
volatile internals. A detail belongs in documentation only when it is a stable
interface, not when it is a copy of the current implementation.

- If a documented detail diverges from the implementation, the documentation
  is wrong: remove the detail. Do not change code, tune a limit or raise a
  bound to match documentation.
- A reviewer does not require such details; a reviewer reports a documented
  volatile detail as a documentation defect.
- The release audit does not treat the absence of a volatile detail as a
  defect, and does not turn a documentation mismatch into a code task.
- Every role that writes or reviews documentation receives this rule through
  the project and repository instruction files.

**Requirements documents are stricter.** A requirements document — a task
specification or a change request — describes functional requirements only. It
contains no technical detail at all, including an interface, contract,
endpoint, request or response format, schema, command, file, identifier or
runtime step. The permission above to document a stable interface applies to
user documentation; it does not apply to a requirements document.

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
7. Stage only the files this coherent change needs. Never `git add -A`, never
   commit the working tree, never commit a file that belongs to another task
   (D-097). The completion step chooses the exact set from the reviewer's
   context; a needed file the specification omitted is included, an unrelated
   file is left uncommitted.

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
