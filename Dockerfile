FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY registry ./registry
COPY jurisdiction ./jurisdiction

RUN pip install --no-cache-dir ".[github]"

# The Docker CLI is used only by the per-project sandbox: it talks to a
# separate daemon over DOCKER_HOST. The host socket is never mounted.
ARG DOCKER_CLI_VERSION=27.5.1
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) cli_arch=x86_64 ;; \
      arm64) cli_arch=aarch64 ;; \
      *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${cli_arch}/docker-${DOCKER_CLI_VERSION}.tgz" \
      | tar -xz --strip-components=1 -C /usr/local/bin "docker/docker"; \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 forgel && \
    useradd --uid 10001 --gid forgel --create-home \
    --shell /usr/sbin/nologin forgel

COPY deploy/entrypoint.sh /usr/local/bin/forgel-entrypoint
RUN chmod 0755 /usr/local/bin/forgel-entrypoint

ENV FORGEL_HOME=/data \
    FORGEL_REGISTRY=/app/registry/recipes.json \
    FORGEL_JURISDICTIONS=/app/jurisdiction \
    FORGEL_QA_RUNTIME=local \
    FORGEL_SANDBOX=local

VOLUME ["/data"]

# Starts as root only to chown the volume, then drops to UID 10001.
ENTRYPOINT ["forgel-entrypoint"]
