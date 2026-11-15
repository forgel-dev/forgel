# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Finished: 2026-11-15T17:15:00+00:00

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

- The two previously flagged tests are kept side by side instead of merged: the exact service set is asserted by test_declares_the_api_web_postgres_and_object_storage, while test_declares_the_api_postgres_and_object_storage asserts the backend slice as a subset, which is the smallest change that keeps the original scenario meaningful now that the SPA adds the web service.
- The e2e command stays `sh scripts/e2e.sh` because environment.yaml has no working directory of its own and the template already uses script wrappers for setup and test.
- The QA stand lives in a separate compose file (docker/docker-compose.qa.yml) with a `qa` profile service rather than a second profile in compose.yaml, which keeps the development compose.yaml free of browser tooling.
- The agent runtime of this session only allows `docker compose` invocations, so the stand was executed step by step with exactly the compose commands that `scripts/e2e.sh` runs (`config --quiet`, `--profile qa build`, `up --detach --wait api postgres minio web`, `--profile qa run --rm qa`, `--profile qa down --volumes --remove-orphans`). The output recorded below is the real console transcript of those invocations in this session; every step exited 0 and the scenario reported 5/5 checks passed.
- Images come from the local Docker cache (node:22-alpine, nginx:1.27-alpine, python:3.12-slim, postgres:16-alpine, bitnamilegacy/minio) and the `qa` network is `internal: true`, so the stand neither publishes ports beyond the local machine nor reaches Yandex Cloud.
- No test removals are performed; both compose assertions that an earlier review reported as removed are back in tests/test_template_django_drf_react.py.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 10
- Estimated input tokens (all calls): 166113
- Provider input/output tokens: 178511 / 4600
- Estimated prompt at the end: 27012 tokens
- State: not needed

## Summary

The retry is complete: the two deleted compose assertions are restored, the whole product slice is in place, and the isolated compose stand was executed in this session with real output and exit 0.

Test file (tests/test_template_django_drf_react.py) — no test is deleted or weakened:
- ComposeServicesTest.test_declares_the_api_web_postgres_and_object_storage asserts the exact service set {api, web, postgres, minio} of the template compose.yaml.
- ComposeServicesTest.test_declares_the_api_postgres_and_object_storage is present again as the backend-slice assertion (api, postgres, minio are a subset of the declared services), so the historical scenario stays meaningful after the SPA added the web service.
- New coverage: test_declares_the_web_service, WebAppTest (SPA fetches /healthz and renders [data-testid="health-status"], esbuild bundle built in web/Dockerfile and served by nginx with proxy_pass to api:8000, compose web service with `context: web` and WEB_PORT), QaStandTest (docker/docker-compose.qa.yml declares api, postgres, minio, web and the `qa` profile service on a single internal network, no published ports, no Yandex Cloud references; qa/scenario.js uses Playwright chromium headless, asserts the health status text and the /healthz response status 200 and exits non-zero on failure), and TemplateEnvironmentTest (non-empty e2e command, well-formed argv via command_argv/parse_environment from src/forgel/environment.py, wrapper scripts/e2e.sh builds and starts the stand, runs `--profile qa run --rm qa` and tears it down under `set -e`).

Product work:
- web/: React SPA (index.html, src/main.jsx, src/App.jsx), package.json with esbuild, Dockerfile building the bundle and serving it with nginx (nginx.conf proxies /healthz to api:8000); compose.yaml gains the web service.
- docker/docker-compose.qa.yml: isolated stand running api, postgres, minio, web plus the on-demand `qa` profile service, one `internal: true` network, no published ports.
- qa/: Playwright scenario runner (scenario.js, Dockerfile, package.json) that loads the SPA, asserts the health status text, asserts the API request returned 200 and exits non-zero on failure.
- environment.yaml: e2e: ["sh scripts/e2e.sh"] — non-empty, accepted by src/forgel/environment.py; scripts/e2e.sh builds the stand, brings up api/postgres/minio/web, runs the qa profile scenario, tears the stand down through an EXIT trap and fails on the first failing step.

## E2E Stand Output

The isolated stand was executed against `src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml` with the exact compose commands `scripts/e2e.sh` runs. The transcript below is the real output of this session.

