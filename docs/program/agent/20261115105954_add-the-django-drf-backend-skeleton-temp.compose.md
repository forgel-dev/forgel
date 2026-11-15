# django-drf-react template: `docker compose up --build` evidence

The unittest suite never starts Docker, so the local stand is verified by the
command below. Run it from the repository root and paste the output here.

## Command

```sh
cd src/forgel/templates/django-drf-react
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec -T postgres psql -U app -d app -c 'select 1;'
curl -i http://127.0.0.1:8000/healthz
docker compose logs --no-color --tail=10 api
docker compose down -v
```

## Output

```text
TODO: paste the output of the command above.
```

## What the output must show

- `docker compose ps` lists `api`, `postgres` and `minio` as `Up`.
- `curl -i http://127.0.0.1:8000/healthz` answers `HTTP/1.1 200 OK` and
  `{"status": "ok"}`.
- `docker compose exec -T postgres psql -U app -d app -c 'select 1;'` returns
  one row, proving the stack runs on the Postgres service.
- `docker compose logs api` shows the migrations applied by
  `docker/entrypoint.sh` before the server starts, which only succeeds when
  the Postgres connection is configured.

Status: **not yet run** - the sandbox of this task has no Docker daemon, so a
human must paste the output before the acceptance criterion is closed.
