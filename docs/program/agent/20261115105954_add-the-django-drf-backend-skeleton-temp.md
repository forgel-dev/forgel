# Agent Run: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Status: `done`
- Repository: `main`
- Finished: 2026-11-15T15:40:00+00:00

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
- The task report contains the actual output of `docker compose up --build` in the template, showing GET /healthz with 200 and the Postgres connection; an independent review confirms the output.

## Constraints

- No network calls, Docker runs or cloud resources inside the unittest suite.
- Do not hardcode credentials; only placeholder values from environment variables and an .env.example-style sample.
- Template text (README, FORGEL.md, AGENTS.md) in English.
- The template must not depend on the hello-web recipe or its modules.

## Assumptions

- The S3-compatible service stays the MinIO server, but its image comes from MINIO_IMAGE (default bitnamilegacy/minio:latest) because minio/minio is no longer pullable from Docker Hub and quay.io/minio/minio answers unauthorized; the same S3 API, mc and curl are available, and the image can be pinned or mirrored through MINIO_IMAGE.
- The API container no longer polls the database itself: compose already waits for postgres/minio health, so the entrypoint applies migrations, creates the bucket and execs runserver.
- Bucket creation logs its result ('bucket ... is ready') so the startup proof is visible in `docker compose logs api`.
- Long pip download lines in the evidence block are elided with `...`; every other line is the verbatim output of the run.
- The Docker run was executed on the coding host and recorded as the review evidence; the unittest suite itself never starts Docker, calls the network or touches cloud resources.

## Test Removals

- none

## Summary

Added the Django/DRF backend skeleton template at src/forgel/templates/django-drf-react/ and captured the real `docker compose up --build` evidence.

Template (hello-web-style layout, English text, no hello-web dependency): FORGEL.md, AGENTS.md, README.md, .gitignore, .dockerignore, .env.example (placeholders only), Dockerfile, docker/entrypoint.sh, compose.yaml, environment.yaml, scripts/test.sh, and api/ with manage.py, pinned requirements.txt (Django==5.2.7, djangorestframework==3.16.1, psycopg[binary]==3.2.10, django-storages==1.14.6, boto3==1.40.50), config/ (settings read DATABASE_URL or POSTGRES_*, S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY/S3_REGION, SQLite + local storage fallbacks, S3Storage wiring), config/bucket.py (creates the S3_BUCKET on startup), health/ (DRF APIView returning {"status": "ok"}) routed as GET /healthz, and api/tests/test_health.py exercising /healthz through the Django test client with no DB server and no S3. environment.yaml runs test: ["sh", "scripts/test.sh"] -> cd api && python manage.py test, e2e left empty for the next task. compose.yaml declares exactly api + postgres + minio, all wired through environment variables.

Docker evidence (review blocker): the Compose Evidence section below is the ready-to-paste command block and the actual output captured on the coding host (Docker Compose v5.3.1). The same evidence, with the full build log, is kept in `docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.compose.md`.

Tests: tests/test_template_django_drf_react.py covers required files, pinned requirements, compilation of every template .py, env-driven settings, hello-web independence, environment.yaml parsing (non-empty test command, empty e2e, artifacts exist), compose services (api/postgres/minio, env wiring, bucket bootstrap, MinIO default image, no committed credentials) and the /healthz route/view/client test plus the SQLite fallback. Full suite: `python -m unittest discover -s tests` -> Ran 459 tests, OK. `python -m compileall -q src/forgel/templates/django-drf-react` -> exit 0.

## Compose Evidence - `docker compose up --build`

### Command

Run from the repository root:

```sh
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react --env-file src/forgel/templates/django-drf-react/.env.example up --build -d
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react ps
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react logs --no-color api
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T api python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz'); print(r.status, r.read().decode())"
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T postgres psql -U app -d app -c 'select 1;'
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react logs --no-color --tail=6 api
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react down -v
```

### Output

Build log lines are verbatim; `...` marks an elided run of pip download lines.

