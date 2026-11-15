# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Sessions: 2
- Finished: 2026-11-15T17:22:00+00:00

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

- The e2e command stays `sh scripts/e2e.sh` because environment.yaml has no working directory of its own and the template already uses script wrappers for setup and test.
- The QA stand lives in a separate compose file docker/docker-compose.qa.yml with a `qa` profile service rather than a second profile in compose.yaml, keeping the development compose.yaml free of browser tooling.
- The agent runner has no bare `sh` executable action, so the declared command `sh scripts/e2e.sh` was executed unchanged through `python -c "import subprocess,sys; p=subprocess.run(['sh','scripts/e2e.sh'], cwd='src/forgel/templates/django-drf-react'); print('EXIT', p.returncode); sys.exit(p.returncode)"`. The wrapper itself ran; its own stdout/stderr and its exit status are recorded verbatim below.
- Images came from the local Docker cache and the `qa` network is `internal: true`, so the stand neither publishes host ports nor contacts Yandex Cloud.
- The two previously flagged compose tests are kept side by side: one asserts the exact service set {api, web, postgres, minio}, the other asserts the backend slice as a subset.

## Test Removals

- none

## Summary

The product slice is in place: web/ holds a React SPA (index.html + esbuild-bundled entry in web/src/) served by nginx which proxies /healthz to api:8000; compose.yaml declares the web service; docker/docker-compose.qa.yml is an isolated stand (api, postgres, minio, web plus the on-demand `qa` profile service) on a single internal network with no published ports and no cloud references; qa/scenario.js is a playwright-core headless scenario asserting the /healthz 200 response and the rendered health text, exiting non-zero on failure; environment.yaml declares `e2e: ["sh scripts/e2e.sh"]`, which builds and runs the profile under `set -e`; tests/test_template_django_drf_react.py covers all of it and parses the command through src/forgel/environment.py.

This session fixed the one remaining blocking defect: the report now contains the output of the declared e2e command itself. `sh scripts/e2e.sh` (the exact declared argument list, run from the template root) executed end to end and exited 0: the SPA index returned 200, /healthz returned 200 with `{"status":"ok"}`, the SPA rendered `Health: ok (HTTP 200)`, `SUMMARY: 5/5 checks passed`, `e2e: the isolated QA stand passed`. The verbatim transcript and exit status are in "E2E Stand Output" below, and "Final Test Output" now holds the real unittest transcript instead of pipeline stage logs.

Tests: `python -m unittest tests.test_template_django_drf_react -v` -> 30 tests OK; `python -m unittest discover -s tests` -> 478 tests OK (exit 0). The unittest suite performs no browser download, Docker run or network access. No tests were removed or weakened.

## E2E Stand Output

The template environment.yaml declares:

```
e2e: ["sh scripts/e2e.sh"]
```

The command was launched exactly as declared, with the template root as working directory:

```
python -c "import subprocess,sys; p=subprocess.run(['sh','scripts/e2e.sh'],cwd='src/forgel/templates/django-drf-react'); print('EXIT', p.returncode); sys.exit(p.returncode)"
```

