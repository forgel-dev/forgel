# Forgel

Open-source autonomous software studio. Describe a product; get a working web app with specs, independent QA, and a deploy — on your infrastructure, with your model key.

**Status:** pre-alpha. The plan is in [PLAN.md](PLAN.md).

## Try the M0 Skeleton

Requires Python 3.11+.

```bash
make demo
```

This creates `.forgel-demo/` and runs the full pipeline from brief to staging.
The same commands are available in a local console — no Telegram bot, no token
and no server:

```bash
make chat
# forgel> /new My app | A minimal SaaS with a landing page and a health check
# forgel> /status
# forgel> /approve <project-id> staging
```

For continuous work without a prompt, run the daemon in another terminal:

```bash
PYTHONPATH=src python3 -m forgel daemon --home .forgel-demo
```

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

**Autonomy vs gates.** The agent does not ask questions while it works. Before
a release it decides reversible details itself, records every assumption and
shows a finished result with evidence. It stops only for a material fork, an
irreversible or production action, or missing access. The staging and
production approvals are checkpoints on a finished result, not an
interrogation; production data, payments and secrets stay human-gated.

**Context and handoff.** The runtime owns the context window. A long task runs
in sessions; when the estimated prompt approaches the budget or a session
hits its step cap, Forgel writes durable state to
`docs/program/agent/<task>.state.md` and starts a new session from it. The
model is told not to estimate tokens or ask to continue. The report shows the
session count, handoffs and estimated usage. The window defaults to 1M tokens;
tokens are counted with `tiktoken` when installed (`pip install
'forgel[tokens]'`, included in the Docker image) and with a conservative
fallback otherwise. A task left `running` by a crash is requeued at the next
daemon start and continues from its state file, up to three resumes. See
`PLAN.md` §7.15.

**Task QA and milestones.** A task that the coding agent reports done is
followed by an independent QA pass over the project's `environment.yaml`
(`test`, then `e2e`) in the sandbox; a red gate fails the task with
`docs/program/agent/<task>.qa.md`. `forgel plan` (or `/plan`) turns a
milestone goal into an ordered backlog of tasks with explicit requirements,
acceptance and dependencies; `--dry-run` previews it, and the daemon runs a
task only after its dependencies are done. The plan is committed as
`docs/program/plans/<id>.md`. See `PLAN.md` §7.15.

**Models and cost.** `deepseek-flash` is the default for every role; a more
expensive model is an explicit configuration choice. Autonomous work defaults
to DeepSeek's off-peak hours, when the rate is half the peak rate. During a
peak window the daemon holds model-using work and free text answers with the
window close time; `/peak` shows the schedule, `/peak always` and `/peak
off_peak` set the policy, and `FORGEL_PEAK_HOURS` overrides the windows. See
`PLAN.md` §7.16.

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
/config set models.default deepseek-flash
/config set models.base_url https://api.deepseek.com/v1
```

### Model and agent

The project agent talks to an OpenAI-compatible endpoint. In production the
key and URL come from the environment or the local secret store:

```bash
export FORGEL_MODEL_API_KEY=...
export FORGEL_MODEL_BASE_URL=https://api.deepseek.com/v1   # optional
export FORGEL_MODEL_NAME=deepseek-flash                     # optional
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

### Adopt an Existing Repository

`/new` generates a project from a template. To bring an existing repository
under Forgel without regenerating it:

```text
/adopt <url> [| brief]
/adopt https://github.com/owner/backend
/adopt git@github.com:owner/backend.git
/adopt owner/backend
/adopt /srv/repos/backend | Internal billing service
```

A bare `owner/repo` is treated as a GitHub shorthand; for a local path use an
absolute path or prefix it with `./`.

The repository is cloned into `repos/main`, receives a `forgel-baseline` tag,
and the control repository `program/` gets `forgel.toml`, `program.yaml`,
`FORGEL.md`, `AGENTS.md` and `docs/program/adoption.md`. The adopted
repository's current branch becomes `git.base_branch`, so a `master` repository
publishes to `master` without extra configuration. The project is brownfield:
the template pipeline never runs and Forgel never regenerates the code.

Add related repositories or change their edges:

```text
/repo add <url> [id] [depends_on=<id>]
/repo create <id> [org=<name>] [public] [depends_on=<id,id>] [| description]
/repo publish [id] [org=<name>] [public]
/repo link <id> depends_on=<id,id>
/repo list
```

```text
/repo add https://github.com/owner/frontend web depends_on=main
/repo create billing org=acme depends_on=main | Billing service
/repo publish                 # create GitHub remotes for the local repositories
/repo add https://github.com/owner/infra infra
/repo link web depends_on=main
```

