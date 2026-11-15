# Session State: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Session: 1
- Status: in progress

## Goal

Implement the task requirements in the repository, run the final test and
commit. Continue from this state; do not repeat finished work.

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

- none

## Files Changed

- docs/program/tasks/20261115105954_add-the-django-drf-backend-skeleton-temp.json
- src/forgel/templates/django-drf-react/
- src/forgel/templates/django-drf-react/Dockerfile
- src/forgel/templates/django-drf-react/api/config/__init__.py
- src/forgel/templates/django-drf-react/api/config/asgi.py
- src/forgel/templates/django-drf-react/api/config/settings.py
- src/forgel/templates/django-drf-react/api/config/urls.py
- src/forgel/templates/django-drf-react/api/health/__init__.py
- src/forgel/templates/django-drf-react/api/health/apps.py
- src/forgel/templates/django-drf-react/api/health/tests/__init__.py
- src/forgel/templates/django-drf-react/api/health/urls.py
- src/forgel/templates/django-drf-react/api/health/views.py
- src/forgel/templates/django-drf-react/api/tests/__init__.py
- src/forgel/templates/django-drf-react/api/tests/test_health.py
- src/forgel/templates/django-drf-react/compose.yaml
- src/forgel/templates/django-drf-react/docker/entrypoint.sh
- src/forgel/templates/django-drf-react/environment.yaml

## Actions

- write_file: src/forgel/templates/django-drf-react/Dockerfile
- write_file: src/forgel/templates/django-drf-react/api/config/__init__.py
- write_file: src/forgel/templates/django-drf-react/api/config/settings.py
- write_file: src/forgel/templates/django-drf-react/api/config/urls.py
- write_file: src/forgel/templates/django-drf-react/api/config/asgi.py
- write_file: src/forgel/templates/django-drf-react/api/health/__init__.py
- write_file: src/forgel/templates/django-drf-react/api/health/views.py
- write_file: src/forgel/templates/django-drf-react/api/health/views.py
- write_file: src/forgel/templates/django-drf-react/api/health/urls.py
- write_file: src/forgel/templates/django-drf-react/api/health/apps.py
- write_file: src/forgel/templates/django-drf-react/api/health/tests/__init__.py
- run: ['docker', 'compose', 'version']
- write_file: src/forgel/templates/django-drf-react/api/config/settings.py
- write_file: src/forgel/templates/django-drf-react/api/tests/__init__.py
- write_file: src/forgel/templates/django-drf-react/api/tests/test_health.py
- write_file: src/forgel/templates/django-drf-react/environment.yaml
- write_file: src/forgel/templates/django-drf-react/docker/entrypoint.sh
- write_file: src/forgel/templates/django-drf-react/compose.yaml

## Commands

- none

## Recent Observations

- wrote 84 bytes to src/forgel/templates/django-drf-react/environment.yaml
- wrote 404 bytes to src/forgel/templates/django-drf-react/docker/entrypoint.sh
- wrote 2568 bytes to src/forgel/templates/django-drf-react/compose.yaml

## Next Step

Continue the task from the requirements and the current repository state.
