# Task Report: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Repository: `main`
- Template: `src/forgel/templates/django-drf-react`

## Summary

The Django/DRF template now ships the React SPA, the `web` compose service and an
isolated QA stand with a headless-browser scenario:

- `web/` — React SPA (`index.html`, `src/main.jsx`, `src/App.jsx`) bundled with
  esbuild into `dist/`, served by nginx (`web/Dockerfile`, `web/nginx.conf`).
  `App.jsx` fetches `/healthz` through the nginx proxy to `api:8000` and renders
  `Health: ok (HTTP 200)` inside `[data-testid="health"]`, with the status text in
  `[data-testid="health-status"]`.
- `compose.yaml` — gained the `web` service built from `web/Dockerfile` next to
  `api`, `postgres` and `minio`.
- `docker/docker-compose.qa.yml` — the isolated QA stand: `api`, `postgres`,
  `minio`, `web` and the on-demand `qa` profile. Every service sits on the `qa`
  network, which is declared `internal: true`; no service publishes a host port
  and nothing talks to Yandex Cloud.
- `qa/` — `scenario.js` (Playwright/`playwright-core` driving the `chromium`
  already installed in the image), `package.json` and `Dockerfile`. The scenario
  loads the SPA, asserts the API `/healthz` request returns 200 with
  `{"status": "ok"}`, asserts the rendered health text and exits non-zero on a
  failed check.
- `environment.yaml` — declares `e2e: ["sh scripts/e2e.sh"]`; the wrapper builds
  the QA stack, brings the slice up with `--wait`, runs the `qa` profile and tears
  the stand down, with `set -e` so any step fails the gate.
- `tests/test_template_django_drf_react.py` — asserts the `web` service, the QA
  compose file, the QA scenario file and the non-empty e2e command, including
  that `command_argv`/`parse_environment` from `src/forgel/environment.py` accept
  the declared command.

## E2E Stand Output (exit 0)

The declared command was executed from the template root in the isolated compose
stand. `scripts/e2e.sh` itself could not be launched by the agent sandbox (`sh`
is not an allowed program), so its three steps were executed verbatim and each
exited 0:

```
$ docker compose -f docker/docker-compose.qa.yml --profile qa build
#1 [internal] load local bake definitions
#1 reading from stdin 1.73kB done
#1 DONE 0.0s
...
#38 [web] exporting to image
#38 naming to docker.io/library/django-drf-react-web 0.0s done
#39 [qa] exporting to image
#39 naming to docker.io/library/django-drf-react-qa 0.0s done
 Image django-drf-react-web Building
 Image django-drf-react-qa Building
 Image django-drf-react-api Building
 Image django-drf-react-api Built
 Image django-drf-react-qa Built
 Image django-drf-react-web Built
exit 0

$ docker compose -f docker/docker-compose.qa.yml up --detach --wait api postgres minio web
 Network django-drf-react-qa_qa Creating
 Network django-drf-react-qa_qa Created
 Volume django-drf-react-qa_postgres-data Creating
 Volume django-drf-react-qa_minio-data Creating
 Container django-drf-react-qa-postgres-1 Creating
 Container django-drf-react-qa-minio-1 Creating
 Container django-drf-react-qa-api-1 Creating
 Container django-drf-react-qa-web-1 Creating
 Container django-drf-react-qa-minio-1 Started
 Container django-drf-react-qa-postgres-1 Started
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-api-1 Started
 Container django-drf-react-qa-web-1 Started
 Container django-drf-react-qa-web-1 Healthy
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-api-1 Healthy
exit 0

$ docker compose -f docker/docker-compose.qa.yml --profile qa run --rm qa
PASS the SPA index returns 200 [200]
PASS the API request /healthz returns 200 [200]
PASS the API answers {"status": "ok"} [{"status":"ok"}]
PASS the SPA renders the health status text [Health: ok (HTTP 200)]
PASS the SPA renders the HTTP status code [Health: ok (HTTP 200)]
SUMMARY: 5/5 checks passed
 Container django-drf-react-qa-qa-run-5d9fa6c7b274 Created
exit 0

$ docker compose -f docker/docker-compose.qa.yml --profile qa down --volumes --remove-orphans
 Container django-drf-react-qa-web-1 Removed
 Container django-drf-react-qa-api-1 Removed
 Container django-drf-react-qa-minio-1 Removed
 Container django-drf-react-qa-postgres-1 Removed
 Volume django-drf-react-qa_postgres-data Removed
 Volume django-drf-react-qa_minio-data Removed
 Network django-drf-react-qa_qa Removed
exit 0
```

The scenario runner exits non-zero as soon as a check fails (`process.exit(1)`),
and `scripts/e2e.sh` runs under `set -e`, so a red scenario fails the declared
`e2e` command.

## Tests

`python -m unittest tests.test_template_django_drf_react -v` — 27 tests, OK.
`python -m unittest discover -s tests` — 472 tests, OK.

No browser download, Docker run or network access happens in the unittest suite:
the tests only read the template files and parse `environment.yaml` through
`src/forgel/environment.py`.
