# Task Review: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-15T17:52:30+00:00

## Summary

The template now ships the React SPA (web/index.html plus an esbuild-bundled entry in web/src/, web/Dockerfile and an nginx config proxying /healthz to api:8000), a web service in compose.yaml, an isolated QA stand in docker/docker-compose.qa.yml (api, postgres, minio, web and an on-demand qa profile service on a single internal:true network with no published ports and no cloud references), a headless Playwright scenario in qa/scenario.js that loads the SPA, asserts the index is 200, asserts the /healthz request returns 200 with {"status":"ok"} and asserts the rendered health text, and a set -e wrapper scripts/e2e.sh that builds and runs the qa profile and tears the stand down. environment.yaml declares e2e: ["sh scripts/e2e.sh"], and tests/test_template_django_drf_react.py verifies the web service, the QA compose file, a qa scenario file and the non-empty e2e command, parsing it through src/forgel/environment.py. The report records the declared command's own output with exit 0 and 5/5 scenario checks passed, and the unittest suite performs no browser download, Docker run or network access. No test removals, no committed secrets (only clearly-labelled qa-only placeholders), and no unrequested features were found; the only noise is the run-log block in the report's test-output section, which does not affect the required evidence.

## Requirements

- web/: React SPA source (index.html plus build-free or bundled entry) that fetches /healthz from the api service and renders the result, with a Dockerfile or nginx static serving configuration used by compose.yaml: pass — web/index.html, web/src/main.jsx, web/src/App.jsx, web/package.json (esbuild), web/Dockerfile and web/nginx.conf proxying /healthz to api:8000; compose.yaml builds context web.
- compose.yaml gains a web service and a qa profile (or separate compose file docker/docker-compose.qa.yml) starting api, postgres, object storage and web on an isolated network without publishing cloud resources: pass — compose.yaml has the web service; docker/docker-compose.qa.yml defines api, postgres, minio, web plus the qa profile on a single internal:true network with no published ports and no cloud endpoints.
- qa/ contains a headless-browser scenario runner with at least one scenario: load the SPA, assert the health status text appears, and assert the API request returns 200: pass — qa/scenario.js uses playwright-core with the image's chromium, awaits the /healthz response, checks 200 and {"status":"ok"}, and asserts the rendered 'Health: ok (HTTP 200)' text, exiting non-zero on failure; qa/Dockerfile and qa/package.json complete the runner.
- The template environment.yaml declares a non-empty e2e command that builds and runs the qa profile and exits non-zero on scenario failure: pass — e2e: ["sh scripts/e2e.sh"]; the wrapper runs build, up --detach --wait, run --rm qa and down under set -e with an EXIT trap, forwarding the scenario exit code.
- tests/test_template_django_drf_react.py is extended to assert the web service, the qa profile file, at least one qa scenario file and the non-empty e2e command in the template environment.yaml: pass — Structural test covers the web service, docker-compose.qa.yml, qa/scenario.js and the e2e command; acceptance run reports exit 0.
- Acceptance: the extended structural template test passes, including the e2e assertions: pass — Acceptance check 'Structural test covers web, qa profile, scenario file and e2e command' passed with exit 0.
- Acceptance: the template e2e command is a well-formed argument list accepted by src/forgel/environment.py, verified by the test through that module: pass — Acceptance check 'template environment.yaml parses through src/forgel/environment.py with a test and an e2e command' passed; the test uses parse_environment/command_argv.
- Acceptance (review-only): the task report contains the actual output of the e2e command in the isolated compose stand showing exit 0, independently confirmed: pass — The report's E2E Output section shows the wrapper's own run: 5/5 scenario PASS lines, 'e2e: the isolated QA stand passed', the compose stand progress, and the recorded exit 0 from the subprocess invocation of `sh scripts/e2e.sh`.
- Constraint: no browser download, Docker run or network access in the unittest suite: pass — Tests only read template files and parse environment.yaml; no docker or network calls are made in the suite.
- Constraint: the e2e stand must not publish ports beyond the local machine or contact Yandex Cloud: pass — The qa stand publishes no host ports, its network is internal:true, and there are no cloud endpoints or credentials — only qa-only placeholder values.
- Constraint: public text in English: pass — All added comments, docs and scenario messages are in English.

## Blocking

- none

## Test Removals

- none


