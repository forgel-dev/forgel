# Task Review: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-15T17:12:37+00:00

## Summary

The product slice is in place: web/ ships a React SPA (index.html, src/main.jsx, src/App.jsx fetching /healthz and rendering [data-testid="health-status"]), bundled with esbuild and served by nginx (web/Dockerfile, web/nginx.conf), compose.yaml gains the web service, docker/docker-compose.qa.yml runs api/postgres/minio/web plus the on-demand qa service on a single internal network with no published ports and no cloud references, qa/scenario.js is a playwright-core headless scenario asserting the rendered health text and /healthz 200 with a non-zero exit on failure, environment.yaml declares e2e: ["sh scripts/e2e.sh"], and the structural test suite covers the web service, QA compose file, scenario file and e2e command while parsing the command through src/forgel/environment.py (acceptance checks report exit 0, and no test removals were detected). However, the review-only acceptance criterion fails: the final task report does not contain the actual output of the e2e command in the isolated compose stand. Its Assumptions section explicitly states that the Docker stand was not executed in this session, that its behaviour is only pinned by structural assertions, and that the pipeline environment e2e verdict is recorded 'rather than a stand log fabricated here' — retracting the stand log that an earlier revision of the same report contained. Since the earlier log was withdrawn and no executed output replaces it, an independent review cannot confirm the stand ran with exit 0, which is exactly what the acceptance criterion requires.

## Requirements

- web/: React SPA source (index.html plus a bundled entry) that fetches /healthz from the api service and renders the result: pass — web/index.html, web/src/main.jsx and web/src/App.jsx fetch /healthz and render Health: ok (HTTP 200) in [data-testid="health-status"], with test ids asserted both in the scenario and the tests.
- web Dockerfile or nginx-style static serving configuration used by compose.yaml: pass — web/Dockerfile builds the esbuild bundle and serves it from nginx (web/nginx.conf proxying /healthz to api:8000); compose.yaml builds the web service from context: web.
- compose.yaml gains a web service and a qa profile or docker/docker-compose.qa.yml that starts api, postgres, object storage and web on an isolated network without publishing cloud resources: pass — compose.yaml declares web next to api/postgres/minio; docker/docker-compose.qa.yml runs the same four services plus the qa profile on an internal: true network, with no ports published and no Yandex Cloud references.
- qa/ contains a headless-browser scenario runner with a scenario that loads the SPA, asserts the health status text and that the API request returns 200: pass — qa/scenario.js launches chromium via playwright-core, waits for the /healthz response, asserts status 200 and {"status":"ok"}, asserts the rendered health text and HTTP code, and process.exit(1) on failure.
- The template environment.yaml declares a non-empty e2e command that builds and runs the qa profile and exits non-zero on scenario failure: pass — e2e: ["sh scripts/e2e.sh"]; scripts/e2e.sh builds the QA stack, brings it up with --wait, runs --profile qa run --rm qa under set -e and tears it down in an EXIT trap.
- tests/test_template_django_drf_react.py is extended to assert the web service, the qa profile file, at least one qa scenario file and the non-empty e2e command: pass — Per the acceptance checks and the report, ComposeServicesTest/WebAppTest/QaStandTest/TemplateEnvironmentTest cover the web service, docker/docker-compose.qa.yml, qa/scenario.js and the e2e command; the structural check passed with exit 0.
- The extended structural template test passes, including the e2e assertions: pass — Acceptance check 'Structural test covers web, qa profile, scenario file and e2e command' reports pass (exit 0).
- The template e2e command is a well-formed argument list accepted by Forgel's environment parser, verified through src/forgel/environment.py: pass — The environment test and the parser-level e2e check pass; the test uses command_argv/parse_environment on the declared command.
- The task report contains the actual output of the e2e command in the isolated compose stand, showing exit 0; an independent review confirms the output: fail — The final report states the compose stand was not executed and records the pipeline environment e2e verdict 'rather than a stand log fabricated here'; the stand output present in the previous revision was retracted, so no executed output can be confirmed.
- No browser download, Docker run or network access in the unittest suite: pass — The tests only read template files and parse environment.yaml; the QA image installs chromium from Alpine packages rather than downloading a browser.
- The e2e stand must not publish ports beyond the local machine or contact Yandex Cloud: pass — docker/docker-compose.qa.yml declares no ports at all and puts every service on an internal: true network; no Yandex Cloud endpoint or credential appears.
- Public text in English: pass — All added SPA, QA, compose and report text is in English.
- No deleted or weakened tests: pass — No test removals were detected, and the report states the two previously flagged compose assertions were restored as exact-service and subset assertions.

## Blocking

- The task report does not contain actual output of the e2e command from the isolated compose stand showing exit 0: the final revision explicitly says the stand was not executed and discards the earlier stand log as something that would be 'fabricated here', so the review-only acceptance criterion 'task report contains the actual e2e output, exit 0, independently confirmed' is unmet. The report's 'Final Test Output' block likewise contains only pipeline stage logging rather than the claimed unittest run.

## Test Removals

- none


