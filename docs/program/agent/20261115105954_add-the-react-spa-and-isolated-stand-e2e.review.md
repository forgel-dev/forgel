# Task Review: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-15T17:18:18+00:00

## Summary

The product slice is in place: web/ holds a React SPA bundled by esbuild and served by nginx proxying /healthz to api:8000, compose.yaml declares the web service, docker/docker-compose.qa.yml is an isolated stand (api, postgres, minio, web plus the on-demand qa profile) on a single internal network with no published ports or cloud references, qa/scenario.js is a playwright-core headless scenario that asserts the /healthz 200 response and the rendered health text and exits non-zero on failure, environment.yaml declares e2e: ["sh scripts/e2e.sh"] which builds and runs the profile under set -e, and the structural test covers all of it and parses the command through src/forgel/environment.py. The blocking gap is the review-only acceptance criterion and evidence quality: the report states the declared e2e command wrapper could not be launched and instead records a series of separate docker compose invocations, so it does not contain the actual output/exit status of the e2e command itself; worse, the three successive report versions disagree about whether `sh scripts/e2e.sh` ran at all, and the section labelled 'Final Test Output' contains orchestration pipeline stage logs ([intake]/[dev]/[qa]/...) rather than the unittest transcript the report claims, which makes the recorded evidence untrustworthy.

## Requirements

- web/ contains a React SPA source (index.html plus a build-free or bundled entry) that fetches /healthz from the api service and renders the result, with a Dockerfile or nginx-style static serving configuration used by compose.yaml.: pass — web/index.html, src/main.jsx, src/App.jsx fetch /healthz through the nginx proxy to api:8000 and render status in [data-testid="health-status"]; web/Dockerfile builds with esbuild and web/nginx.conf serves the bundle; compose.yaml builds the web service from web/.
- compose.yaml gains a web service and a qa profile (or docker/docker-compose.qa.yml) that starts api, postgres, object storage and web on an isolated network without publishing cloud resources.: pass — compose.yaml declares the web service next to api/postgres/minio; docker/docker-compose.qa.yml defines api, postgres, minio, web and the qa profile on the single 'qa' network marked internal: true, with no published ports and no cloud endpoints.
- qa/ contains a headless-browser scenario runner with at least one scenario: load the SPA, assert the health status text appears, and assert the API request returns 200.: pass — qa/scenario.js launches chromium via playwright-core, waits for the /healthz response, asserts status 200 and {"status":"ok"}, asserts the rendered 'Health: ok (HTTP 200)' text, and exits 1 when any check fails; qa/Dockerfile uses Alpine chromium with no browser download.
- The template environment.yaml declares a non-empty e2e command that builds and runs the qa profile and exits non-zero on scenario failure.: pass — environment.yaml declares e2e: ["sh scripts/e2e.sh"]; scripts/e2e.sh cd's to the template root, builds the QA stack, brings up api/postgres/minio/web with --wait, runs the qa profile service with --exit-code-from semantics of `run --rm` (exit code propagates) under `set -e`, and tears down in an EXIT trap.
- tests/test_template_django_drf_react.py is extended to assert the web service, the qa profile file, at least one qa scenario file and the non-empty e2e command in the template environment.yaml.: pass — Acceptance run reports the structural test passing (exit 0) with assertions for the web service, docker/docker-compose.qa.yml, qa/scenario.js and the non-empty e2e command; previous compose assertions were kept rather than deleted (no test removals detected).
- Acceptance: the extended structural template test passes, including the e2e assertions.: pass — Recorded acceptance check 'Structural test covers web, qa profile, scenario file and e2e command: pass (exit 0)'.
- Acceptance: the template e2e command is a well-formed argument list that Forgel's environment parser accepts, verified by the test through src/forgel/environment.py.: pass — Acceptance check 'The template environment.yaml parses through src/forgel/environment.py with a test and an e2e command: pass (exit 0)'; the test exercises parse_environment/command_argv.
- Review-only acceptance: the task report contains the actual output of the e2e command in the isolated compose stand, showing exit 0, and an independent review confirms the output.: fail — The report explicitly says the declared command wrapper could not be launched ('the agent runtime of this session only permits docker compose invocations') and records separate compose invocations instead of the e2e command's output and exit status. Successive report versions contradict each other on whether `sh scripts/e2e.sh` was ever executed, and the section titled 'Final Test Output' contains orchestration pipeline stage logs, not the unittest transcript the report claims, so the evidence cannot be independently confirmed.

## Blocking

- The task report does not contain the actual output of the declared e2e command (`sh scripts/e2e.sh`) in the isolated compose stand: it states the wrapper was not executed and substitutes separate docker compose step transcripts, so the review-only acceptance criterion is unmet; the report versions also conflict on whether the wrapper ran, and the 'Final Test Output' block records pipeline stage logs instead of the claimed unittest output.

## Test Removals

- none