```text
$ docker compose ... up --build -d
#1 [internal] load local bake definitions
#1 reading from stdin 628B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 411B 0.0s done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.12-slim
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 91B done
#4 DONE 0.0s

#5 [1/7] FROM docker.io/library/python:3.12-slim
#5 DONE 0.0s

#6 [2/7] WORKDIR /app
#6 CACHED

#7 [internal] load build context
#7 transferring context: 9.23kB done
#7 DONE 0.0s

#8 [3/7] COPY api/requirements.txt /app/requirements.txt
#8 DONE 0.0s

#9 [4/7] RUN pip install --no-cache-dir -r /app/requirements.txt
#9 2.735 Collecting Django==5.2.7 (from -r /app/requirements.txt (line 1))
#9 2.997   Downloading django-5.2.7-py3-none-any.whl.metadata (4.1 kB)
#9 3.198 Collecting djangorestframework==3.16.1 (from -r /app/requirements.txt (line 2))
#9 3.269   Downloading djangorestframework-3.16.1-py3-none-any.whl.metadata (11 kB)
#9 3.351 Collecting psycopg==3.2.10 (from psycopg[binary]==3.2.10->-r /app/requirements.txt (line 3))
#9 3.417   Downloading psycopg-3.2.10-py3-none-any.whl.metadata (4.6 kB)
#9 3.509 Collecting django-storages==1.14.6 (from -r /app/requirements.txt (line 4))
#9 3.574   Downloading django_storages-1.14.6-py3-none-any.whl.metadata (4.7 kB)
#9 4.267 Collecting boto3==1.40.50 (from -r /app/requirements.txt (line 5))
#9 4.348   Downloading boto3-1.40.50-py3-none-any.whl.metadata (6.7 kB)
...
#9 21.18 Successfully installed Django-5.2.7 asgiref-3.13.0 boto3-1.40.50 botocore-1.40.76 django-storages-1.14.6 djangorestframework-3.16.1 jmespath-1.1.0 psycopg-3.2.10 psycopg-binary-3.2.10 python-dateutil-2.9.0.post0 s3transfer-0.14.0 six-1.17.0 sqlparse-0.6.1 typing-extensions-4.16.0 urllib3-2.8.0
#9 DONE 21.9s

#10 [5/7] COPY api/ /app/
#10 DONE 0.0s

#11 [6/7] COPY docker/ /app/docker/
#11 DONE 0.0s

#12 [7/7] RUN chmod +x /app/docker/entrypoint.sh
#12 DONE 0.2s

#13 exporting to image
#13 exporting layers 1.6s done
#13 writing image sha256:c8679448285104b32937462b4bd6d90e663d6d59a064f525f6c3267cff219fc7 done
#13 naming to docker.io/library/django-drf-react-api done
#13 DONE 1.6s

#14 resolving provenance for metadata file
#14 DONE 0.0s
 Image django-drf-react-api Building
 Image django-drf-react-api Built
 Network django-drf-react_default Creating
 Network django-drf-react_default Created
 Volume django-drf-react_postgres-data Creating
 Volume django-drf-react_postgres-data Created
 Volume django-drf-react_minio-data Creating
 Volume django-drf-react_minio-data Created
 Container django-drf-react-postgres-1 Creating
 Container django-drf-react-minio-1 Creating
 Container django-drf-react-postgres-1 Created
 Container django-drf-react-minio-1 Created
 Container django-drf-react-api-1 Creating
 Container django-drf-react-api-1 Created
 Container django-drf-react-postgres-1 Starting
 Container django-drf-react-minio-1 Starting
 Container django-drf-react-minio-1 Started
 Container django-drf-react-postgres-1 Started
 Container django-drf-react-postgres-1 Waiting
 Container django-drf-react-minio-1 Waiting
 Container django-drf-react-minio-1 Healthy
 Container django-drf-react-postgres-1 Healthy
 Container django-drf-react-api-1 Starting
 Container django-drf-react-api-1 Started

$ docker compose ... ps
NAME                          IMAGE                        COMMAND                  SERVICE    CREATED          STATUS                    PORTS
django-drf-react-api-1        django-drf-react-api         "/app/docker/entrypo..."   api        10 seconds ago   Up 4 seconds              0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
django-drf-react-minio-1      bitnamilegacy/minio:latest   "/opt/bitnami/script..."   minio      10 seconds ago   Up 10 seconds (healthy)   0.0.0.0:9000-9001->9000-9001/tcp, [::]:9000-9001->9000-9001/tcp
django-drf-react-postgres-1   postgres:16-alpine           "docker-entrypoint.s..."   postgres   10 seconds ago   Up 10 seconds (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

$ docker compose ... logs --no-color api
api-1  | Operations to perform:
api-1  |   Apply all migrations: auth, contenttypes
api-1  | Running migrations:
api-1  |   Applying contenttypes.0001_initial... OK
api-1  |   Applying contenttypes.0002_remove_content_type_name... OK
api-1  |   Applying auth.0001_initial... OK
api-1  |   Applying auth.0002_alter_permission_name_max_length... OK
api-1  |   Applying auth.0003_alter_user_email_max_length... OK
api-1  |   Applying auth.0004_alter_user_username_opts... OK
api-1  |   Applying auth.0005_alter_user_last_login_null... OK
api-1  |   Applying auth.0006_require_contenttypes_0002... OK
api-1  |   Applying auth.0007_alter_validators_add_error_messages... OK
api-1  |   Applying auth.0008_alter_user_username_max_length... OK
api-1  |   Applying auth.0009_alter_user_last_name_max_length... OK
api-1  |   Applying auth.0010_alter_group_name_max_length... OK
api-1  |   Applying auth.0011_update_proxy_permissions... OK
api-1  |   Applying auth.0012_alter_user_first_name_max_length... OK
api-1  | bucket 'app-media' is ready

$ docker compose ... exec -T api python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz'); print(r.status, r.read().decode())"
200 {"status":"ok"}

$ docker compose ... exec -T postgres psql -U app -d app -c 'select 1;'
 ?column?
----------
        1
(1 row)

$ docker compose ... logs --no-color --tail=6 api
api-1  | Starting development server at http://0.0.0.0:8000/
api-1  | Quit the server with CONTROL-C.
api-1  |
api-1  | WARNING: This is a development server. Do not use it in a production setting. Use a production WSGI or ASGI server instead.
api-1  | [15/Nov/2026 09:26:52] "GET /healthz HTTP/1.1" 200 15

$ docker compose ... down -v
 Container django-drf-react-api-1 Stopped
 Container django-drf-react-api-1 Removed
 Container django-drf-react-minio-1 Removed
 Container django-drf-react-postgres-1 Removed
 Network django-drf-react_default Removed
 Volume django-drf-react_postgres-data Removed
 Volume django-drf-react_minio-data Removed
```

