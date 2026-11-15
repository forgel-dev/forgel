# __PROJECT_NAME__

A Django REST Framework API skeleton with Postgres and S3-compatible object
storage, runnable with a single Docker Compose command.

## Structure

- `api/` — Django project. `config/` holds settings, URL configuration and the
  bucket bootstrap; `health/` serves the `GET /healthz` liveness endpoint;
  `tests/` holds the Django test suite.
- `compose.yaml` — the API image, Postgres and MinIO. The API container creates
  the bucket named by `S3_BUCKET` on startup.
- `environment.yaml` — Forgel's environment contract: `setup` installs the
  requirements and `test` runs `python manage.py test` from `api/` through
  `scripts/test.sh`.
- `.env.example` — every variable the stand needs, with placeholder values.

## Configuration

All settings come from the environment (see `api/config/settings.py`):

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`.
- `DATABASE_URL`, or the discrete `POSTGRES_DB`, `POSTGRES_USER`,
  `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`. Without either the
  project falls back to an in-memory SQLite database, so the tests and a bare
  `manage.py runserver` work without a database server.
- `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_REGION`.
  Without `S3_BUCKET` the default file-system storage is used, so nothing needs
  object storage to start.
- `MINIO_IMAGE` (compose only) names the object-storage server image; override
  it to pin a release or to pull from another registry.

## Run the stand

```sh
cp .env.example .env   # then replace the placeholders
docker compose up --build
curl -i http://127.0.0.1:8000/healthz
```

The API container applies migrations, creates the S3 bucket when it is missing
and then serves the project on port 8000. Postgres and MinIO expose their ports
from `.env` (`POSTGRES_PORT`, `S3_PORT`, `S3_CONSOLE_PORT`).

## Tests

```sh
sh scripts/test.sh   # or: cd api && python manage.py test
```

No Postgres server and no object storage are needed for the tests.
