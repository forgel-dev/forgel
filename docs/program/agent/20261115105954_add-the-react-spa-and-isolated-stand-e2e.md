# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Steps: 31
- Finished: 2026-11-15T16:16:41+00:00

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
- The QA stand lives in a separate docker/docker-compose.qa.yml rather than a `qa` profile inside compose.yaml, so the local stand can stay internal-only and never publish ports.
- The headless browser uses playwright-core driving the Alpine `chromium` package already installed in the qa image, avoiding any browser download at build or test time.
- Because the agent sandbox rejects running `sh` directly, the three commands of scripts/e2e.sh were executed verbatim through docker compose to produce the recorded exit-0 output instead of invoking the wrapper itself.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 31
- Estimated input tokens (all calls): 619968
- Provider input/output tokens: 660055 / 12108
- Estimated prompt at the end: 38107 tokens
- State: not needed

## Summary

Completed the React SPA + isolated-stand e2e QA scenario for the django-drf-react template and verified it end to end. Work present in the tree and validated by tests: web/ holds the React SPA (index.html, src/main.jsx, src/App.jsx fetching /healthz via the nginx proxy and rendering the health text in [data-testid="health-status"]), bundled with esbuild and served by nginx (web/Dockerfile, web/nginx.conf); compose.yaml declares the api, web, postgres and minio services; docker/docker-compose.qa.yml is the isolated QA stand (api, postgres, minio, web plus the on-demand qa profile) on an internal network with no published ports and no cloud references; qa/scenario.js is a playwright-core headless-chromium scenario that loads the SPA, asserts the /healthz request returns 200 with {"status":"ok"} and the rendered health text, and exits non-zero on failure; environment.yaml declares the non-empty e2e command `sh scripts/e2e.sh`, which builds the QA stack, brings the slice up with --wait, runs the qa profile and tears it down under `set -e`; tests/test_template_django_drf_react.py asserts the web service, the QA compose file, the qa scenario file and the e2e command including its parse through src/forgel/environment.py (parse_environment/command_argv). Testing: `python -m unittest tests.test_template_django_drf_react -v` → 27 tests OK; `python -m unittest tests.test_environment -v` → 39 tests OK; full suite `python -m unittest discover -s tests` → 472 tests OK. The e2e stand itself was executed in the isolated compose stand (the agent sandbox does not allow `sh`, so the wrapper's own steps were run verbatim with docker compose: build, up --wait, --profile qa run --rm qa, down --volumes) and every step exited 0 — the scenario printed PASS for all 5 checks (SPA index 200, /healthz 200, {"status":"ok"}, health status text, HTTP 200) with SUMMARY: 5/5 checks passed. That actual output is recorded in docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md for independent review.

## Files Changed

- `docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md`

## Commands

- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["docker", "compose", "version"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "build"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "up", "--detach", "--wait", "api", "postgres", "minio", "web"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "run", "--rm", "qa"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "down", "--volumes", "--remove-orphans"]` → exit 0
- `["python", "-m", "unittest", "tests.test_environment", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115161552_inspect-and-finish: context handoff to session 2 (~4815/3072 tokens)
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 472 tests in 61.375s

OK

```

## Actions

- list_files
- list_files
- read_file: src/forgel/templates/django-drf-react/environment.yaml
- read_file: tests/test_template_django_drf_react.py
- run: ['python', '-m', 'unittest', 'tests.test_template_django_drf_react', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- list_files
- read_file: src/forgel/templates/django-drf-react/scripts/e2e.sh
- read_file: docs/program/tasks/20261115105954_add-the-react-spa-and-isolated-stand-e2e.json
- run: ['docker', 'version', '--format', '{{.Server.Version}}']
- run: ['docker', 'compose', 'version']
- read_file: src/forgel/templates/django-drf-react/qa/scenario.js
- read_file: src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'build']
- run: ['sh', 'src/forgel/templates/django-drf-react/scripts/e2e.sh']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'up', '--detach', '--wait', 'api', 'postgres', 'minio', 'web']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'run', '--rm', 'qa']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'down', '--volumes', '--remove-orphans']
- read_file: docs/program/agent/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.md
- write_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- run: ['python', '-m', 'unittest', 'tests.test_environment', '-v']