`repo create` creates the GitHub repository, initializes the local repository
with `README.md`, `FORGEL.md` and `AGENTS.md`, registers it in `program.yaml`,
pushes it and records a ledger event. `repo publish` creates remotes for
existing local repositories. Both are private by default and never delete a
repository or force-push. The organization comes from `[git] org`,
`--org`/`org=`, or `FORGEL_GITHUB_ORG`; otherwise Forgel uses the single
GitHub owner already present in the project, and a PAT falls back to the
account's login.

Link repositories only when their code depends on each other: a frontend
consumes a backend contract, an E2E suite exercises both, an infrastructure
repository deploys a specific backend. Independent repositories can be added
to one project; nothing breaks, but Forgel maintains them separately and the
grouping adds no coupling.

**GitHub authentication.** Three sources, resolved in this order:

1. **GitHub App** (preferred): short-lived installation tokens. Create an App
   with Contents read/write, Pull requests read/write, Checks read and
   Metadata read, plus Administration write when Forgel should create
   repositories, then install it. Set `FORGEL_GITHUB_APP_ID`,
   `FORGEL_GITHUB_INSTALLATION_ID` (optional when there is one installation)
   and the private key as a mounted `0600` file
   (`FORGEL_GITHUB_APP_PRIVATE_KEY_PATH`) or an inline PEM. App auth needs
   `pip install 'forgel[github]'`; the Docker image includes it.
2. **PAT** (M0.5 bootstrap): fine-grained Contents read/write (plus
   Administration write for repository creation) or classic `repo`, via
   `FORGEL_GITHUB_TOKEN`, `/secret set github.token`, or
   `forgel secret set github.token`.
3. **SSH/deploy key**: clone, fetch and push only; no API token, so pull
   requests need one of the first two.

Public HTTPS clones need no credentials, and credential-bearing URLs are
rejected. Hosting sits behind a provider contract, so GitLab, Gitea or a
private server can be added without touching the core.

### Publish and Merge

Forgel publishes through a feature branch and a pull request. It never pushes
to the base branch and never force-pushes. `[git]` in `forgel.toml` controls
the policy:

```toml
[git]
provider = "github"
auth = "auto"            # auto | github_app | pat | deploy_key
base_branch = "main"
branch_prefix = "forgel/"
draft_pr = true
require_ci = true
merge = "auto"           # auto | human
auto_revert_on_failure = true
```

```bash
forgel github status <project>
forgel github publish <project> --title "Add dark mode" [--repo api] [--commit "message"]
forgel github merge <project> [--pr 12]
```

```text
/github
/github publish [repo] <title>
/github merge [repo] [pr]
```

`publish` fetches, rebases onto `origin/<base>` (a conflict stops the run),
commits when a message is given, pushes the feature branch, opens a draft PR
and records it in `docs/program/git/report.md` and the ledger. With
`merge=auto` it waits for checks and merges only when they are green; with
`require_ci=true` and no CI checks it stops at `no_ci`. `merge=human` leaves
the pull request open. Post-merge smoke and auto-revert are not implemented
yet; the config field is reserved.

## Coding Agent

Queue a task for a project:

```bash
forgel task add <project> \
  --title "Minimal blog platform" \
  --require "Build a blog in Python with the standard library" \
  --require "Tests run with python -m unittest discover -s tests" \
  --accept "The external validator exits 0" \
  --test-command "python -m unittest discover -s tests"
forgel task list <project>
forgel task accept <project> --task <id> [--notes "..."]
forgel task reject <project> --task <id> [--notes "..."]
```

A plain chat message is not just conversation: the project agent classifies it,
and a change request becomes a pending task with explicit requirements,
acceptance criteria, a target repository, optional constraints, a test command
and recorded assumptions. In a multi-repository project the agent picks the
most likely repository and states why instead of asking; a wrong assumption is
corrected by the next request. The bot reports the task id, and `/tasks` lists
it. Cancel a queued task with `/task cancel <id>`.

For a milestone, `forgel plan <project> --goal "..."` (or `/plan <goal>` in the
chat) asks the model for an ordered backlog of small tasks with explicit
requirements, acceptance and dependency edges; `--dry-run` previews it. The
plan is committed as `docs/program/plans/<id>.md`, and the daemon runs a task
only after its dependencies are done.

