# Task Review: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-15T16:17:43+00:00

## Summary

The SPA, web service, QA compose file, scenario runner, e2e wrapper, environment.yaml command and structural test changes appear present, and the report claims the unittest suite passes. However, the required acceptance criterion for the e2e stand is not met: the report explicitly states that the declared e2e command (`sh scripts/e2e.sh`) could not be run in the sandbox; instead its individual docker compose steps were executed separately. The reported output is therefore not the actual output of the declared e2e command and is truncated with an ellipsis, so an independent review cannot confirm an exit-0 run of that command. The remaining product requirements and constraints appear satisfied from the available evidence.

## Requirements

- web/: React SPA source (index.html plus a build-free or bundled entry) fetching /healthz from the api service and rendering the result, with a Dockerfile or nginx-style static serving configuration used by compose.yaml: pass — web/index.html, web/src/main.jsx, web/src/App.jsx, web/Dockerfile and web/nginx.conf are present; the report describes the nginx proxy to api:8000 and rendering of the health result.
- compose.yaml gains a web service and a qa profile (or separate docker/docker-compose.qa.yml) starting api, postgres, object storage and web on an isolated network without publishing cloud resources: pass — compose.yaml and docker/docker-compose.qa.yml are present; the report states the QA stand uses an internal network with no host ports and no cloud references.
- qa/ contains a headless-browser scenario runner (Playwright or equivalent) with at least one scenario loading the SPA, asserting the health status text appears and the API request returns 200: pass — qa/scenario.js, qa/package.json and qa/Dockerfile are present; the report describes a Playwright scenario asserting the SPA load, the health text and the /healthz 200 response.
- The template environment.yaml declares a non-empty e2e command that builds and runs the qa profile and exits non-zero on scenario failure: pass — environment.yaml declares `sh scripts/e2e.sh`; scripts/e2e.sh builds the QA stack, runs the qa profile and uses `set -e` to fail the gate.
- tests/test_template_django_drf_react.py is extended to assert the web service, the qa profile file, at least one qa scenario file and the non-empty e2e command in the template environment.yaml: pass — The test file is modified; the report states it asserts these items and verifies the e2e command through src/forgel/environment.py.
- Acceptance: the extended structural template test passes, including the e2e assertions: pass — The report states `python -m unittest tests.test_template_django_drf_react -v` exits 0 with 27 tests.
- Acceptance: the template e2e command is a well-formed argument list accepted by Forgel's environment parser, verified by the test through src/forgel/environment.py: pass — The report states the test verifies the declared command via `command_argv`/`parse_environment` from src/forgel/environment.py.
- Acceptance: the task report contains the actual output of the e2e command in the isolated compose stand, showing exit 0, and an independent review confirms the output: fail — The report explicitly says `scripts/e2e.sh` could not be launched; it shows separately executed docker compose steps with truncated output, not the actual output of the declared e2e command. An independent review therefore cannot confirm an exit-0 run of `sh scripts/e2e.sh`.
- Constraint: no browser download, Docker run or network access in the unittest suite: pass — The report states the tests only read template files and parse environment.yaml; no evidence of Docker or network access in the unittest suite was found.
- Constraint: the e2e stand must not publish ports beyond the local machine or contact Yandex Cloud: pass — The report states the QA compose file uses an internal network, publishes no host ports and has no cloud references.
- Constraint: public text in English: pass — The report and template text are in English.
- No deleted tests without an allowed justification: pass — No test removals were detected in the attributed commits.

## Blocking

- The required e2e acceptance criterion is not met: the task report does not contain the actual output of the declared e2e command (`sh scripts/e2e.sh`) in the isolated compose stand. It admits the wrapper could not be launched and instead shows separately executed docker compose steps with truncated output, so an independent review cannot confirm an exit-0 run of the declared command.

## Test Removals

- none


