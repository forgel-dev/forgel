# Deploying the Forgel Daemon

The recommended path is one local command. `forgel deploy` reads
`.env.deploy`, talks to the server over SSH, prepares the image, writes the
production Compose file and a `0600` runtime `.env`, starts the service and
runs `forgel doctor`. No manual server configuration and no env editing over
SSH.

## Server Requirements

The server needs only:

- SSH access;
- Docker Engine;
- Docker Compose v2 (v1 is detected as a fallback).

Nothing else is required. `DEPLOY_HOST` can be an `~/.ssh/config` alias. `DEPLOY_USER`, `DEPLOY_PORT` and `DEPLOY_SSH_KEY` are optional: leave them empty and ssh uses the config, the agent and the default key (for example `~/.ssh/id_rsa`). The SSH user should be root, or have passwordless sudo for installation and Docker access (directly or through `sudo -n`).

`forgel deploy up` checks this before doing anything:

- if Docker or Compose is missing, it prints a warning and asks permission to
  install them;
- with root or passwordless `sudo -n`, it installs from `get.docker.com` or
  the distribution package manager, starts the daemon and adds the SSH user to
  the `docker` group where appropriate;
- without those privileges it stops and prints the exact commands for the
  detected distribution or asks the administrator to install Docker manually.

Flags: `--yes` allows installation without a prompt; `--no-install` never
installs and only reports. Without a TTY, the command asks for `--yes` instead
of hanging on a prompt.

The same check runs for `status`, `logs`, `restart` and `backup` with
installation disabled: they report a missing Docker/Compose instead of
installing it.

## One Command (Recommended)

```bash
forgel deploy init          # creates .env.deploy with mode 0600
$EDITOR .env.deploy
forgel deploy up
```

`.env.deploy` is local and gitignored. It has two parts:

- `DEPLOY_*` — where and how to deploy; never sent to the container;
- everything else — runtime configuration, written to the remote `.env`
  with mode `0600`.

```dotenv
DEPLOY_HOST=example.com
DEPLOY_USER=root
DEPLOY_SSH_KEY=~/.ssh/id_ed25519
DEPLOY_DIR=/srv/forgel
DEPLOY_BUILD=auto
DEPLOY_IMAGE=ghcr.io/forgel-dev/forgel:latest
DEPLOY_PUSH=false
# DEPLOY_REGISTRY_USER / DEPLOY_REGISTRY_TOKEN for a private registry
# DEPLOY_APP_KEY_FILE=./github-app.pem

TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_CHAT_IDS=123456789
FORGEL_MODEL_API_KEY=...
FORGEL_MODEL_BASE_URL=https://api.deepseek.com/v1
FORGEL_MODEL_NAME=deepseek-chat
FORGEL_GITHUB_TOKEN=...
```

The target server needs only Docker Engine and Compose v2. The SSH user must
be able to run Docker (root or the `docker` group).

### Image Strategy

| `DEPLOY_BUILD` | Behavior | When |
|---|---|---|
| `remote` | Sends the build context and builds on the server | First self-host, no registry |
| `local` + `DEPLOY_PUSH=true` | Builds and pushes locally, pulls on the server | Versioned releases, GHCR |
| `auto` | `local` if push is enabled, otherwise `remote` | Default |

Publishing an image is not strictly required. For a clean release process it
is recommended: CI builds `ghcr.io/<owner>/<repo>:<tag>` and the server only
pulls it. The local utility can also build and push with
`DEPLOY_REGISTRY_USER` / `DEPLOY_REGISTRY_TOKEN`; the token is passed on stdin
and never appears in argv or logs.

A GitHub Actions workflow for GHCR is in
`.github/workflows/image.yml`; it runs on `v*` tags and manual dispatch. Point
`DEPLOY_IMAGE` at that image, set `DEPLOY_BUILD=local`, `DEPLOY_PUSH=true` and
the registry credentials.

### What `forgel deploy up` Does

1. Checks SSH, remote Docker and Compose; offers the install described above.
2. Builds remotely or builds/pushes locally.
3. Uploads `compose.yaml`, the filtered `.env` and an optional App private key
   through an SSH tar stream; the remote directory is `0700`, `.env` is
   `0600`.
4. Runs `docker compose up -d --remove-orphans`.
5. Shows `docker compose ps` and the output of `forgel doctor` inside the
   container.

Configuration changes are the same loop: edit `.env.deploy`, run
`forgel deploy up`. The remote `.env` is replaced and the container is
recreated. Do not edit files on the server by hand; the next deploy overwrites
them.

### Operations

