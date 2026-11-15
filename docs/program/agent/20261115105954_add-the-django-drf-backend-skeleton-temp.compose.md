# django-drf-react template: `docker compose up --build` evidence

The unittest suite never starts Docker (constraint), so the local stand is
verified by the command below. Run it from the repository root and paste the
output into the `Output` section.

## Command

```sh
cd src/forgel/templates/django-drf-react
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec -T postgres psql -U "${POSTGRES_USER:-app}" -d "${POSTGRES_DB:-app}" -c 'select 1;'
curl -i http://127.0.0.1:8000/healthz
docker compose logs --no-color --tail=20 api
docker compose down -v
```

## Output

```text
TODO: paste the output of the command above.
```

## What the output must show

- `docker compose ps` lists `api`, `postgres` and `minio` as `Up`.
- `docker compose logs api` shows the `migrate` run followed by
  `python -m config.bucket` (the bucket named by `S3_BUCKET` is created) and
  then the `runserver` start; migrations only succeed when the Postgres
  connection is configured.
- `docker compose exec -T postgres psql -U app -d app -c 'select 1;'` returns
  one row, proving the stack runs on the Postgres service.
- `curl -i http://127.0.0.1:8000/healthz` answers `HTTP/1.1 200 OK` and
  `{"status": "ok"}`.

## Also verifiable without Docker

The Django suite behind `environment.yaml` is runnable directly (SQLite
fallback, no object storage):

```sh
sh src/forgel/templates/django-drf-react/scripts/test.sh
```

Status: **not yet run in Docker** - the sandbox of this task has no Docker
daemon, so a human must paste the compose output before the acceptance
criterion is closed.
