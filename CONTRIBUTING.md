# Contributing to Forgel

Thanks for your interest. Forgel is pre-alpha; read [PLAN.md](PLAN.md) before making a significant change.

## Ways to Contribute

- **Bug reports** — a minimal reproduction and the expected behavior.
- **RFCs** — for anything that changes the architecture, the plugin contract, the registry format, or the process. Open an issue with the `rfc` label before writing code.
- **Code** — bug fixes, tests, documentation, CLI ergonomics.
- **Plugins and recipes** — see below.
- **Docs** — examples, tutorials, corrections.

## Language

All public artifacts are in English (D-025): issues, pull requests, commit messages, documentation, and code comments. Code identifiers and file names are English.

## Licensing and DCO

- The core, plugin SDK, official plugins, templates and schemas are **Apache-2.0**.
- Inbound contributions are licensed under the same terms as the component they touch (inbound = outbound).
- Every commit must be signed off: `git commit -s`. This certifies the [Developer Certificate of Origin 1.1](https://developercertificate.org/). There is no CLA.

## Development Setup

Requires Python 3.11 or newer.

```bash
git clone https://github.com/forgel-dev/forgel.git
cd forgel
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
make test
make lint
```

`make test` runs unit tests only. Scenario replays are a separate category:
`make scenario` and `make scenario-execute` use the configured real model,
spend tokens and run only on an explicit request; `make scenario-test` runs
the sandbox core with a scripted model and spends nothing. See
[docs/scenarios.md](docs/scenarios.md).

Run the M0 end-to-end skeleton:

```bash
PYTHONPATH=src python3 -m forgel init "My app" --brief "A minimal SaaS." --home .forgel-demo
PYTHONPATH=src python3 -m forgel run <project-id> --home .forgel-demo
```

The run creates the project under `.forgel-demo/`, advances the pipeline, and writes a staging descriptor. The pipeline parks at the staging approval gate. Inspect and close it with:

```bash
PYTHONPATH=src python3 -m forgel status <project-id> --home .forgel-demo
PYTHONPATH=src python3 -m forgel approve <project-id> --scope staging
PYTHONPATH=src python3 -m forgel run <project-id> --home .forgel-demo
```

`forgel telegram` runs the same core behind a Telegram chat interface; see the
README. It needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_CHAT_IDS` and is
closed to every other chat.

## Project Layout

| Path | Purpose |
|---|---|
| `src/forgel/` | Core: orchestrator, ledger, state machine, registry, CLI |
| `src/forgel/templates/` | Project templates used by recipes |
| `plugins/official/` | Official plugins (created in M2) |
| `registry/` | Recipe registry data |
| `tests/` | `unittest` suite |
| `docs/` | Public documentation |
| `PLAN.md` | Product and architecture plan |
| `INTERNAL.md` | Internal notes — gitignored, never committed |

## Prompts

Prompts are code and are reviewed like code. A prompt carries only role,
state, task, constraints and the provenance of its context.

- Never add a concrete scenario: no failure example, incident, named provider,
  tool, credential, environment or step-by-step script.
- Never encode a fix for one observed case as prompt prose. Fix the context
  construction, the role boundary or the runtime instead.
- Capabilities are structured per-agent state, not text inferred from another
  agent's report.
- Context is scoped by producer. The conversation stores the user's dialogue,
  this agent's own turns and user-visible reports, each labeled by producer.
- If a rule needs an example to be understood, it is not a rule yet; design
  the data and the boundary.
- The main chat agent's prompt includes the runtime process model from
  `src/forgel/runtime_model.py`. When a stage, owner, gate or release-policy
  line changes, update the model and its test in the same change.

This applies to every prompt in the engine and to every generated project
instruction file. The canonical text is in [AGENTS.md](AGENTS.md) **Prompt
Rules**, [FORGEL.md](FORGEL.md) and [docs/prompts.md](docs/prompts.md).

## Pull Requests

1. Open an issue or RFC first for a significant change.
2. Keep one logical change per pull request.
3. Add a test for behavior; update docs for user-facing changes.
4. Run `make test` and `make lint`.
5. In the PR description, state: what changed, why, how it was tested, and any risks.
6. If a prompt changed, confirm no concrete scenario, incident, named
   provider/tool/credential/environment or step-by-step script was added, and
   that context is scoped by producer.

Small fixes (typos, broken links) can go straight to a PR.

## Commit Messages

- **Never commit the whole working tree.** Stage only the files the task's
  specification lists (D-097). Unrelated changes are never attributed to a
  task and never committed with it. Committing everything makes the reviewer
  reject the extra file and the cycle never ends; this has been tried and
  rejected repeatedly. Never do it.
- English, imperative mood, subject at most 72 characters.
- The body explains **why**, not what the diff already shows.
- Sign off with `-s`.
- Conventional Commits are welcome but not required.

## Plugins and Recipes

The plugin SDK and the conformance kit land in M2. Until then, propose a plugin or recipe in an issue with:

- the capability it provides;
- the manifest it would declare;
- how it would pass `provision → apply → verify → rollback → destroy`;
- the license (Apache-2.0 for official plugins).

A recipe is a named composition of plugins, not free-form code. The registry is data; changes require a conformance report.

## Security

Do not open a public issue for a vulnerability. Use the repository's **Security → Report a vulnerability** flow (GitHub Security Advisories). Include a minimal reproduction and the affected version.

## Code of Conduct

Be respectful, assume good faith, and do not harass anyone. Maintainers may remove harmful content and restrict participation. A formal code of conduct will be published before the public alpha.

## Good First Issues

Issues labeled `good first issue` are scoped for new contributors. If you want to take one, comment on it so work is not duplicated.