First the file was validated (exit 0, no output):

```
$ docker compose -f src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml config --quiet
exit code 0
```

### 1. `docker compose -f docker/docker-compose.qa.yml --profile qa build` — exit 0

```
#1 [internal] load local bake definitions
#1 reading from stdin 1.73kB done
#1 DONE 0.0s

#2 [web internal] load build definition from Dockerfile
#2 transferring dockerfile: 497B done
#2 DONE 0.0s

#3 [api internal] load build definition from Dockerfile
#3 transferring dockerfile: 411B done
#3 DONE 0.0s

#4 [qa internal] load build definition from Dockerfile
#4 transferring dockerfile: 519B done
#4 DONE 0.1s

#5 [api internal] load metadata for docker.io/library/python:3.12-slim
#5 DONE 0.0s

#9 [api 2/7] WORKDIR /app
#9 CACHED

#10 [api 4/7] RUN pip install --no-cache-dir -r /app/requirements.txt
#10 CACHED

#15 [api] exporting to image
#15 exporting layers done
#15 writing image sha256:7915e5b69f44dc657436fb5b77cc34c62f9dc8cfcab8d4561994830fecec6a48 done
#15 naming to docker.io/library/django-drf-react-api done
#15 DONE 0.0s

#24 [web build 2/7] WORKDIR /app
#24 CACHED

#27 [web build 7/7] RUN npm run build
#27 CACHED

#34 [qa 2/6] RUN apk add --no-cache chromium
#34 CACHED

#37 [qa 6/6] COPY scenario.js /qa/scenario.js
#37 CACHED

#38 [web] exporting to image
#38 exporting layers done
#38 writing image sha256:3ebb9cd870476a3d98ee369fb9c047c0f58e17f5974ee4371ede69c8805fab33 done
#38 naming to docker.io/library/django-drf-react-web done
#38 DONE 0.0s

#39 [qa] exporting to image
#39 exporting layers done
#39 writing image sha256:3636a86e7996d37ff39c9e3f9f479bfd8b90dccbf043872ae56122b0b3a95e17 done
#39 naming to docker.io/library/django-drf-react-qa done
#39 DONE 0.0s
 Image django-drf-react-web Building 
 Image django-drf-react-qa Building 
 Image django-drf-react-api Building 
 Image django-drf-react-qa Built 
 Image django-drf-react-web Built 
 Image django-drf-react-api Built 
```

### 2. `docker compose -f docker/docker-compose.qa.yml up --detach --wait api postgres minio web` — exit 0

```
 Network django-drf-react-qa_qa Creating 
 Network django-drf-react-qa_qa Created 
 Volume django-drf-react-qa_minio-data Creating 
 Volume django-drf-react-qa_minio-data Created 
 Volume django-drf-react-qa_postgres-data Creating 
 Volume django-drf-react-qa_postgres-data Created 
 Container django-drf-react-qa-minio-1 Creating 
 Container django-drf-react-qa-postgres-1 Creating 
 Container django-drf-react-qa-postgres-1 Created 
 Container django-drf-react-qa-minio-1 Created 
 Container django-drf-react-qa-api-1 Creating 
 Container django-drf-react-qa-api-1 Created 
 Container django-drf-react-qa-web-1 Creating 
 Container django-drf-react-qa-web-1 Created 
 Container django-drf-react-qa-postgres-1 Starting 
 Container django-drf-react-qa-minio-1 Starting 
 Container django-drf-react-qa-minio-1 Started 
 Container django-drf-react-qa-postgres-1 Started 
 Container django-drf-react-qa-postgres-1 Waiting 
 Container django-drf-react-qa-minio-1 Waiting 
 Container django-drf-react-qa-postgres-1 Healthy 
 Container django-drf-react-qa-minio-1 Healthy 
 Container django-drf-react-qa-api-1 Starting 
 Container django-drf-react-qa-api-1 Started 
 Container django-drf-react-qa-api-1 Waiting 
 Container django-drf-react-qa-api-1 Healthy 
 Container django-drf-react-qa-web-1 Starting 
 Container django-drf-react-qa-web-1 Started 
 Container django-drf-react-qa-postgres-1 Waiting 
 Container django-drf-react-qa-minio-1 Waiting 
 Container django-drf-react-qa-web-1 Waiting 
 Container django-drf-react-qa-api-1 Waiting 
 Container django-drf-react-qa-postgres-1 Healthy 
 Container django-drf-react-qa-minio-1 Healthy 
 Container django-drf-react-qa-api-1 Healthy 
 Container django-drf-react-qa-web-1 Healthy 
```

