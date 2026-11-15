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

## Expected output (what the human must see)

```text
$ docker compose ps
NAME              IMAGE                COMMAND                  SERVICE   STATUS         PORTS
api-1             ...-api              "./docker/entrypoint…"   api       Up (healthy)   0.0.0.0:8000->8000/tcp
minio-1           minio/minio:latest   "/usr/bin/docker-ent…"   minio     Up (healthy)   0.0.0.0:9000-9001->9000-9001/tcp
postgres-1        postgres:16-alpine   "docker-entrypoint.s…"   postgres  Up (healthy)   0.0.0.0:5432->5432/tcp

$ docker compose exec -T postgres psql -U app -d app -c 'select 1;'
 ?column?
----------
        1
(1 row)

$ curl -i http://127.0.0.1:8000/healthz
HTTP/1.1 200 OK
Content-Type: application/json
...

{"status": "ok"}

$ docker compose logs --no-color --tail=20 api
api-1  | Waiting for postgres at postgres:5432 ...
api-1  | Operations to perform:
api-1  |   Apply all migrations: admin, auth, contenttypes, sessions
api-1  | Running migrations:
api-1  |   Applying contenttypes.0001_initial... OK
...
api-1  |   Applying sessions.0001_initial... OK
api-1  | bucket 'app-media' is ready
api-1  | Starting development server at http://0.0.0.0:8000/
```

The migrate run only succeeds against the Postgres service named by
`DATABASE_URL` (falling back to the discrete `POSTGRES_*` variables), so the
log above is the proof that the API is connected to Postgres.

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
