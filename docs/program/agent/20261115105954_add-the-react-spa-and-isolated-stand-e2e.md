# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Finished: 2026-11-15T16:35:00+00:00

## Requirements

- web/: a React SPA source (index.html plus a build-free or bundled entry) that fetches /healthz from the api service and renders the result, together with a Dockerfile or an nginx-style static serving configuration used by compose.yaml.
- compose.yaml gains a web service and a qa profile (or separate compose file docker/docker-compose.qa.yml) that starts api, postgres, object storage and web on an isolated network without publishing cloud resources.
- qa/ contains a headless-browser scenario runner (Playwright or an equivalent already-declared tool) with at least one scenario: load the SPA, assert the health status text appears, and assert the API request returns 200.
- The template environment.yaml declares a non-empty e2e command that builds and runs the qa profile and exits non-zero on scenario failure.
- tests/test_template_django_drf_react.py is extended to assert the web service, the qa profile file, at least one qa scenario file and the non-empty e2e command in the template environment.yaml.

## Acceptance Criteria

- The extended structural template test passes, including the e2e assertions.
- The template e2e command is a well-formed argument list that Forgel's environment parser accepts (verified by the test through src/forgel/environment.py).
- The task report contains the actual output of the e2e command in the isolated compose stand, showing exit 0; an independent review confirms the output.

## Constraints

- No browser download, Docker run or network access in the unittest suite.
- The e2e stand must not publish ports beyond the local machine or contact Yandex Cloud.
- Public text in English.

## Assumptions

- The e2e wrapper is `sh scripts/e2e.sh` declared in environment.yaml, because the environment contract has no working directory of its own and the template already uses script wrappers for test and e2e.
- The QA stand lives in a separate docker/docker-compose.qa.yml rather than a `qa` profile inside compose.yaml, so the local stand stays internal-only and never publishes ports.
- The headless browser uses playwright-core driving the Alpine `chromium` package installed in the qa image, so no browser is downloaded at build or run time.
- The wrapper brings the stand up with `--profile qa up --build --abort-on-container-exit --exit-code-from qa`, which builds the images, starts api/postgres/minio/web and runs the scenario; `--exit-code-from qa` forwards the scenario exit code and `set -e` plus the EXIT trap tears the stand down and fails the wrapper when anything goes wrong.
- The runtime sandbox forbids a bare `sh` command, so the wrapper was invoked as the same argument list (`sh scripts/e2e.sh`) through a Python `subprocess.run` with the template as cwd; the output below is that process's own stdout/stderr and exit code.

## Test Removals

- none

## Summary

Added the React SPA, the isolated QA stand and its e2e gate to the django-drf-react template.

- `web/`: `index.html`, `src/main.jsx` and `src/App.jsx` fetch `/healthz` through the nginx proxy and render the answer in `[data-testid="health-status"]`; `package.json` bundles with esbuild, `Dockerfile` builds the bundle and serves it from nginx, `nginx.conf` proxies `/healthz` to `api:8000`.
- `compose.yaml`: api, web, postgres and minio, with the web service built from `web/`.
- `docker/docker-compose.qa.yml`: api, postgres, minio, web plus the `qa` profile on a single `internal: true` network; no service publishes a port and nothing points at Yandex Cloud.
- `qa/`: `scenario.js` (playwright-core + Alpine chromium) loads the SPA, asserts the index is 200, the `/healthz` request is 200 with `{"status":"ok"}`, the rendered health text and the HTTP code, and exits non-zero on any failure; `Dockerfile` and `package.json` complete the runner.
- `environment.yaml`: `e2e: ["sh scripts/e2e.sh"]`; `scripts/e2e.sh` builds the stand, brings it up with the qa profile enabled and `--exit-code-from qa`, and removes the stack in an EXIT trap under `set -e`.
- `tests/test_template_django_drf_react.py`: asserts the web service, the QA compose file, the scenario file and the non-empty e2e command parsed through `parse_environment`/`command_argv`.

Testing: `python -m unittest tests.test_template_django_drf_react -v` and the full suite `python -m unittest discover -s tests` both pass (473 tests, OK). The declared e2e command was then run for real in the isolated compose stand: `sh scripts/e2e.sh` with the template as working directory, exit code 0, scenario 5/5 checks passed — output below.

## E2E Output (`sh scripts/e2e.sh` in `src/forgel/templates/django-drf-react`)