### What the output shows

- `docker compose ps` lists `api`, `postgres` and `minio`; Postgres and MinIO are
  `(healthy)` and the API publishes `0.0.0.0:8000->8000/tcp`.
- The API log shows `migrate` applying the `contenttypes` and `auth` migrations.
  Those tables only exist in the Postgres service named by `POSTGRES_HOST` /
  `POSTGRES_DB` / `POSTGRES_USER`, so a green migration is the Postgres
  connection in action.
- `bucket 'app-media' is ready` is `api/config/bucket.py` creating the bucket
  named by `S3_BUCKET` in MinIO on startup.
- The in-container request returns `200 {"status":"ok"}` and the API access log
  records `"GET /healthz HTTP/1.1" 200 15`.
- `psql -U app -d app -c 'select 1;'` inside the `postgres` service returns one
  row.

### Object-storage image note

`minio/minio:latest` is rejected by Docker Hub for this registry and
`quay.io/minio/minio:latest` answers `unauthorized`. The compose file therefore
takes the server image from `MINIO_IMAGE` (default
`bitnamilegacy/minio:latest`, which serves the same S3 API); the run above uses
that default. Pin or mirror it through `MINIO_IMAGE` in `.env` for another
registry.

Status: **confirmed** - captured on the coding host with Docker Compose v5.3.1;
the block above is that run's output.

## Files Changed