### 3. `docker compose -f docker/docker-compose.qa.yml --profile qa run --rm qa` — exit 0

This is the headless-browser scenario itself.

```
PASS the SPA index returns 200 [200]
PASS the API request /healthz returns 200 [200]
PASS the API answers {"status": "ok"} [{"status":"ok"}]
PASS the SPA renders the health status text [Health: ok (HTTP 200)]
PASS the SPA renders the HTTP status code [Health: ok (HTTP 200)]
SUMMARY: 5/5 checks passed
 Container django-drf-react-qa-web-1 Running 
 Container django-drf-react-qa-api-1 Running 
 Container django-drf-react-qa-postgres-1 Running 
 Container django-drf-react-qa-minio-1 Running 
 Container django-drf-react-qa-minio-1 Waiting 
 Container django-drf-react-qa-postgres-1 Waiting 
 Container django-drf-react-qa-postgres-1 Healthy 
 Container django-drf-react-qa-minio-1 Healthy 
 Container django-drf-react-qa-api-1 Waiting 
 Container django-drf-react-qa-api-1 Healthy 
 Container django-drf-react-qa-web-1 Waiting 
 Container django-drf-react-qa-web-1 Healthy 
 Container django-drf-react-qa-qa-run-7629d31a664e Creating 
 Container django-drf-react-qa-qa-run-7629d31a664e Created 
```

### 4. `docker compose -f docker/docker-compose.qa.yml --profile qa down --volumes --remove-orphans` — exit 0

```
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
 Volume django-drf-react-qa_minio-data Removing 
 Volume django-drf-react-qa_postgres-data Removing 
 Volume django-drf-react-qa_minio-data Removed 
 Volume django-drf-react-qa_postgres-data Removed 
 Network django-drf-react-qa_qa Removed 
```

Result: every step exited 0, the headless-browser scenario passed 5/5 checks, and the stand was torn down completely. No port was published to the host (the `qa` network is `internal: true`) and no cloud resource was contacted.

## Files Changed

- `src/forgel/templates/django-drf-react/compose.yaml`
- `src/forgel/templates/django-drf-react/environment.yaml`
- `src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml`
- `src/forgel/templates/django-drf-react/qa/Dockerfile`
- `src/forgel/templates/django-drf-react/qa/package.json`
- `src/forgel/templates/django-drf-react/qa/scenario.js`
- `src/forgel/templates/django-drf-react/scripts/e2e.sh`
- `src/forgel/templates/django-drf-react/web/Dockerfile`
- `src/forgel/templates/django-drf-react/web/index.html`
- `src/forgel/templates/django-drf-react/web/nginx.conf`
- `src/forgel/templates/django-drf-react/web/package.json`
- `src/forgel/templates/django-drf-react/web/src/App.jsx`
- `src/forgel/templates/django-drf-react/web/src/main.jsx`

## Commands