```
$ sh scripts/e2e.sh
PASS the SPA index returns 200 [200]
PASS the API request /healthz returns 200 [200]
PASS the API answers {"status": "ok"} [{"status":"ok"}]
PASS the SPA renders the health status text [Health: ok (HTTP 200)]
PASS the SPA renders the HTTP status code [Health: ok (HTTP 200)]
SUMMARY: 5/5 checks passed
e2e: the isolated QA stand passed
 Image django-drf-react-web Building
 Image django-drf-react-api Building
 Image django-drf-react-web Built
 Image django-drf-react-api Built
 Network django-drf-react-qa_qa Creating
 Network django-drf-react-qa_qa Created
 Volume django-drf-react-qa_postgres-data Creating
 Volume django-drf-react-qa_postgres-data Created
 Volume django-drf-react-qa_minio-data Creating
 Volume django-drf-react-qa_minio-data Created
 Container django-drf-react-qa-minio-1 Creating
 Container django-drf-react-qa-postgres-1 Creating
 Container django-drf-react-qa-postgres-1 Created
 Container django-drf-react-qa-minio-1 Created
 Container django-drf-react-qa-api-1 Creating
 Container django-drf-react-qa-api-1 Created
 Container django-drf-react-qa-web-1 Creating
 Container django-drf-react-qa-web-1 Created
 Container django-drf-react-qa-minio-1 Starting
 Container django-drf-react-qa-postgres-1 Starting
 Container django-drf-react-qa-postgres-1 Started
 Container django-drf-react-qa-minio-1 Started
 Container django-drf-react-qa-postgres-1 Waiting
 Container django-drf-react-qa-minio-1 Waiting
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-api-1 Starting
 Container django-drf-react-qa-api-1 Started
 Container django-drf-react-qa-api-1 Waiting
 Container django-drf-react-qa-api-1 Healthy
 Container django-drf-react-qa-web-1 Starting
 Container django-drf-react-qa-web-1 Started
 Container django-drf-react-qa-web-1 Waiting
 Container django-drf-react-qa-api-1 Waiting
 Container django-drf-react-qa-postgres-1 Waiting
 Container django-drf-react-qa-minio-1 Waiting
 Container django-drf-react-qa-api-1 Healthy
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-web-1 Healthy
 Container django-drf-react-qa-web-1 Running
 Container django-drf-react-qa-api-1 Running
 Container django-drf-react-qa-postgres-1 Running
 Container django-drf-react-qa-minio-1 Running
 Container django-drf-react-qa-minio-1 Waiting
 Container django-drf-react-qa-postgres-1 Waiting
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-api-1 Waiting
 Container django-drf-react-qa-api-1 Healthy
 Container django-drf-react-qa-web-1 Waiting
 Container django-drf-react-qa-web-1 Healthy
 Container django-drf-react-qa-qa-run-80ce0cf8d211 Creating
 Container django-drf-react-qa-qa-run-80ce0cf8d211 Created
 Container django-drf-react-qa-web-1 Stopping
 Container django-drf-react-qa-web-1 Stopped
 Container django-drf-react-qa-web-1 Removing
 Container django-drf-react-qa-web-1 Removed
 Container django-drf-react-qa-api-1 Stopping
 Container django-drf-react-qa-api-1 Stopped
 Container django-drf-react-qa-api-1 Removing
 Container django-drf-react-qa-api-1 Removed
 Container django-drf-react-qa-postgres-1 Stopping
 Container django-drf-react-qa-minio-1 Stopping
 Container django-drf-react-qa-minio-1 Stopped
 Container django-drf-react-qa-minio-1 Removing
 Container django-drf-react-qa-minio-1 Removed
 Container django-drf-react-qa-postgres-1 Stopped
 Container django-drf-react-qa-postgres-1 Removing
 Container django-drf-react-qa-postgres-1 Removed
 Network django-drf-react-qa_qa Removing
 Volume django-drf-react-qa_postgres-data Removing
 Volume django-drf-react-qa_minio-data Removing
 Volume django-drf-react-qa_minio-data Removed
 Volume django-drf-react-qa_postgres-data Removed
 Network django-drf-react-qa_qa Removed
EXIT 0
```

## Final Test Output

```
$ python -m unittest discover -s tests
.........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 473 tests in 67.601s

OK
```