```bash
forgel deploy status
forgel deploy logs            # --follow for streaming
forgel deploy restart
forgel deploy backup          # writes forgel-backup-<timestamp>.tgz locally
```

The backup runs `tar` inside the running container over `/data` and stores the
archive locally with mode `0600`. The named volume `forgel-data` holds the
ledger and every project.

### GitHub App Key

Set `DEPLOY_APP_KEY_FILE=./github-app.pem`. The key is uploaded to
`<DEPLOY_DIR>/secrets/forge-github-app.pem` with mode `0600`; the Compose file
mounts `./secrets` read-only at `/run/secrets` and the runtime sets
`FORGEL_GITHUB_APP_PRIVATE_KEY_PATH`. Do not put the key in the runtime env.

## Container Rights and Project Environments

The image starts as root only for one action: make the `/data` volume writable,
then drop to the unprivileged `forgel` user (UID/GID `10001`) through
`deploy/entrypoint.sh`. The long-running daemon and every agent command run as
`10001`.

What the runtime user can do:

- read and write `/data` (the ledger, projects, configuration);
- clone and push repositories through git with the configured HTTPS/PAT
  credentials or a key mounted by the operator;
- run project commands from the allowlist (`python`, `node`, `npm`, `make`,
  read-only git) inside the container;
- run local tests and an app as a local process.

What it cannot do:

- become root;
- access the host filesystem;
- access the host Docker socket — it is deliberately not mounted;
- see the daemon's secret environment in agent commands (`_safe_env` strips
  it).

`FORGEL_SANDBOX=local` is the only implemented mode. It is **single-tenant**:
all projects live under the same `/data` and the same UID, so a hostile project
command could read another project's files. Do not run untrusted projects on a
shared installation. A per-project sandbox (a separate Docker daemon or remote
sandbox, project-only mounts, labels, network and resource limits) is the next
milestone; the core refuses `FORGEL_SANDBOX=docker` until it exists.

The environment contract is an OCI image or build context plus a small
`environment.yaml` with `setup`, `test` and `e2e` commands. The core has no
per-language adapters; official recipes are starting points, and the agent may
author a standard environment definition for a missing stack with review. In
the local fallback QA runs the contract's `test` and `e2e` commands on the host
and skips `setup`; a malformed contract fails QA instead of falling back, while
a project without one keeps the legacy e2e script.

Project environments that need containers (Postgres, Redis, a compose stack)
require that future sandbox. The daemon never mounts the host
`/var/run/docker.sock`; doing so would give project code root-equivalent
control of the host. For a trusted single-user host, run those services
outside Forgel and point the project at them explicitly; for multi-tenant,
wait for the sandbox.

### Secrets

- Keep `.env.deploy` at `0600`. It contains the bot token, model key and
  optionally GitHub credentials.
- The utility never puts secrets in command arguments or logs. The remote
  `.env` and the secrets directory are `0600`/`0700`.
- Prefer environment variables for daemon secrets in production. The
  `/secret` file lives under `/data` and is readable by the runtime user, so it
  is not a boundary against project code in the local sandbox.
- SSH keys, the provider key and the GitHub App key are the valuable assets;
  rotate them if the laptop or server is compromised.
- The bot uses outbound long polling; no inbound port is needed. Restrict SSH
  and keep the host patched.
- Budget enforcement is not implemented yet (M1). Use a scoped, prepaid model
  key with auto top-up disabled.

## Manual Fallback

Use this for debugging or when SSH-based deployment is not available. On the
server:

```bash
git clone https://github.com/forgel-dev/forgel.git
cd forgel
cp .env.example .env && chmod 600 .env
# edit .env
docker compose --profile telegram up -d --build telegram
docker compose logs -f telegram
docker compose exec telegram forgel doctor
```

This builds from source on the server and uses the repository's root
`compose.yaml`. The `forgel deploy` utility uses the production file in
`deploy/compose.yaml` instead: an explicit image, `restart: unless-stopped`,
bounded logs, an `.env` file and the `secrets` mount.

## First Project

From an allowed chat:

```text
/new notes app | A small notes app with a web UI and a health check.
```

or adopt an existing repository:

```text
/adopt https://github.com/owner/repo | Existing backend service
```

A plain text message is a change request: the intake agent turns it into a
task with requirements, acceptance criteria and a repository; the daemon runs
it with the coding agent. `/tasks` shows the queue.

## Known Gaps

- No deploy provider: production releases are manual.
- No GitHub App creation flow; create and install the App yourself.
- One installation is one operator; no multi-user isolation.
- Docker QA is not run inside the daemon container by default; projects use
  local QA.
- The blog e2e in `tests/e2e` is a manual test, not part of the service.
