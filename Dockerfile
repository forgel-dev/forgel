FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY registry ./registry
COPY jurisdiction ./jurisdiction

RUN pip install --no-cache-dir .

ENV FORGEL_HOME=/data \
    FORGEL_REGISTRY=/app/registry/recipes.json \
    FORGEL_JURISDICTIONS=/app/jurisdiction \
    FORGEL_QA_RUNTIME=local

VOLUME ["/data"]

ENTRYPOINT ["forgel"]
