# Agent Run: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Status: `done`
- Repository: `main`

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

## What was built

`src/forgel/templates/django-drf-react/`

- `FORGEL.md`, `AGENTS.md`, `README.md` (English), `.gitignore`, `.dockerignore`,
  `.env.example`, `Dockerfile`, `compose.yaml`, `environment.yaml`,
  `scripts/test.sh`, `docker/entrypoint.sh`.
- `api/manage.py`, `api/requirements.txt` (Django, djangorestframework, psycopg,
  django-storages, boto3 — all pinned).
- `api/config/settings.py` — reads `DATABASE_URL` or the discrete `POSTGRES_*`
  variables and `S3_ENDPOINT`/`S3_BUCKET`/`S3_ACCESS_KEY`/`S3_SECRET_KEY`
  (`S3_REGION` optional); without them it falls back to in-memory SQLite and
  file-system storage so tests need no server and no object storage.
- `api/config/urls.py` routes `health.urls`; `api/health/views.py` is a DRF
  `APIView` answering `GET /healthz` with `{"status": "ok"}`.
- `api/config/bucket.py` creates the S3 bucket on container startup.
- `api/tests/test_health.py` exercises `/healthz` through the Django test client.
- `compose.yaml` declares exactly three services — `api`, `postgres`, `minio` —
  wired through `${...}` environment variables; the API container creates the
  bucket named by `S3_BUCKET` (via `api/config/bucket.py` in the entrypoint).
- `environment.yaml`: `test: ["./scripts/test.sh"]`, a wrapper that enters
  `api/` and runs `python manage.py test`; `e2e` is left for the next task.

`tests/test_template_django_drf_react.py` (18 tests) asserts the required
files, the pins, the settings env reads, the template's independence from
hello-web, the parsed environment contract with a non-empty test command that
runs from `api/`, the compose services, the bucket creation, and the registered
`/healthz` route backing a DRF view tested through the Django client.

## Verification run here

```text
$ python -m unittest discover -s tests
Ran 438 tests in 56.024s
OK

$ python -m unittest tests.test_template_django_drf_react -v
Ran 18 tests in 0.019s
OK

$ python -m compileall -q src/forgel/templates/django-drf-react
exit code 0
```

## Ready-to-paste compose verification

Docker is not available inside the unittest sandbox, so the stand is verified by
hand. Run from the repository root:

```sh
cd src/forgel/templates/django-drf-react
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose exec -T postgres psql -U app -d app -c 'select 1;'
curl -i http://127.0.0.1:8000/healthz
docker compose logs --no-color --tail=20 api
docker compose down -v
```

Expected output (the parts a human must confirm):

```text
$ docker compose ps
NAME                      SERVICE   STATUS
...-api-1                 api       Up
django-drf-react-postgres-1  postgres  Up (healthy)
django-drf-react-minio-1     minio     Up (healthy)

$ docker compose exec -T postgres psql -U app -d app -c 'select 1;'
 ?column?
----------
        1
(1 row)

$ curl -i http://127.0.0.1:8000/healthz
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "ok"}

$ docker compose logs --no-color --tail=20 api
... Applying contenttypes.0001_initial... OK
... Applying auth.0001_initial... OK
... (bucket app-media created)
... Starting development server at http://0.0.0.0:8000/
```

The `migrate` lines are the proof that the Postgres connection is configured:
the container only starts the server after migrations succeed against
`postgres:5432`. The command and its output also live in
`docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.compose.md`.

## Assumptions

- The environment contract has no working-directory field, so the run-from-`api/`
  test command is provided by `scripts/test.sh` invoked from `environment.yaml`.
- The S3 bucket is created by the API container on startup
  (`api/config/bucket.py` in `docker/entrypoint.sh`), keeping `compose.yaml` at
  the three services the task names.
- The container serves Django's built-in `runserver`; no WSGI/ASGI server was
  requested.
- `django.contrib.auth` is installed because DRF resolves its default
  `UNAUTHENTICATED_USER` through that app; the skeleton ships no auth endpoints.
- The Django suite itself is not part of the repository unittest gate (Django is
  not installed in it); the structural test compiles every template `.py` file
  and the suite is runnable via `scripts/test.sh` wherever Django is installed.
