# Deploying the Forgel Daemon

This guide runs the Telegram gateway and the daemon on a Linux server. The bot
uses long polling, so it needs no inbound port: outbound HTTPS to Telegram and
to the model endpoint is enough.

## Prerequisites

- Linux host with Docker Engine and Compose v2.
- A Telegram bot token from BotFather and your numeric chat id.
- A model key for an OpenAI-compatible endpoint (DeepSeek by default).
- Optional: a GitHub PAT or GitHub App for `/adopt` and `/github`.
- Start with 1 vCPU, 2 GB RAM and 10 GB disk. Generated projects and QA can
  grow; the `/data` volume is the important one.

## 1. Get the Source

```bash
git clone https://github.com/forgel-dev/forgel.git
cd forgel
cp .env.example .env
chmod 600 .env
```

## 2. Configure `.env`

```dotenv
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_CHAT_IDS=123456789
FORGEL_MODEL_API_KEY=...
FORGEL_MODEL_BASE_URL=https://api.deepseek.com/v1
FORGEL_MODEL_NAME=deepseek-chat
```

The allowlist is mandatory: the bot refuses to start without it and ignores
every other chat. Get your numeric id from a bot such as `@userinfobot`.

GitHub is optional:

```dotenv
FORGEL_GITHUB_TOKEN=...
# or an App:
FORGEL_GITHUB_APP_ID=...
FORGEL_GITHUB_INSTALLATION_ID=...
FORGEL_GITHUB_APP_PRIVATE_KEY_PATH=/data/github-app.pem
```

For an App private key, place the PEM on the persistent volume. One way:

```bash
docker compose run --rm --no-deps --entrypoint sh telegram \
  -c 'cat > /data/github-app.pem' < github-app.pem
docker compose run --rm --no-deps --entrypoint sh telegram \
  -c 'chmod 600 /data/github-app.pem'
```

`FORGEL_GITHUB_APP_PRIVATE_KEY` (inline PEM) also works if your environment
supports multi-line values. Public repositories need no GitHub credential at
all; SSH remotes use the host/container key if you provide one.

Secrets are read from the environment first and `$FORGEL_HOME/secrets.toml`
second. Telegram bots have no end-to-end encryption, so prefer environment
variables on the server; `/secret` is a development convenience.

## 3. Start the Daemon

```bash
docker compose --profile telegram up -d --build telegram
docker compose logs -f telegram
```

The first log lines show `[telegram] ...`, then the bot announces online to
the allowed chats. Send `/help` to it.

Check the installation inside the running container:

```bash
docker compose exec telegram forgel doctor
```

Warnings for Telegram, the model or GitHub are expected only before they are
configured; the process needs Telegram and a model to be useful.

## 4. First Project

From the allowed chat:

```text
/new notes app | A small notes app with a web UI and a health check.
```

or adopt an existing repository:

```text
/adopt https://github.com/owner/repo | Existing backend service
```

A plain text message is a change request: the intake agent turns it into a
task with requirements, acceptance criteria and a repository; the daemon runs
it with the coding agent.

```text
/tasks
/status <project-id>
/use <project-id>
```

## Operations

- Pause/resume: `/pause`, `/resume` or `forgel pause|resume` in the container.
- Restart: `docker compose restart telegram`.
- Logs: `docker compose logs -f --tail=200 telegram`.
- Update: `git pull`, then `docker compose --profile telegram up -d --build telegram`.
  The `/data` volume survives rebuilds.
- Health: `docker compose ps`, logs, and `docker compose exec telegram forgel doctor`.

### Backup

The ledger and every project live in the `forgel-data` volume. A simple
archive:

```bash
docker run --rm -v forgel-data:/data -v "$PWD":/backup \
  busybox tar czf /backup/forgel-data.tgz -C /data .
```

Restore into an empty volume with the reverse command. Stop the daemon first
or accept a SQLite WAL snapshot; WAL can be reconstructed, but a stopped
process is cleaner.

## Security and Limits

- The bot has no inbound port. Restrict SSH, keep the host patched, and do not
  publish `/data`.
- The allowlist is the access control. Never put a token or a private key in a
  project, a task or a git repository.
- Provider budget enforcement is not implemented yet (M1). Use a scoped,
  prepaid provider key with auto top-up disabled. The coding agent has a step
  cap and the gateway is single-threaded, but the provider balance is the
  practical limit.
- The container currently runs as root. Treat it as a single-user control
  plane and isolate it on a dedicated host or network.
- The GitHub App private key and the model key are the most valuable files on
  the server; back up only what you need and rotate tokens if the host is
  compromised.
- The blog e2e in `tests/e2e` is a manual test, not part of the production
  service.

## Known Gaps at This Milestone

- No deploy provider: `/deploy` and production releases are manual.
- No GitHub App creation flow; create the App yourself and install it.
- No multi-user isolation; one installation is one operator.
- Docker QA is not run inside the daemon container by default; projects use
  local QA (`FORGEL_QA_RUNTIME=local`).