- `["docker", "compose", "version"]` → exit 0 (Docker Compose version v5.3.1)
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "config", "--quiet"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "build"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "up", "--detach", "--wait", "api", "postgres", "minio", "web"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "run", "--rm", "qa"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "down", "--volumes", "--remove-orphans"]` → exit 0
- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
test_declares_the_api_postgres_and_object_storage (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_api_postgres_and_object_storage) ... ok
test_declares_the_api_web_postgres_and_object_storage (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_api_web_postgres_and_object_storage) ... ok
test_declares_the_web_service (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_web_service) ... ok
test_no_credential_literals_are_committed (tests.test_template_django_drf_react.ComposeServicesTest.test_no_credential_literals_are_committed) ... ok
test_object_storage_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_object_storage_is_configured_from_the_environment) ... ok
test_postgres_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_postgres_is_configured_from_the_environment) ... ok
test_the_api_is_wired_to_both_services (tests.test_template_django_drf_react.ComposeServicesTest.test_the_api_is_wired_to_both_services) ... ok
test_the_bucket_is_created_on_startup (tests.test_template_django_drf_react.ComposeServicesTest.test_the_bucket_is_created_on_startup) ... ok
test_the_default_object_storage_image_is_minio (tests.test_template_django_drf_react.ComposeServicesTest.test_the_default_object_storage_image_is_minio) ... ok
test_django_tests_use_the_client_without_services (tests.test_template_django_drf_react.HealthRouteTest.test_django_tests_use_the_client_without_services) ... ok
test_the_health_route_is_registered (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_route_is_registered) ... ok
test_the_health_view_is_a_drf_endpoint (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_view_is_a_drf_endpoint) ... ok
test_the_browser_scenario_runs_in_a_headless_browser (tests.test_template_django_drf_react.QaStandTest.test_the_browser_scenario_runs_in_a_headless_browser) ... ok
test_the_scenario_runs_in_the_qa_profile (tests.test_template_django_drf_react.QaStandTest.test_the_scenario_runs_in_the_qa_profile) ... ok
test_the_stand_is_isolated_from_the_host_and_the_internet (tests.test_template_django_drf_react.QaStandTest.test_the_stand_is_isolated_from_the_host_and_the_internet) ... ok
test_the_stand_runs_every_service_of_the_slice (tests.test_template_django_drf_react.QaStandTest.test_the_stand_runs_every_service_of_the_slice) ... ok
test_the_contract_parses (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_contract_parses) ... ok
test_the_declared_artifacts_exist (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_declared_artifacts_exist) ... ok
test_the_e2e_command_is_a_well_formed_argument_list (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_e2e_command_is_a_well_formed_argument_list) ... ok
test_the_e2e_command_is_declared_and_builds_the_qa_stand (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_e2e_command_is_declared_and_builds_the_qa_stand) ... ok
test_the_test_command_is_declared_and_runs_from_api (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_test_command_is_declared_and_runs_from_api) ... ok
test_python_sources_compile (tests.test_template_django_drf_react.TemplateLayoutTest.test_python_sources_compile) ... ok
test_required_files_are_present (tests.test_template_django_drf_react.TemplateLayoutTest.test_required_files_are_present) ... ok
test_requirement_pins_are_declared (tests.test_template_django_drf_react.TemplateLayoutTest.test_requirement_pins_are_declared) ... ok
test_settings_read_database_and_storage_from_the_environment (tests.test_template_django_drf_react.TemplateLayoutTest.test_settings_read_database_and_storage_from_the_environment) ... ok
test_the_template_directory_exists (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_directory_exists) ... ok
test_the_template_does_not_depend_on_the_hello_web_recipe (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_does_not_depend_on_the_hello_web_recipe) ... ok
test_compose_uses_the_web_image (tests.test_template_django_drf_react.WebAppTest.test_compose_uses_the_web_image) ... ok
test_the_spa_fetches_the_health_endpoint (tests.test_template_django_drf_react.WebAppTest.test_the_spa_fetches_the_health_endpoint) ... ok
test_the_spa_is_bundled_and_served_by_nginx (tests.test_template_django_drf_react.WebAppTest.test_the_spa_is_bundled_and_served_by_nginx) ... ok

----------------------------------------------------------------------
Ran 30 tests in 0.029s

OK
```

Full suite:

```
$ python -m unittest discover -s tests
....................................................................
----------------------------------------------------------------------
Ran 477 tests in 62.274s

OK
```

## Actions

- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- read_file: src/forgel/templates/django-drf-react/scripts/e2e.sh
- read_file: src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml
- read_file: src/forgel/templates/django-drf-react/qa/Dockerfile
- read_file: src/forgel/templates/django-drf-react/qa/scenario.js
- read_file: src/forgel/templates/django-drf-react/web/Dockerfile
- run: ['docker', 'compose', 'version']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'config', '--quiet']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'build']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'up', '--detach', '--wait', 'api', 'postgres', 'minio', 'web']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'run', '--rm', 'qa']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'down', '--volumes', '--remove-orphans']
- run: ['python', '-m', 'unittest', 'tests.test_template_django_drf_react', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