Actual output of the e2e command (verbatim; docker compose buffers its own
progress lines and flushes them after the scenario's stdout):

```
#1 [internal] load local bake definitions
#1 reading from stdin 1.18kB done
#1 DONE 0.0s

#2 [web internal] load build definition from Dockerfile
#2 transferring dockerfile: 497B done
#2 DONE 0.0s

#3 [api internal] load build definition from Dockerfile
#3 transferring dockerfile: 411B done
#3 DONE 0.0s

#4 [api internal] load metadata for docker.io/library/python:3.12-slim
#4 DONE 0.0s

#5 [api internal] load .dockerignore
#5 transferring context: 91B done
#5 DONE 0.0s

#6 [api 1/7] FROM docker.io/library/python:3.12-slim
#6 DONE 0.0s

#7 [api internal] load build context
#7 transferring context: 806B done
#7 DONE 0.0s

#8 [api 5/7] COPY api/ /app/
#8 CACHED
#9 [api 2/7] WORKDIR /app
#9 CACHED
#10 [api 4/7] RUN pip install --no-cache-dir -r /app/requirements.txt
#10 CACHED
#11 [api 6/7] COPY docker/ /app/docker/
#11 CACHED
#12 [api 3/7] COPY api/requirements.txt /app/requirements.txt
#12 CACHED
#13 [api 7/7] RUN chmod +x /app/docker/entrypoint.sh
#13 CACHED

#14 [api] exporting to image
#14 exporting layers done
#14 writing image sha256:7915e5b69f44dc657436fb5b77cc34c62f9dc8cfcab8d4561994830fecec6a48 done
#14 naming to docker.io/library/django-drf-react-api done
#14 DONE 0.0s
#15 [api] resolving provenance for metadata file
#15 DONE 0.0s

#16 [web internal] load metadata for docker.io/library/node:22-alpine
#17 [web internal] load metadata for docker.io/library/nginx:1.27-alpine
#17 DONE 0.9s
#16 DONE 1.1s
#18 [web internal] load .dockerignore
#18 transferring context: 2B done
#18 DONE 0.0s
#19 [web build 1/7] FROM docker.io/library/node:22-alpine
#19 DONE 0.0s
#20 [web stage-1 1/3] FROM docker.io/library/nginx:1.27-alpine
#20 DONE 0.0s
#21 [web internal] load build context
#21 transferring context: 180B done
#21 DONE 0.0s
#22 [web build 3/7] COPY package.json /app/package.json
#22 CACHED
#23 [web stage-1 2/3] COPY nginx.conf /etc/nginx/conf.d/default.conf
#23 CACHED
#24 [web build 2/7] WORKDIR /app
#24 CACHED
#25 [web build 5/7] COPY index.html /app/index.html
#25 CACHED
#26 [web build 7/7] RUN npm run build
#26 CACHED
#27 [web build 4/7] RUN npm install --no-audit --no-fund
#27 CACHED
#28 [web build 6/7] COPY src /app/src
#28 CACHED
#29 [web stage-1 3/3] COPY --from=build /app/dist /usr/share/nginx/html
#29 CACHED

#30 [web] exporting to image
#30 exporting layers done
#30 writing image sha256:3ebb9cd870476a3d98ee369fb9c047c0f58e17f5974ee4371ede69c8805fab33 done
#30 naming to docker.io/library/django-drf-react-web done
#30 DONE 0.0s
#31 [web] resolving provenance for metadata file
#31 DONE 0.0s
PASS the SPA index returns 200 [200]
PASS the API request /healthz returns 200 [200]
PASS the API answers {"status": "ok"} [{"status":"ok"}]
PASS the SPA renders the health status text [Health: ok (HTTP 200)]
PASS the SPA renders the HTTP status code [Health: ok (HTTP 200)]
SUMMARY: 5/5 checks passed
e2e: the isolated QA stand passed
EXIT 0
```

The compose driver's own progress lines for the stand (all four services Healthy
on the internal `django-drf-react-qa_qa` network, then teardown) were:

```
 Image django-drf-react-web Building
 Image django-drf-react-api Building
 Image django-drf-react-api Built
 Image django-drf-react-web Built
 Network django-drf-react-qa_qa Creating
 Network django-drf-react-qa_qa Created
 Volume django-drf-react-qa_postgres-data Created
 Volume django-drf-react-qa_minio-data Created
 Container django-drf-react-qa-postgres-1 Started
 Container django-drf-react-qa-minio-1 Started
 Container django-drf-react-qa-minio-1 Healthy
 Container django-drf-react-qa-postgres-1 Healthy
 Container django-drf-react-qa-api-1 Started
 Container django-drf-react-qa-api-1 Healthy
 Container django-drf-react-qa-web-1 Started
 Container django-drf-react-qa-web-1 Healthy
 Container django-drf-react-qa-qa-run-956c43dbcbb4 Created
 Container django-drf-react-qa-web-1 Stopped
 Container django-drf-react-qa-api-1 Stopped
 Container django-drf-react-qa-minio-1 Stopped
 Container django-drf-react-qa-postgres-1 Stopped
 Volume django-drf-react-qa_postgres-data Removed
 Volume django-drf-react-qa_minio-data Removed
 Network django-drf-react-qa_qa Removed
```

Exit status of the declared command: `EXIT 0`.

## Final Test Output

`python -m unittest discover -s tests`:

```
Ran 478 tests in 60.508s

OK
```

## Commands

- `["docker", "compose", "version"]` -> exit 0
- `["python", "-c", "... subprocess.run(['sh','scripts/e2e.sh'], cwd='src/forgel/templates/django-drf-react') ..."]` -> exit 0 (the declared e2e command `sh scripts/e2e.sh`)
- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` -> exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` -> exit 0

## Actions

- read_file: src/forgel/templates/django-drf-react/scripts/e2e.sh
- read_file: src/forgel/templates/django-drf-react/environment.yaml
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- run: declared e2e command `sh scripts/e2e.sh` -> EXIT 0
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests'] -> OK (478 tests)
- write_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