- `docs/program/agent/20261115105954_add-the-django-drf-backend-skeleton-temp.compose.md`
- `src/forgel/templates/django-drf-react/.dockerignore`
- `src/forgel/templates/django-drf-react/.env.example`
- `src/forgel/templates/django-drf-react/.gitignore`
- `src/forgel/templates/django-drf-react/AGENTS.md`
- `src/forgel/templates/django-drf-react/Dockerfile`
- `src/forgel/templates/django-drf-react/FORGEL.md`
- `src/forgel/templates/django-drf-react/README.md`
- `src/forgel/templates/django-drf-react/api/config/__init__.py`
- `src/forgel/templates/django-drf-react/api/config/asgi.py`
- `src/forgel/templates/django-drf-react/api/config/bucket.py`
- `src/forgel/templates/django-drf-react/api/config/settings.py`
- `src/forgel/templates/django-drf-react/api/config/urls.py`
- `src/forgel/templates/django-drf-react/api/config/wsgi.py`
- `src/forgel/templates/django-drf-react/api/health/__init__.py`
- `src/forgel/templates/django-drf-react/api/health/apps.py`
- `src/forgel/templates/django-drf-react/api/health/urls.py`
- `src/forgel/templates/django-drf-react/api/health/views.py`
- `src/forgel/templates/django-drf-react/api/manage.py`
- `src/forgel/templates/django-drf-react/api/requirements.txt`
- `src/forgel/templates/django-drf-react/api/tests/__init__.py`
- `src/forgel/templates/django-drf-react/api/tests/test_health.py`
- `src/forgel/templates/django-drf-react/compose.yaml`
- `src/forgel/templates/django-drf-react/docker/entrypoint.sh`
- `src/forgel/templates/django-drf-react/environment.yaml`
- `src/forgel/templates/django-drf-react/scripts/test.sh`
- `tests/test_template_django_drf_react.py`

## Commands

- `["docker", "compose", "...", "up", "--build", "-d"]` -> exit 0 (see Compose Evidence)
- `["docker", "compose", "...", "ps"]` -> exit 0
- `["docker", "compose", "...", "logs", "--no-color", "api"]` -> exit 0
- `["docker", "compose", "...", "exec", "-T", "api", "python", "-c", "...urlopen('http://127.0.0.1:8000/healthz')..."]` -> exit 0, `200 {"status":"ok"}`
- `["docker", "compose", "...", "exec", "-T", "postgres", "psql", "-U", "app", "-d", "app", "-c", "select 1;"]` -> exit 0
- `["docker", "compose", "...", "down", "-v"]` -> exit 0
- `["python", "-m", "compileall", "-q", "src/forgel/templates/django-drf-react"]` -> exit 0
- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` -> exit 0 (Ran 19 tests, OK)
- `["python", "-m", "unittest", "discover", "-s", "tests"]` -> exit 0 (Ran 459 tests, OK)

## Final Test Output

```
test_declares_the_api_postgres_and_object_storage ... ok
test_no_credential_literals_are_committed ... ok
test_object_storage_is_configured_from_the_environment ... ok
test_postgres_is_configured_from_the_environment ... ok
test_the_api_is_wired_to_both_services ... ok
test_the_bucket_is_created_on_startup ... ok
test_the_default_object_storage_image_is_minio ... ok
test_django_tests_use_the_client_without_services ... ok
test_the_health_route_is_registered ... ok
test_the_health_view_is_a_drf_endpoint ... ok
test_the_contract_parses ... ok
test_the_declared_artifacts_exist ... ok
test_the_test_command_is_declared_and_runs_from_api ... ok
test_python_sources_compile ... ok
test_required_files_are_present ... ok
test_requirement_pins_are_declared ... ok
test_settings_read_database_and_storage_from_the_environment ... ok
test_the_template_directory_exists ... ok
test_the_template_does_not_depend_on_the_hello_web_recipe ... ok

----------------------------------------------------------------------
Ran 19 tests in 0.012s

OK

----------------------------------------------------------------------
Ran 459 tests in 58.105s

OK
```
