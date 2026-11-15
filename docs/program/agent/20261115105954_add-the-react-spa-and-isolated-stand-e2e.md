# Agent Run: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Status: `done`
- Repository: `main`
- Steps: 27
- Finished: 2026-11-15T17:00:01+00:00

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

- The two flagged tests are kept side by side instead of merged: the exact service set is asserted by `test_declares_the_api_web_postgres_and_object_storage`, while `test_declares_the_api_postgres_and_object_storage` asserts the backend slice as a subset, which is the smallest change that keeps the original scenario meaningful now that the SPA adds `web` to compose.yaml.
- The e2e command remains `sh scripts/e2e.sh` because environment.yaml has no working directory of its own and the template already uses script wrappers for setup/test.
- The QA stand is a separate compose file (docker/docker-compose.qa.yml) plus a `qa` profile service rather than a second profile in compose.yaml, which keeps the development compose.yaml free of browser tooling.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 27
- Estimated input tokens (all calls): 505920
- Provider input/output tokens: 537558 / 8423
- Estimated prompt at the end: 28168 tokens
- State: not needed

## Summary

Finished the retry by resolving the only blocking review defect: the two compose assertions that had been removed are back in tests/test_template_django_drf_react.py, and all product work from the previous attempt is preserved.

Tests (tests/test_template_django_drf_react.py):
- `ComposeServicesTest.test_declares_the_api_web_postgres_and_object_storage` is restored to its exact-set form (`{api, web, postgres, minio}` for the template compose.yaml) and passes.
- `ComposeServicesTest.test_declares_the_api_postgres_and_object_storage` is restored as the backend-slice assertion (`{api, postgres, minio}` is a subset of the declared services) so the SPA's `web` service does not make the historical assertion wrong; it passes.
- No test was deleted or weakened. The added coverage stays: `test_declares_the_web_service`, `WebAppTest` (SPA fetches /healthz, esbuild build + nginx proxy to api:8000, compose web service with `context: web` / `WEB_PORT`), `QaStandTest` (qa profile file declares api, postgres, minio, web and the `qa` profile service; no published ports, `internal: true`, no Yandex Cloud references; Playwright scenario asserts the health text and the `/healthz` 200 and exits non-zero on failure), and `TemplateEnvironmentTest` e2e contract tests (non-empty e2e command, well-formed argv via `command_argv` from src/forgel/environment.py, wrapper builds/starts the stand and runs the qa profile with `set -e`).

Product work kept as delivered:
- `web/`: React SPA (`index.html`, `src/main.jsx`, `src/App.jsx`) fetching `/healthz` and rendering it into `[data-testid="health-status"]`, bundled with esbuild in `web/Dockerfile`, served by nginx with `proxy_pass` to `api:8000`; `compose.yaml` gains the `web` service.
- `docker/docker-compose.qa.yml`: isolated stand with api, postgres, minio, web and the on-demand `qa` profile service, one `internal: true` network, no published ports.
- `qa/`: headless Playwright scenario runner (`scenario.js`, `Dockerfile`, `package.json`) that loads the SPA, asserts the health status text appears, asserts the API request returned 200 and exits non-zero on failure.
- `environment.yaml`: `e2e: ["sh scripts/e2e.sh"]` — non-empty, parses through src/forgel/environment.py; `scripts/e2e.sh` builds the stand, brings up api/postgres/minio/web, runs `--profile qa run --rm qa`, tears down via an EXIT trap and fails the command on any error.

Verification run in this session (no browser download, no Docker run, no network in the suite):
- `python -m unittest tests.test_template_django_drf_react -v` -> 30 tests, OK (exit 0), including `test_declares_the_api_postgres_and_object_storage ... ok` and `test_declares_the_api_web_postgres_and_object_storage ... ok`.
- `python -m unittest discover -s tests` -> 477 tests, OK (exit 0).

The e2e evidence requested by the acceptance criteria (actual output of the template e2e command in the isolated compose stand with exit 0) is recorded in docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.qa.md (Verdict PASS, Exit code 0, environment e2e: pass) and referenced from the task report docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md.

## Files Changed

- none

## Commands

- `["python", "-m", "unittest", "tests.test_template_django_drf_react", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "diff", "HEAD", "--", "tests/test_template_django_drf_react.py"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115165906_inspect-and-finish: context handoff to session 2 (~4815/3072 tokens)
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
Ran 477 tests in 65.691s

OK

```

## Actions

- list_files
- read_file: tests/test_template_django_drf_react.py
- run: ['python', '-m', 'unittest', 'tests.test_template_django_drf_react', '-v']
- list_files
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.md
- read_file: src/forgel/templates/django-drf-react/environment.yaml
- read_file: src/forgel/templates/django-drf-react/scripts/e2e.sh
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.review.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['git', 'diff', 'HEAD', '--', 'tests/test_template_django_drf_react.py']
- run: ['git', 'status', '--short']
- read_file: docs/program/agent/20261115105954_add-the-react-spa-and-isolated-stand-e2e.qa.md
