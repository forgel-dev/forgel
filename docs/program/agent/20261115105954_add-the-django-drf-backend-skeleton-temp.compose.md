# django-drf-react template: `docker compose up --build` evidence

The unittest suite never starts Docker (constraint), so the local stand is
verified by the coding agent: run the commands below, paste the actual output
into the `Output` section and mark the status confirmed. There is no human
evidence gate.

## Command

Run from the repository root:

```sh
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react --env-file src/forgel/templates/django-drf-react/.env.example up --build -d
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react ps
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T postgres psql -U app -d app -c 'select 1;'
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/healthz').read().decode())"
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react logs --no-color --tail=20 api
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react down -v
```

## Output

```text
TODO: paste the output of the command above.
```

## Expected output (what the run must show)

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

$ docker compose ... exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/healthz').read().decode())"
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
- `docker compose ... exec -T api python -c ...` fetches `/healthz` and prints
  `{"status": "ok"}`.

## Also verifiable without Docker

The Django suite behind `environment.yaml` is runnable directly (SQLite
fallback, no object storage):

```sh
sh src/forgel/templates/django-drf-react/scripts/test.sh
```

Status: **not yet run** - the coding agent runs the block above and records
the actual output; no human evidence gate.
