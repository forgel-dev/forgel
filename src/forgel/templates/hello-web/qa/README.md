# QA Runner

Ported from the Gapi QA pattern: the product runs in a Docker Compose stand,
and a headless Chrome runner drives the acceptance scenario.

## Run

```bash
docker compose -f docker/docker-compose.qa.yml up -d --build
npm --prefix qa install
QA_BASE_URL=http://127.0.0.1:8000 node qa/runner.mjs
docker compose -f docker/docker-compose.qa.yml down -v
```

- `CHROME_PATH` overrides the browser executable.
- `--base-url` overrides `QA_BASE_URL`.
- `--scenario` selects a module from `qa/scenarios/`.
- A scenario exports `run({ page, baseUrl, check })`.
- The runner exits non-zero when any check fails or when the browser console or
  page raises an error.

This is the M0 pattern. M1 will reuse the same runner for the Django/React
product, with a database reset before each scenario and the full suite guard.
