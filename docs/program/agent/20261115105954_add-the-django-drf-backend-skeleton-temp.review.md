# Task Review: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-15T13:36:30+00:00

## Summary

The template itself is in good shape: the hello-web-style layout, English FORGEL.md/AGENTS.md/README.md, a Django/DRF api with env-driven Postgres/S3 settings, pinned requirements, Django client tests for /healthz, a three-service compose.yaml (api, postgres, minio) with a bucket created on startup, an environment.yaml whose test command is a scripts/test.sh wrapper that cd's into api/ and runs `python manage.py test`, and tests/test_template_django_drf_react.py covering the required files/contract/compose/route. However the review-only acceptance criterion is not met: docs/program/agent/...compose.md still has `TODO: paste the output of the command above.` in its Output section and states 'not yet run in Docker', and the task report only supplies 'expected output ... a human must confirm', so the required ready-to-paste command together with its actual output and human confirmation is not present. The unrelated core edit to src/forgel/environment.py is covered by attributed tests and not itself blocking, but the missing compose evidence blocks acceptance.

## Requirements

- Template directory follows hello-web layout (FORGEL.md, AGENTS.md, .gitignore, .dockerignore, Dockerfile, environment.yaml): pass — All listed files are present in src/forgel/templates/django-drf-react/.
- api/ is a Django + DRF project with env-driven Postgres (DATABASE_URL or POSTGRES_*) and S3 (S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY) settings and a DRF GET /healthz returning {"status": "ok"}: pass — api/config/settings.py reads the env variables with SQLite/local-storage fallbacks; api/config/urls.py routes the health app; api/health/views.py is a DRF APIView returning the expected JSON.
- api/requirements.txt pins Django, djangorestframework, psycopg, django-storages and boto3: pass — All five are pinned per the report and the structural test asserts the pins.
- api/ contains Django tests (api/tests/) exercising /healthz via the Django test client without a DB server or S3: pass — api/tests/test_health.py uses the Django test client with the SQLite fallback; removal of api/health/tests/__init__.py is justified by this replacement file being present.
- compose.yaml declares three services (api image, postgres, S3-compatible minio with a created bucket) wired through environment variables: pass — The three services are declared with ${...} variables; the bucket is created by api/config/bucket.py from the entrypoint.
- environment.yaml declares the test command (python manage.py test from api/) via an explicit working directory or wrapper script and leaves e2e for the next task: pass — test: ["./scripts/test.sh"] where scripts/test.sh enters api/ and runs python manage.py test; e2e is absent.
- tests/test_template_django_drf_react.py asserts the required files, parsed environment.yaml with a non-empty test command, compose postgres and object storage services, and the /healthz route in the URL configuration: pass — The test file exists with these assertions (18 tests).
- No hardcoded credentials; only placeholder values from environment variables and an .env.example-style sample: pass — compose.yaml uses ${...} variables and .env.example supplies placeholders.
- All Python sources under the template compile with python -m compileall: pass — Acceptance check passed with exit 0.
- A human confirms from the task report that `docker compose up --build` serves GET /healthz with 200 against Postgres; a ready-to-paste command and its output are included in docs/program/agent/<task>.md: fail — review-only criterion: docs/program/agent/20261115105954_...compose.md still contains 'TODO: paste the output of the command above.' and 'Status: not yet run in Docker'; the report shows only expected output flagged as needing human confirmation.

## Blocking

- Review-only acceptance criterion unmet: the task report's compose evidence section has no actual `docker compose up --build` output or human confirmation (Output still says 'TODO: paste the output' and status 'not yet run in Docker'); only expected output is provided.

## Test Removals

- none

- src/forgel/templates/django-drf-react/api/health/tests/__init__.py: removed -> src/forgel/templates/django-drf-react/api/tests/test_health.py
