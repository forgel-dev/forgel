# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Steps: 22
- Finished: 2026-11-15T17:16:53+00:00

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

- The two previously flagged compose tests are kept side by side instead of merged: test_declares_the_api_web_postgres_and_object_storage asserts the exact service set {api, web, postgres, minio}, test_declares_the_api_postgres_and_object_storage asserts the backend slice as a subset.
- The e2e command stays `sh scripts/e2e.sh` because environment.yaml has no working directory of its own and the template already uses script wrappers for setup and test.
- The QA stand lives in a separate compose file docker/docker-compose.qa.yml with a `qa` profile service rather than a second profile in compose.yaml, keeping the development compose.yaml free of browser tooling.
- Because this session's runtime only allows `docker compose` invocations, the stand was executed step by step with exactly the compose commands scripts/e2e.sh runs (config --quiet, --profile qa build, up --detach --wait api postgres minio web, --profile qa run --rm qa, --profile qa down --volumes --remove-orphans) and those real transcripts are what the report records.
- Images were taken from the local Docker cache and the `qa` network is internal: true, so the stand neither publishes host ports nor contacts Yandex Cloud.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 22
- Estimated input tokens (all calls): 376137
- Provider input/output tokens: 395149 / 19533
- Estimated prompt at the end: 34883 tokens
- State: not needed

## Summary

Completed the retry: the SPA/e2e product slice is intact (web/ React SPA bundled with esbuild and served by nginx proxying /healthz to api:8000, web service in compose.yaml, docker/docker-compose.qa.yml isolated stand with api/postgres/minio/web plus the on-demand `qa` profile service on a single internal network with no published ports and no cloud references, qa/scenario.js Playwright headless scenario, environment.yaml e2e: ["sh scripts/e2e.sh"], extended tests/test_template_django_drf_react.py), and I addressed the single remaining blocking defect by actually executing the isolated compose stand in this session and recording its real output in the task report. Commands run and their exits: `docker compose ... config --quiet` (0), `--profile qa build` (0), `up --detach --wait api postgres minio web` (0, all four services Healthy), `--profile qa run --rm qa` (0, 5/5 checks: SPA index 200, /healthz 200, body {"status":"ok"}, rendered text 'Health: ok (HTTP 200)'), `--profile qa down --volumes --remove-orphans` (0). These are exactly the compose steps scripts/e2e.sh executes; the agent runtime of this session only permits `docker compose` invocations, so the wrapper itself could not be launched, but the stand the wrapper drives ran end to end with exit 0. Tests: `python -m unittest tests.test_template_django_drf_react -v` -> 30 tests OK (exit 0); `python -m unittest discover -s tests` -> 477 tests OK (exit 0). The unittest suite itself performs no browser download, Docker run or network access. The updated report docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md now contains the E2E Stand Output section with the verbatim transcripts and the Final Test Output block with the real unittest output. No tests were removed or weakened; the earlier deleted compose assertions are present.

## Files Changed

- `docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md`

## Commands

- `["docker", "compose", "version"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "config", "--quiet"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "build", "web"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "build"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "up", "--detach", "--wait", "api", "postgres", "minio", "web"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "run", "--rm", "qa"]` → exit 0
- `["docker", "compose", "-f", "src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml", "--profile", "qa", "down", "--volumes", "--remove-orphans"]` → exit 0
- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115171605_inspect-and-finish: context handoff to session 2 (~4816/3072 tokens)
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
.............................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 477 tests in 57.705s

OK

```

## Actions

- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- read_file: src/forgel/templates/django-drf-react/scripts/e2e.sh
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.qa.md
- read_file: src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml
- run: ['docker', 'version', '--format', '{{.Server.Version}}']
- run: ['docker', 'compose', 'version']
- read_file: src/forgel/templates/django-drf-react/qa/Dockerfile
- read_file: src/forgel/templates/django-drf-react/web/Dockerfile
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'config', '--quiet']
- read_file: src/forgel/templates/django-drf-react/qa/scenario.js
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'build', 'web']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'build']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', 'up', '--detach', '--wait', 'api', 'postgres', 'minio', 'web']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'run', '--rm', 'qa']
- run: ['docker', 'compose', '-f', 'src/forgel/templates/django-drf-react/docker/docker-compose.qa.yml', '--profile', 'qa', 'down', '--volumes', '--remove-orphans']
- run: ['python', '-m', 'unittest', 'tests.test_template_django_drf_react', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- write_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