The daemon picks up pending tasks and runs the coding agent inside the
project's repository. The model returns one JSON action per turn (list, read,
write, delete, run, done, fail). The runtime keeps paths inside the repository,
uses a small command allowlist, strips secret environment variables, caps the
step count, runs the final test command, commits with a bot message, writes
`docs/program/agent/<task>.md` and records a ledger event. It refuses to commit
secret-looking files. After a done task the independent QA pass runs the
environment contract again (sandbox or local); a red gate fails the task and
writes `docs/program/agent/<task>.qa.md`. Then an independent reviewer with a
clean context judges the committed diff against the explicit requirements and
writes `docs/program/agent/<task>.review.md`; a failed verdict fails the task.
A passing review leaves the task in `review` for a human decision (the default
`FORGEL_TASK_ACCEPT=human`); `forgel task accept|reject` or `/task
accept|reject` records it. Set `FORGEL_TASK_ACCEPT=auto` to accept green
reviews automatically; an errored review never auto-accepts.

Failures are handled by kind: infrastructure failures are retried
(`FORGEL_TASK_RETRIES`), QA/review rejections go back for rework with the
feedback (`FORGEL_TASK_REWORKS`), external causes stop and ask a human, and an
exhausted budget quarantines the task and blocks its dependents. When a review
rejection repeats, an external arbiter decides whether the change or the
acceptance criteria are wrong; `criteria` fails the task with a proposed
revision. `forgel task retry` requeues a failed task and releases its
dependents; `forgel plan --status` shows the milestone state.

Tasks carry executable acceptance checks, run by QA and stored outside the
agent's write scope. A criterion that cannot be automated is marked
`verification: review` and cannot be auto-accepted. Tests are normally only
added; a deletion needs a recorded reason (`removed`, `replaced` with the
replacement, or `wrong`), and an unjustified deletion fails the review.

From the chat: send a plain message to the selected project to queue a change;
`/plan` decomposes a milestone; `/tasks` shows the queue; `/task accept|reject`
records a review decision; `/task cancel <id>` cancels a pending task.

Free local runs can use a scripted model or a subagent bridge instead of a
provider key; a production run uses `FORGEL_MODEL_API_KEY`. The manual blog e2e
and its acceptance criteria are in [tests/e2e/README.md](tests/e2e/README.md);
it is run on explicit instruction and not part of `make test`.

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

Deploy it from your laptop with one command:

```bash
forgel deploy init          # creates .env.deploy
$EDITOR .env.deploy
forgel deploy up
```

The utility reads `.env.deploy`, talks to the server over SSH, builds the image
remotely or pushes it to a registry, uploads the production Compose file and a
`0600` runtime `.env`, starts the service and runs the doctor. The server needs
only SSH, Docker and Compose: if they are missing, the utility warns and asks
permission to install (root or passwordless sudo); otherwise it prints the
manual commands. Edit the same file and run `forgel deploy up` to change
configuration; `status`, `logs`, `restart` and `backup` are available too.
Image publishing to GHCR is optional; see [docs/deploy.md](docs/deploy.md).

The manual Compose path is still available:

```bash
cp .env.example .env    # set the token and your chat id
docker compose --profile telegram up -d --build telegram
```

The bot and the ledger share the `/data` volume, so state survives restarts.
The daemon runs from the image; stopping the process is a deployment action,
not a chat command.

## Configuration

- `forgel.toml` — project config: QA runtime, jurisdiction pack, model policy, context window, peak policy, budget.
- `environment.yaml` — the project environment contract: image or build, the `setup`, `test`, `e2e` commands Forgel runs, and optional `env`. It sits in the control repository, or in the repository itself for a single-repository project. The core carries no per-language commands. See `PLAN.md` §7.13.
- `FORGEL.md` → `AGENTS.md` → `CLAUDE.md` — instruction files, read in that order.
- `forgel config <project-id>` — show the effective project config.
- `forgel context <project-id> [--raw]` — show the resolved context files and their priority.
- `forgel doctor` — check the home, registry, ledger, Telegram, model, GitHub and tools before a deployment. See [docs/deploy.md](docs/deploy.md).

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

For a brownfield project, reconcile does not start the template pipeline:
`accept` and `ignore` commit the accepted changes to the repository baseline,
`rollback` restores the files, and `fix` records the defect. The same decisions
are available from the chat with `/sync` and `/reconcile`.

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

Core, plugin SDK, official plugins and templates: Apache-2.0. Generated project code belongs to the user. See [LICENSE](LICENSE).

## Agent Instructions

- [AGENTS.md](AGENTS.md) — cross-harness canon.
- [FORGEL.md](FORGEL.md) — native Forgel instructions, read first.

## Contributing

Public roadmap, RFC process, DCO instead of CLA. See [PLAN.md](PLAN.md) §14.
