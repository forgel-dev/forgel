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
- src/forgel/templates/django-drf-react/.dockerignore
- src/forgel/templates/django-drf-react/.gitignore
- src/forgel/templates/django-drf-react/AGENTS.md
- src/forgel/templates/django-drf-react/FORGEL.md
- src/forgel/templates/django-drf-react/README.md
- src/forgel/templates/django-drf-react/api/manage.py
- src/forgel/templates/django-drf-react/api/requirements.txt

## Actions

- list_files
- read_file: src/forgel/templates/hello-web/environment.yaml
- read_file: src/forgel/templates/hello-web/Dockerfile
- read_file: src/forgel/templates/hello-web/FORGEL.md
- read_file: src/forgel/templates/hello-web/AGENTS.md
- read_file: src/forgel/templates/hello-web/.gitignore
- read_file: src/forgel/templates/hello-web/.dockerignore
- read_file: docs/program/tasks/20261115105954_add-the-django-drf-backend-skeleton-temp.json
- read_file: src/forgel/templates/hello-web/docker/docker-compose.qa.yml
- read_file: src/forgel/environment.py
- run: ['python', '-c', "import os;print('\n'.join(sorted(os.listdir('tests'))))"]
- list_files
- read_file: registry/recipes.json
- read_file: tests/test_registry.py
- read_file: tests/test_templates.py
- read_file: docs/program/plans/20261115105954_m1-oss-django-drf-react-spa-postgres-s3-.md
- read_file: tests/test_environment.py
- read_file: docs/program/agent/20261115004702_readme.md
- read_file: src/forgel/templates/hello-web/api/app.py
- read_file: src/forgel/projects.py
- run: ['docker', 'compose', 'version']
- run: ['python', '-c', "import importlib.util as u;print(u.find_spec('django') is not None, u.find_spec('rest_framework') is not None)"]
- write_file: src/forgel/templates/django-drf-react/FORGEL.md
- write_file: src/forgel/templates/django-drf-react/AGENTS.md
- write_file: src/forgel/templates/django-drf-react/README.md
- write_file: src/forgel/templates/django-drf-react/.gitignore
- write_file: src/forgel/templates/django-drf-react/.dockerignore
- write_file: src/forgel/templates/django-drf-react/api/requirements.txt
- write_file: src/forgel/templates/django-drf-react/api/manage.py

## Commands

- `['python', '-c', "import os;print('\n'.join(sorted(os.listdir('tests'))))"]` -> exit 1
- `['python', '-c', "import importlib.util as u;print(u.find_spec('django') is not None, u.find_spec('rest_framework') is not None)"]` -> exit 0

## Recent Observations

- wrote 51 bytes to src/forgel/templates/django-drf-react/.dockerignore
- wrote 105 bytes to src/forgel/templates/django-drf-react/api/requirements.txt
- wrote 586 bytes to src/forgel/templates/django-drf-react/api/manage.py

## Next Step

Continue the task from the requirements and the current repository state.
