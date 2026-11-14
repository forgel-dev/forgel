FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY registry ./registry
COPY jurisdiction ./jurisdiction

RUN pip install --no-cache-dir ".[github]"

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
