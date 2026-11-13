# Forgel

Open-source autonomous software studio. Describe a product; get a working web app with specs, independent QA, and a deploy — on your infrastructure, with your model key.

**Status:** pre-alpha. The plan is in [PLAN.md](PLAN.md).

## Try the M0 Skeleton

Requires Python 3.11+.

```bash
make demo
```

This creates `.forgel-demo/` and runs the full pipeline from brief to staging.
The pipeline parks at the staging approval gate; nothing reaches `done`
without a human decision:

```bash
PYTHONPATH=src python3 -m forgel list --home .forgel-demo
PYTHONPATH=src python3 -m forgel status <project-id> --home .forgel-demo
PYTHONPATH=src python3 -m forgel approve <project-id> --scope staging --home .forgel-demo
PYTHONPATH=src python3 -m forgel run <project-id> --home .forgel-demo
PYTHONPATH=src python3 -m forgel serve <project-id> --home .forgel-demo
```

Approvals are recorded in the ledger and in `docs/program/approvals.md` inside
the project's control repository, together with the release the human reviewed.
They are scoped to one generation, so a new generation asks again. Production
approval is only accepted for a completed release and requires
`--accept-compliance-responsibility`. For a multi-repository project the
release is a digest of every repository state; the per-repository SHAs are in
`docs/program/releases/g<generation>.json`.

Run the tests:

```bash
make test
```

Run the core from the Docker image:

```bash
docker compose run --rm forgel demo
```

## Telegram Interface

`forgel telegram` runs the chat gateway and the daemon in one process. It uses
long polling with the standard library and needs no extra services.

```bash
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_ALLOWED_CHAT_IDS=123456789
PYTHONPATH=src python3 -m forgel telegram --home .forgel-demo
```

The gateway is closed by default: it refuses to start without
`TELEGRAM_ALLOWED_CHAT_IDS` and ignores every other chat. One daemon serves
many projects. Each chat selects a project with `/use`; a message without a
command goes to the agent of the selected project. The agent receives only
that project's files, configuration and conversation history.

```text
/new <name> | <brief>     create a project and select it
/projects                 projects, state and the selected one
/use <id>                 select the current project
/status [id]              state, staging, approvals, recent stages

/run [id]                 ask the daemon to run it now
/sync [id]                detect external changes
/reconcile [id] decide    accept|fix|rollback|ignore
/proposals [id]           post-release proposals
/approve [id] [scope]     staging (default) or production
/reject [id] [scope]      reject and stay at the gate

/config                   effective daemon and project settings
/config set <key> <value>
/secret [set|delete] ...  local secret store
/pause, /resume           control the daemon
```

Production approval asks for an explicit compliance acknowledgement with an
inline button. The bot answers with the release SHA and records the decision
in the ledger and `docs/program/approvals.md`.

### Configuration

Configuration has two layers. Daemon settings live in
`$FORGEL_HOME/config.toml` and cover the polling cadence, worker interval and
the model endpoint. Project settings stay in the project's `forgel.toml`:
QA runtime, jurisdiction, model names, budget, release, simplicity and
refactoring policy. `/config` shows every value with its source.

```text
/config set qa.runtime docker
/config set budget.per_feature_usd 20
/config set models.default deepseek-chat
/config set models.base_url https://api.deepseek.com/v1
```

### Model and agent

The project agent talks to an OpenAI-compatible endpoint. In production the
key and URL come from the environment or the local secret store:

```bash
export FORGEL_MODEL_API_KEY=...
export FORGEL_MODEL_BASE_URL=https://api.deepseek.com/v1   # optional
export FORGEL_MODEL_NAME=deepseek-chat                     # optional
```

The current agent is the intake stage: it answers from the project context and
records change requests in `docs/program/requests/`. It does not edit code yet.

For local runs without a model key, `FORGEL_MODEL_MODE=script` reads responses
from `$FORGEL_HOME/model-script.json` (`{"responses": ["..."]}`). This is how a
subagent given the same prompt can stand in for a model call.

### Secrets

Telegram bots have **no end-to-end encryption**: messages pass through
Telegram's cloud. `/secret set` deletes the source message immediately and
stores the value in `$FORGEL_HOME/secrets.toml` with mode `0600`; the value is
never echoed or written to artifacts. Environment variables take precedence.
For production, prefer setting secrets over SSH:

