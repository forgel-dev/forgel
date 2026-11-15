# Agent Run: Register the django-drf-react recipe and validate registry entries

- Task: `20261115105954_register-the-django-drf-react-recipe-and`
- Status: `done`
- Repository: `main`
- Steps: 39
- Finished: 2026-11-15T17:29:04+00:00

## Requirements

- Add a second entry to registry/recipes.json with id django-drf-react, version 0.1.0, status conformant, composes the stack (stack-django-drf, frontend-react, db-postgres, storage-s3, provider-yandex, qa-browser), requires ["web", "django", "react", "postgres", "object-storage"], regions ["ru"], excludes ["mobile", "regulated"], template django-drf-react.
- Extend src/forgel/registry.py with a deterministic validation function that rejects: duplicate ids, malformed composes entries (missing '@'), non-numeric versions, a conformant recipe whose template directory does not exist under src/forgel/templates/, and unknown status values; the loader calls it and raises RegistryError.
- Keep select_recipe behavior unchanged for existing callers: requirements still filter by requires, excludes, status and region.
- Extend tests/test_registry.py to cover: the recipe is selectable for requirements {requires: [web, django, react, postgres, object-storage], region: ru}, is not selected for region us, validation raises on a duplicate id and on a missing template directory.

## Acceptance Criteria

- The extended registry tests pass.
- Selecting a recipe for a Django/React/Postgres/S3 request in region ru returns django-drf-react, and region us raises RegistryError — asserted by the tests.
- make demo still completes against the hello-web recipe, so existing projects are unaffected.

## Constraints

- Registry changes are data plus validation code only; do not hardcode recipe ids in the matcher.
- No network access in tests.
- Registry JSON stays valid JSON with stable ordering.

## Assumptions

- Composes entries use name@version with the same `@0.1` suffix convention as the existing hello-web recipe.
- Known statuses are draft, conformant and deprecated; unknown values are rejected.
- The template-directory check only applies to conformant recipes, so drafts may point at a not-yet-created template.
- Validation defaults to the package templates directory (src/forgel/templates) and accepts an optional override for tests.
- Template existence is checked with is_dir() and does not inspect template contents.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 39
- Estimated input tokens (all calls): 727000
- Provider input/output tokens: 771634 / 18741
- Estimated prompt at the end: 37164 tokens
- State: not needed

## Summary

Registered the django-drf-react recipe and added deterministic registry validation.

- registry/recipes.json: added a second entry `django-drf-react` @ 0.1.0, status `conformant`, composing stack-django-drf, frontend-react, db-postgres, storage-s3, provider-yandex, qa-browser (each pinned with `@0.1` like the existing hello-web entry), requires [web, django, react, postgres, object-storage], regions [ru], excludes [mobile, regulated], template `django-drf-react`. The existing hello-web entry is untouched and key order is stable.
- src/forgel/registry.py: added `validate_recipes(recipes, templates_path=None)` and made `load_registry(path, templates_path=None)` call it before returning. It rejects duplicate ids, composes entries without `@`, non-numeric versions, unknown statuses (draft/conformant/deprecated) and conformant recipes whose template directory is missing under src/forgel/templates/ (default templates root = the package `templates/` dir). Every fault raises `RegistryError` with a message naming the recipe. `select_recipe` is unchanged, so existing callers keep filtering by requires/excludes/status/region and no recipe id is hardcoded.
- tests/test_registry.py: kept all existing tests and added coverage for the new recipe (registered fields), selection for {requires: [web, django, react, postgres, object-storage], region: ru} returning django-drf-react, non-selection with region us (RegistryError), plus validation cases for duplicate id, missing template directory, malformed composes, non-numeric version, unknown status, and a draft recipe allowed to omit its template.

Testing: `python -m unittest discover -s tests` — 487 tests, OK (including the 14 registry tests). `python -m compileall -q -x templates src tests` passes. `python -m forgel demo --home /tmp/forgel-demo-check` runs the full hello-web pipeline to the staging-approval checkpoint, confirming existing projects are unaffected. `make demo` against the checked-out `.forgel-demo` home failed with `sqlite3.OperationalError: no such column: generation` — that is pre-existing local demo state whose ledger schema predates the generation column; no ledger/code path was changed here, and a fresh home runs the demo fine.

## Files Changed

- `registry/recipes.json`
- `src/forgel/registry.py`
- `tests/test_registry.py`

## Commands

- `["python", "-c", "print(1)"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-k", "registry"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests", "-k", "registry", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["make", "demo"]` → exit 2
- `["python", "-m", "forgel", "demo", "--home", "/tmp/forgel-demo-check"]` → exit 0
- `["python", "-m", "compileall", "-q", "-x", "templates", "src", "tests"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115172814_inspect-and-finish: context handoff to session 2 (~4817/3072 tokens)
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
.......................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 487 tests in 59.594s

OK

```

## Actions

- read_file: registry/recipes.json
- read_file: src/forgel/registry.py
- read_file: tests/test_registry.py
- read_file: Makefile
- read_file: src/forgel/layout.py
- run: ['python', '-c', 'print(1)']
- list_files
- run: ['grep', '-rn', 'template', 'src/forgel/demo.py']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-k', 'registry']
- read_file: src/forgel/projects.py
- read_file: src/forgel/cli.py
- write_file: registry/recipes.json
- list_files
- list_files
- read_file: src/forgel/templates/hello-web/README.md
- read_file: src/forgel/templates/django-drf-react/README.md
- read_file: src/forgel/cli.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/orchestrator.py
- read_file: src/forgel/config.py
- read_file: src/forgel/artifacts.py
- read_file: src/forgel/templates/hello-web/web/index.html
- write_file: src/forgel/registry.py
- write_file: tests/test_registry.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests', '-k', 'registry', '-v']
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['make', 'demo']
- read_file: src/forgel/ledger.py
- run: ['python', '-m', 'forgel', 'demo', '--home', '/tmp/forgel-demo-check']
- read_file: .gitignore
- run: ['python', '-m', 'compileall', '-q', '-x', 'templates', 'src', 'tests']
