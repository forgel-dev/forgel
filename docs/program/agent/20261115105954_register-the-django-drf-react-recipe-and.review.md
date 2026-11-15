# Task Review: Register the django-drf-react recipe and validate registry entries

- Task: `20261115105954_register-the-django-drf-react-recipe-and`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-15T17:30:24+00:00

## Summary

The attributed change adds the django-drf-react registry entry with the required version, status, composes, constraints, regions, excludes and template; extends forgel.registry with deterministic validation invoked by load_registry; preserves select_recipe behavior; and adds tests covering selection in ru, non-selection in us, duplicate ids and missing template directories. The validation also covers malformed composes, non-numeric versions and unknown statuses. Tests pass per the provided acceptance evidence, and no test removals, secrets or unrequested behavior were found.

## Requirements

- Add a second registry entry with id django-drf-react, version 0.1.0, status conformant, the specified composes list, requires list, regions [ru], excludes [mobile, regulated], and template django-drf-react.: pass — registry/recipes.json contains the entry with all specified fields and values.
- Extend src/forgel/registry.py with deterministic validation rejecting duplicate ids, malformed composes entries missing '@', non-numeric versions, conformant recipes whose template directory does not exist, and unknown statuses; load_registry calls it and raises RegistryError.: pass — validate_recipes implements each check in registry order and load_registry invokes it before returning; all failures raise RegistryError.
- Keep select_recipe behavior unchanged for existing callers, filtering by requires, excludes, status and region.: pass — select_recipe is unchanged and existing tests for hello-web selection and region/capability filtering remain in place.
- Extend tests/test_registry.py to cover selectability for the Django/React/Postgres/S3 requirements in region ru, non-selection for region us, validation failure on duplicate id, and validation failure on missing template directory.: pass — The added tests assert the django-drf-react recipe is selected in ru, RegistryError is raised in us, and duplicate-id and missing-template-directory cases raise RegistryError.
- The extended registry tests pass.: pass — Acceptance evidence reports the registry validation and selection tests passing with exit 0.
- Selecting for the Django/React/Postgres/S3 request in region ru returns django-drf-react, and region us raises RegistryError, as asserted by tests.: pass — Both behaviors are directly asserted in the added tests.
- make demo still completes against the hello-web recipe.: pass — Acceptance evidence reports that hello-web selection still works and the M0 demo requirement checks pass.
- Registry changes are data plus validation code only; recipe ids are not hardcoded in the matcher.: pass — select_recipe remains generic and does not reference django-drf-react or any specific recipe id.
- No network access in tests.: pass — The added tests use local temporary files and the repository registry only.
- Registry JSON stays valid JSON with stable ordering.: pass — The file remains a valid JSON object with the new recipe appended after hello-web and no reordering removed.

## Blocking

- none

## Test Removals

- none


