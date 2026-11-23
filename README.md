<p align="center">
  <img src="brand/forgel-mark.svg" width="96" height="96" alt="Forgel">
</p>

<h1 align="center">Forgel</h1>

<p align="center"><strong>Brief in. Product out. Your cloud.</strong></p>

<p align="center">
  An open-source autonomous software studio. Describe a product; get a working
  web app with specs, independent QA, and a deploy — on your infrastructure,
  with your model key.
</p>

**Status:** pre-alpha. M0 — Skeleton: done. M0.5 — Self-Hosting: partial — what remains is the self-hosting exit criterion (a Forgel change specified, implemented, reviewed, QA'd and accepted through Forgel itself) and post-merge smoke with auto-revert. Evidence and remaining items: [PLAN.md §10](PLAN.md#10-roadmap).

## One Client

Run `forgel` in the repository you want to hand over. It opens the local
console; there are no separate utilities to remember.

```bash
cd /path/to/repo
forgel setup            # creates .env.local (gitignored)
# put FORGEL_MODEL_API_KEY in .env.local
forgel
forgel> /adopt .
forgel> plan the milestone: bring the project to M1
# the daemon works; then:
forgel> what is happening?
forgel> accept the latest task
forgel> quit
```

After adoption the client is driven in plain language: describe a change, ask
what is happening, say "accept" or "send it back: <reason>", "retry the failed
task", "work in peak hours", "pause". The model chooses the operation; you do
not need to remember commands. `/adopt`, `/new`, `/secret` and `/config` stay
explicit because they are entry points or touch sensitive state.

- `/plan` needs a model key: set `FORGEL_MODEL_API_KEY` in `.env.local` (the
  client loads it automatically), in the environment, or with
  `/secret set model.api_key` inside the client.
- `.env.local` is the local client setup (model, GitHub, task pipeline, peak
  hours, sandbox). SSH and other deployment settings live only in
  `.env.deploy` and are not needed locally; see `docs/deploy.md`.
- After each command the daemon runs until it needs a human: a task awaiting
  acceptance, a stalled or finished milestone, or a scheduled retry (it waits
  through the backoff; Ctrl-C returns to the prompt).
- Answers follow the language of your message. After a task the console
  explains what actually broke and why, using the agent's actions, command
  exits, QA report, review defects and milestone state; it names the concrete
  cause or says which evidence is missing instead of restating the status.
- The home defaults to `FORGEL_HOME` (usually `~/.forgel`).
- Every console command also exists as a `forgel` subcommand for scripts; add
  `--json` for one machine-readable object per call (see
  [Scripted Client](#scripted-client)).

## Scripted Client

Every operation of the local client is also a parameterized `forgel` subcommand
that needs no interactive prompt. With `--json` a command writes exactly one
JSON object to stdout and nothing else; without the flag the human-readable
text is the output, unchanged from before.

```text
forgel say --project <id> --text "..." [--session <key>] [--json]
forgel say "add a health endpoint" [--json]
forgel status <id> [--json]
forgel tasks <id> [--json]
forgel task accept|reject|retry|cancel|add --project <id> [--task <id>] [--json]
forgel plan <id> --goal "..." [--release-class minor] [--dry-run] [--json]
forgel plan <id> --status [--json]
forgel projects [--json]
forgel session [<id>] [--session <key>] [--json]
forgel use <id> [--session <key>] [--json]
forgel history [--session <key>] [--limit N] [--json]
forgel daemon [--once|--loop] [--interval S] [--max-cycles N] [--json]
forgel pause [--json]
forgel resume [--json]
```

The JSON envelope is flat and stable:

| field | meaning |
|---|---|
| `ok` | success flag |
| `kind` | `answer`, `change_request`, `action`, `plan`, `status`, `tasks`, `task`, `projects`, `session`, `use`, `history`, `control` or `daemon` |
| `text` | the reply text a human would see |
| `error` | empty on success, a description otherwise |
| payload | one operation-specific field: `task` (+ `task_id`), `tasks`, `plan`, `project`, `projects`, `history`, `paused` or `cycles` |

A failed call exits with a non-zero status and still writes one JSON object with
`"ok": false` and the reason in `error`; the same reason goes to stderr. The
payload never carries secrets.

`forgel say` is the single free-text entry point. It calls the same
`CommandRouter` the console and Telegram use and reports what the message
became — an `answer`, a `change_request` with the queued task id, a `plan` or a
control `action` — together with the reply text. The CLI layer holds no second
dispatch table.

The active project is a durable engine-side session, so the client keeps no
state between calls. The session key defaults to `local` (the console's chat id
0) and is switched with `--session`: `forgel session <id>` and `forgel use <id>`
set it, `forgel session` reads it back, `forgel projects` marks the selected one,
and `forgel history` returns the recent conversation of the session as JSON.
The full contract is in
[docs/program/commands.md](docs/program/commands.md).

## Try the M0 Skeleton

Requires Python 3.11+.

The local console needs no Telegram bot, no token and no server:

```bash
make chat
# forgel> /new My app | A minimal SaaS with a landing page and a health check
# forgel> /status
# forgel> /approve <project-id> staging
```

The console creates `.forgel-demo/`; the daemon runs the project through the
pipeline to the staging gate.

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
`docs/program/agent/<task>.qa.md`. The `e2e` command is the program gate, not
another unit run: it tests the whole construction, and the planner refuses a
project that needs it (interacting repositories, a frontend/acceptance or
mobile repository, or sibling mounts) without one. The e2e suite
lives in the project's main repository, or in the control repository for a
project that started multi-repo; a red e2e returns to the coding agent with the
command, workdir and output. A database or cache covered by the unit-test
framework does not by itself require a program e2e; a browser, a mobile
simulator/emulator or an external tool without a standard harness is covered by
a real-interface command check in the task specification. A mobile simulator or
emulator is deferrable: when it is absent on the current machine, the e2e step
is `skipped` with instructions and the task is not blocked; heavy tools are
declared in `e2e_requires`. A red environment
`test` is a project failure, not
a code defect, and does not spend a coder rework. `forgel plan` (or `/plan`)
turns a
milestone goal into an ordered backlog of task intents; a separate
requirements writer expands each intent into a formal specification under
`docs/program/specs/<task>.md`, and a plan review checks the whole set against
the goal before queueing. `--dry-run` previews the specifications, and the
daemon runs the plan's tasks in the order the plan lists them. The plan is committed
as `docs/program/plans/<id>.md`. A free-text task that has no formal
specification gets one, plus the external-dependency report, before the coder
starts (`FORGEL_FREE_TEXT_SPEC=0` disables this). See `PLAN.md` §7.15.

**External dependencies.** While writing a specification, the requirements
writer lists every external service, tool, binary, API or format the task
touches. A separate dependency scout resolves each one before the task is
queued: `direct` when a local or test interface is available (with evidence
naming it), `stub` with documentation/source evidence and the stub code, or
`unavailable` when no reliable source exists — which stops planning instead
of guessing. The task record keeps the mode, the rendered specification
carries the stub, the coder follows it, and the reviewer checks the stub code
against the recorded evidence.

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
docker compose run --rm forgel init "My app" --brief "A minimal app."
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

The current agent takes a task end to end:

1. A request in plain language becomes a task with explicit requirements and
   acceptance criteria; for a milestone, `forgel plan` (or `/plan`) decomposes
   the goal into task intents, a separate requirements writer writes a formal
   spec for each, and a plan review checks the plan against the goal before the
   daemon starts the tasks in the order the plan lists them.
2. The agent works on the task in the sandbox: it reads the repository, edits
   the code, commits with a bot message and writes its report to
   `docs/program/agent/<task>.md`.
3. An independent QA pass then runs the commands declared in the project's
   `environment.yaml` (`test`, then `e2e`) in the sandbox, and an independent
   review checks the committed diff against the requirements.
4. A passing review is accepted automatically and the task moves to `done`.
   Set `FORGEL_TASK_ACCEPT=human` only if you want to sign off every task
   yourself: it then waits in `review` until you say "accept" in the console
   (or `forgel task accept`), or "send it back: <reason>" (or `forgel task
   reject`), which returns it for rework with that feedback.

Long tasks run as bounded sessions that hand off state through
`docs/program/agent/<task>.state.md`. See `PLAN.md` §7.15.

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

A **local path** is adopted in place: the folder stays the repository, Forgel
does not clone or copy it, and the process artifacts (`forgel.toml`,
`program.yaml`, `FORGEL.md`, `AGENTS.md`, `docs/program/`) are written into the
repository root and committed to it. `.forgel/` is added to the folder's
`.gitignore` and holds only local state (`project.json`, chat history, agent
home, staging state, caches). The existing `origin` is used; if there is none, Forgel creates a
repository under `FORGEL_GITHUB_ORG` and pushes, or reports that the folder
stays local. The folder is never added as a git remote. This is the normal
way to hand over a repository you already work in: other tools keep using the
same folder.

When a single-folder project grows into a program, move its state into a
separate repository with `/control extract [path]` (or ask in plain language):
the process artifacts leave the product repository and get their own git
history and remote. Projects created as multi-repository from the start
(`/new`) keep their state in the separate `program/` control repository.

**The first folder is the entry point, not a one-repository limit.** A linked
project is a normal multi-repository project: add another local folder with
`/repo add /srv/frontend web depends_on=main`, or create a new repository in a
sibling folder with `/repo create billing path=/srv/billing`. Each entry keeps
its own absolute path in `project.json`, its own git history, its own baseline
and its own environment contract. Tasks, plans and the daemon address a
repository by id exactly as in a container project.

A **remote URL** (`https://…`, `git@…`, `owner/repo`) is cloned into a project
container as before. Either way the repository receives a `forgel-baseline`
tag, the control repository gets `forgel.toml`, `program.yaml`, `FORGEL.md`,
`AGENTS.md` and `docs/program/adoption.md`, and the current branch becomes
`git.base_branch`, so a `master` repository publishes to `master` without
extra configuration. The project is brownfield: the template pipeline never
runs and Forgel never regenerates the code.

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

**GitHub authentication.** The modes are interchangeable, and a failed
source falls back to the next available one:

1. **GitHub App** (preferred on a server): short-lived installation tokens.
   Create an App with Contents read/write, Pull requests read/write, Checks
   read and Metadata read, plus Administration write when Forgel should
   create repositories, then install it. Set `FORGEL_GITHUB_APP_ID`,
   `FORGEL_GITHUB_INSTALLATION_ID` (optional when there is one installation)
   and the private key as a mounted `0600` file
   (`FORGEL_GITHUB_APP_PRIVATE_KEY_PATH`) or an inline PEM. App auth needs
   `pip install 'forgel[github]'`; the Docker image includes it.
2. **PAT or an active session**: a fine-grained token with Contents
   read/write (plus Administration write for repository creation) or a
   classic `repo` token, via `FORGEL_GITHUB_TOKEN`, `GITHUB_TOKEN`,
   `GH_TOKEN`, `/secret set github.token` or
   `forgel secret set github.token`. When no token is set, an active
   `gh auth login` session is used (`gh auth token`).
3. **Git transport without a token**: an SSH key/agent or the host's cached
   HTTPS credential helper handles clone, fetch and push. `deploy_key`
   selects this transport; it cannot open pull requests.

The GitHub API (pull requests, checks, merging, repository creation) needs an
API token from modes 1–2. Without one, `github publish` still pushes the
branch and reports `pushed` with no pull request; `github merge` explains
that an API token is required. A failed App call (for example a DNS failure)
falls back to a PAT or session, and an unreachable API after a push falls
back to the push-only result. URL parsing and the API live in the provider;
git transport lives in the core.

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

## Releases

Every accepted change request is a release. The agent turns the request into a
release train, the planner splits it into tasks, and when every task is
accepted the runtime audits the whole change set and publishes one version in
each repository the request touched. A published tag is never moved: a change
after a release is a new version. A request that depends on several
repositories releases them together; versions still differ per repository.
Before publication the runtime writes the release plan and the audit under
`docs/program/releases/<release_id>/`, the repository gets `CHANGELOG.md` and
`releases/<version>/{plan,release}.md`, then an annotated `v<version>` tag and
the provider release are pushed. Publication retries a failed push and a
missing provider release on later daemon cycles.

The version comes from the repository itself. Release tags and `CHANGELOG.md`
set the base; without release history the first version is `0.1.0`. A patch
release increments the patch number, a minor release (new functionality or
changed behaviour) the minor number. A major release is only meaningful from
`1.0.0` onward: before that a breaking change is still a minor release, and
`1.0.0` is the first product release. A failed audit queues fix tasks in the
same release for its critical and major findings. A failure with nothing
blocking publishes the release; its findings stay in the audit report.

Version manifests are written by the repository's runtime preset, not by the
release train. A repository selects one explicitly with `preset:` in
`program.yaml`, or the runtime detects it from `pyproject.toml`/`setup.cfg`/
`requirements.txt`/`manage.py` (Python), `package.json` (Node) or `Gemfile`
(Rails). The Python preset updates static `pyproject.toml`/`setup.cfg`
metadata and `__version__` constants; the Node preset updates the root and
`apps/*/package.json`; the Rails preset updates `API_VERSION` in
`config/initializers/version.rb`. Presets are data under `presets` in the
registry; a project can add its own manifest layout there and select it by id.

The explicit command remains for a manual release outside the request flow.
It tags every code repository at a committed SHA and, when an API token is
available (GitHub App, PAT or `gh` session), creates the provider release
object — a GitHub release with notes. Without a token the tag is still
created and pushed; the result says `tagged` and names the fallback.

```bash
forgel release <project> --version 1.2.0 [--notes "..."] [--repo api] [--draft] [--generate-notes]
```

```text
/release [--version X] [--notes ...] [--repo ID] [--draft] [--generate-notes]
```

The tag is `v<version>` for a plain SemVer (or the version as given); without
`--version` it is `g<generation>`. Repositories must have no uncommitted
changes; a tag that already exists at a different SHA is refused, while the
same SHA is pushed idempotently. The manifest
`docs/program/releases/<tag>.json` records every repository SHA, the release
digest, release URLs and the staging/production approvals.
`--generate-notes` asks GitHub to build the notes from commits; the default
body lists the released repositories. GitHub Releases use the Contents
read/write permission already required for pushing — the App needs no extra
scope, a fine-grained PAT needs Contents read/write and a classic PAT needs
`repo`. The installation must include the repository; without the permission
the API returns a 403 and the release falls back to a tagged result. This is
the release step after the human-approved staging candidate.

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
it. Cancel any task with `/task cancel <id>`.

For a milestone, `forgel plan <project> --goal "..."` (or `/plan <goal>` in the
chat) asks the planner for an ordered backlog of task intents; a separate
requirements writer expands each intent into a formal specification, and a plan
review checks the whole plan against the goal before queueing. `--dry-run`
previews the specifications. The plan is committed as
`docs/program/plans/<id>.md`, and the daemon runs the tasks in the order the
plan lists them.

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
A passing review is accepted automatically (`FORGEL_TASK_ACCEPT=auto`, the
default); `forgel task accept|reject` or `/task accept|reject` remains
available for manual decisions. Set `FORGEL_TASK_ACCEPT=human` to leave every
green task in `review` for a human. A review-only criterion is judged by the
reviewer; only an errored review needs a human.

Every failure goes to the controlling agent: it sees the failing command, its
exit code and its output, and decides whether to retry, send the work back
with feedback (`FORGEL_TASK_REWORKS=8`), fix a broken check or limit, or stop
and ask a human. An exhausted budget fails the task; with
`FORGEL_PLAN_ON_FAILURE=stop` the rest of its milestone stops too. When a review
rejection repeats, an external arbiter decides whether the change or the
acceptance criteria are wrong; `criteria` fails the task with a proposed
revision. `forgel task retry` requeues a failed task and releases the tasks its
milestone stopped; `forgel plan --status` shows the milestone state.

Tasks carry executable acceptance checks, run by QA and stored outside the
agent's write scope. A criterion that cannot be automated is marked
`verification: review` and judged by the independent reviewer. Tests are
normally only added; a deletion needs a recorded reason (`removed`, `replaced`
with the replacement, or `wrong`), and an unjustified deletion fails the
review.

From the chat: send a plain message to the selected project to queue a change;
`/plan` decomposes a milestone; `/tasks` shows the queue; `/task accept|reject`
records a review decision; `/task cancel <id>` cancels a task in any status —
it leaves the task list, its requirements document is marked cancelled at the
top and is never accepted for work again, and commits it already made stay in
the tree for the release audit to judge.

Free local runs can use a scripted model or a subagent bridge instead of a
provider key; a production run uses `FORGEL_MODEL_API_KEY`. The manual blog e2e
and its acceptance criteria are in [tests/e2e/README.md](tests/e2e/README.md);
it is run on explicit instruction and not part of `make test`.

## Project Layout

A local adoption links the folder in place:

```
my-repo/                 the source folder — the single source of truth
  forgel.toml            process config (committed)
  program.yaml           repository graph (committed)
  FORGEL.md · AGENTS.md  process canon (committed)
  docs/program/...       features, tasks, plans, QA/review evidence (committed)
  .forgel/               gitignored local state only
    project.json         layout, mode, repository ids and paths
    conversation.jsonl · agent-home/ · staging.json
  README.md · src/ · ...  the product, untouched and shared with your tools
```

The process artifacts are part of the repository history; `.forgel` is local
state and is never committed. `program.yaml` points at the repository with a
relative path (`.` for the folder itself). No copy of the code exists.

Remote adoption and template projects use a container:

```
project/
  project.json          machine state: layout, mode, repository ids
  program/              control repository
  repos/
    api/   web/   infra/   e2e/    one real git repository each
```

Every repository has its own history and a `forgel-baseline` tag. External
changes, rollback and the complexity patch are computed per repository and
aggregated into one project report. Existing M0 projects keep the flat layout
and remain readable.

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

## Brand

The mark, palette, ASCII wordmark and the GitHub field texts live in
[brand/README.md](brand/README.md).

## License

Core, plugin SDK, official plugins and templates: Apache-2.0. Generated project code belongs to the user. See [LICENSE](LICENSE).

## Agent Instructions

- [AGENTS.md](AGENTS.md) — cross-harness canon; **Prompt Rules** are binding.
- [FORGEL.md](FORGEL.md) — native Forgel instructions, read first.
- [docs/prompts.md](docs/prompts.md) — prompt discipline: role, state, task,
  constraints and context provenance only; never a concrete scenario.
- The main chat agent receives the runtime process model from
  `src/forgel/runtime_model.py` on every prompt: pipeline, stage owners, gates,
  release policy and current releases. A main-chat prompt without it is
  incomplete.
- [docs/scenarios.md](docs/scenarios.md) — the permanent scenario sandbox:
  real workflows, isolated home and repos, no provider, no push, no release on
  a real remote (`forgel scenario`).

## Contributing

Public roadmap, RFC process, DCO instead of CLA. See [PLAN.md](PLAN.md) §14.