```bash
forgel secret set model.api_key   # reads the value without echo
forgel secret list
```

## Project Layout

New projects use a container:

```
project/
  project.json          machine state: layout, mode, repository ids
  program/              control repository: specs, config, approvals
    program.yaml
    forgel.toml
    FORGEL.md · AGENTS.md
    docs/program/...
    lock.json · staging.json
  repos/
    api/   web/   infra/   e2e/    one real git repository each
```

Every repository has its own history and a `forgel-baseline` tag. External
changes, rollback and the complexity patch are computed per repository and
aggregated into one project report. `program.yaml` points at `../repos/<id>`
from the control repository.

Existing M0 projects keep the flat layout and remain readable. Onboarding an
existing repository (`/adopt`, clone + Forgel config initialization) and the
GitHub provider plugin follow in the next milestone.

Deploy it beside the core with Docker Compose:

```bash
cp .env.example .env    # set the token and your chat id
docker compose --profile telegram up -d --build telegram
```

The bot and the ledger share the `/data` volume, so state survives restarts.
The daemon runs from the image; stopping the process is a deployment action,
not a chat command.

## Configuration

- `forgel.toml` — project config: QA runtime, jurisdiction pack, model policy, budget.
- `FORGEL.md` → `AGENTS.md` → `CLAUDE.md` — instruction files, read in that order.
- `forgel config <project-id>` — show the effective project config.
- `forgel context <project-id> [--raw]` — show the resolved context files and their priority.

## Edit Outside Forgel

Forgel never regenerates or overwrites external work. After editing a generated
project by hand or in another harness:

```bash
forgel sync <project-id>
forgel run <project-id>
```

`sync` records the diff in `docs/program/external-changes.md` and
`docs/program/reconciliation.md`, then asks for a decision:

```bash
forgel reconcile <project-id> --decision accept|fix|rollback|ignore [--notes "..."]
```

- `accept` — document the change in the feature spec.
- `fix` — keep it as a defect; the pipeline blocks at review until it is fixed.
- `rollback` — restore the changed files from the generated baseline.
- `ignore` — record the change and continue without documenting it.

Only then does `forgel run` continue, in a new ledger generation, from `review`.

## What it will do

- Chat interface (Telegram) → requirements → a validated recipe (stack + cloud + integrations).
- Multi-repo project: backend, frontend, infrastructure, E2E.
- Spec-driven development with clean-context roles: spec writer, developer, reviewer, QA, acceptor.
- Independent end-to-end QA and acceptance evidence — not "the agent said it works".
- Jurisdiction packs: legal constraints become default requirements and evidence — not a document attached at the end. A draft pack is usable; production carries an explicit compliance acknowledgement.
- Staging deploy; production behind human gates.
- Plugins for stacks, clouds, QA drivers, models, domain and jurisdiction packs.

## Principles

- **Own it** — your server, your model key, your code.
- **Prove it** — spec → review → independent QA → acceptance; jurisdiction evidence and an auditable trail.
- **Extend it** — plugins and a recipe registry instead of a monolith.

## Not

- Not a code generator: the output is repositories and a running staging environment.
- Not no-code: the code is yours and exportable.
- Not an agency: humans only where the law or a platform requires them.

## Compliance Disclaimer

Forgel is a software development tool, not a law firm. Jurisdiction packs are draft
guidance, may be incomplete or out of date, and are not legal advice. Forgel does not
warrant that a generated product complies with the laws of any jurisdiction. The user
is responsible for regulatory compliance; approving a production deploy confirms that
responsibility. See [PLAN.md](PLAN.md) and [jurisdiction/README.md](jurisdiction/README.md).

## License

Core: AGPL-3.0-or-later. Plugin SDK, official plugins and templates: Apache-2.0. Generated project code belongs to the user. See [LICENSE](LICENSE).

## Agent Instructions

- [AGENTS.md](AGENTS.md) — cross-harness canon.
- [FORGEL.md](FORGEL.md) — native Forgel instructions, read first.

## Contributing

Public roadmap, RFC process, DCO instead of CLA. See [PLAN.md](PLAN.md) §14.
