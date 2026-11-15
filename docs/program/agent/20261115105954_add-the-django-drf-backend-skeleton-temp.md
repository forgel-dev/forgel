# Agent Run: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Status: `done`
- Repository: `main`
- Finished: 2026-11-15T13:20:00+00:00

## Requirements

- Create the template directory src/forgel/templates/django-drf-react/ following the layout conventions of the existing hello-web template (FORGEL.md, AGENTS.md, .gitignore, .dockerignore, Dockerfile, environment.yaml).
- api/: a Django project with Django REST Framework, settings read from environment variables (DATABASE_URL or discrete POSTGRES_* variables, and S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY), and a DRF health endpoint GET /healthz returning JSON {"status": "ok"}.
- api/requirements.txt pins Django, djangorestframework, psycopg and django-storages plus boto3.
- api/ contains Django tests (api/tests/) that exercise /healthz through the Django test client and run without a database server or S3.
- compose.yaml declares three services: the api image, a postgres service, and an S3-compatible object storage service (minio) with a created bucket, all wired through environment variables.
- environment.yaml in the template declares test: ["python", "manage.py", "test"] run from api/ via an explicit working directory or a wrapper script, and leaves e2e for the next task.
- Add tests/test_template_django_drf_react.py asserting: the template directory contains the required files, the template environment.yaml parses and declares a non-empty test command, compose.yaml declares postgres and object storage services, and the health endpoint route is registered in the Django URL configuration.

## Acceptance Criteria

- The structural template test passes.
- All Python sources under the template compile with python -m compileall.
- A human confirms from the task report that `docker compose up --build` in the template serves GET /healthz with 200 and the Postgres connection configured; a ready-to-paste command and its output are included in docs/program/agent/<task>.md.

## Constraints

- No network calls, Docker runs or cloud resources inside the unittest suite.
- Do not hardcode credentials; only placeholder values from environment variables and an .env.example-style sample.
- Template text (README, FORGEL.md, AGENTS.md) in English.
- The template must not depend on the hello-web recipe or its modules.

## Assumptions

- environment.yaml has no working-directory field, so the run-from-api/ test command is the scripts/test.sh wrapper invoked from the contract
- The S3 bucket is created by the API container on startup (api/config/bucket.py in docker/entrypoint.sh) so compose.yaml stays at the three services the task names
- The container serves Django's built-in runserver since no WSGI/ASGI server was requested
- django.contrib.auth is installed because DRF resolves its default UNAUTHENTICATED_USER through that app; no auth endpoints are shipped
- The Django suite is not wired into the repository unittest gate (Django is not installed there); the structural test compiles every template .py file instead, and the suite runs via scripts/test.sh wherever Django is installed
- Docker cannot run in the sandbox, so this report documents the exact compose command and the expected output for a human to confirm

## Rework after the failed QA (exit 127)

The previous QA run failed the check

```sh
env PYTHONPATH=src python -m unittest tests.test_template_django_drf_react -v
```

with exit 127 and `env: python: No such file or directory`. QA runs checks from
a stripped environment (a handful of safe variables plus the contract `env`),
so `PATH` is whatever the daemon inherited and a bare `python` may be missing.
`command_argv` already pinned a leading `python`/`python3` to `sys.executable`
but did not look past a leading `env NAME=value`.

Fix: `forgel/environment.py::command_argv` now skips a leading `env` and its
`NAME=value` assignments and pins the program that follows when it is
`python`/`python3`. Any other program is untouched, and an `env` with no
program is rejected. Covered by `tests/test_environment_env_prefix.py` (unit)
and `tests/test_qa_env_command.py`, which runs the resolved argv with a `PATH`
containing only `env` and `python3`, reproducing the QA environment.

## Summary

Completed the django-drf-react template at src/forgel/templates/django-drf-react/:
FORGEL.md, AGENTS.md, README.md, .gitignore, .dockerignore, .env.example,
Dockerfile, compose.yaml, environment.yaml, scripts/test.sh, docker/entrypoint.sh,
plus api/ (manage.py, requirements.txt pinning Django/djangorestframework/psycopg/
django-storages/boto3, config/settings.py reading DATABASE_URL or POSTGRES_* and
S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY with SQLite + filesystem
fallbacks so tests need no server, config/urls.py routing health.urls,
health/views.py DRF APIView answering GET /healthz with {"status": "ok"},
config/bucket.py creating the bucket at container start, and
api/tests/test_health.py exercising /healthz via the Django test client).

compose.yaml declares exactly three services (api, postgres, minio) wired
through ${...} environment variables, with the bucket created by the API
entrypoint; environment.yaml declares test: ["./scripts/test.sh"] (the wrapper
cds into api/ and runs python manage.py test) and leaves e2e for the next task.
tests/test_template_django_drf_react.py (18 tests) asserts the required files,
the pins, the settings env reads, template independence from hello-web, the
parsed environment contract with a non-empty test command running from api/,
the compose services, bucket creation, and the registered /healthz route backed
by a DRF view tested through the Django client.

## Files Changed

- `docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.compose.md`
- `docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.md`
- `src/forgel/environment.py`
- `src/forgel/templates/django-drf-react/README.md`
- `src/forgel/templates/django-drf-react/api/config/settings.py`
- `src/forgel/templates/django-drf-react/compose.yaml`
- `tests/test_environment_env_prefix.py`
- `tests/test_qa_env_command.py`
- `tests/test_template_django_drf_react.py`

## Commands

- `python -m unittest discover -s tests` → exit 0 (443 tests, OK)
- `python -m unittest tests.test_template_django_drf_react -v` → exit 0 (18 tests, OK)
- `python -m unittest tests.test_environment tests.test_environment_env_prefix tests.test_qa_env_command -v` → exit 0
- `python -m compileall -q src/forgel/templates/django-drf-react` → exit 0

## Final Test Output

```text
$ python -m unittest discover -s tests
...........................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 443 tests in 59.586s

OK
```

## Compose stand: `docker compose up --build` (acceptance criterion 3)

The unittest suite never starts Docker (constraint), so the stand is verified by
hand. Run the command below from the repository root and paste the output into
the `Output` section; the same command lives in
`docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.compose.md`.

### Ready-to-paste command

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

### Output

```text
TODO: paste the output of the command above.
```

### Expected output (what the human must see)

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
`DATABASE_URL` (falling back to the discrete `POSTGRES_*` variables), so that
log is the proof that the API runs with the Postgres connection configured.
Status: **not yet run in Docker** — this sandbox has no Docker daemon, so the
`Output` block above stays a TODO until a human pastes it.

### Also verifiable without Docker

The Django suite behind `environment.yaml` runs directly (SQLite fallback, no
object storage):

```sh
sh src/forgel/templates/django-drf-react/scripts/test.sh
```
