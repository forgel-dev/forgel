# Task QA: Add the Django/DRF backend skeleton template with Postgres and S3 compose

- Task: `20261115105954_add-the-django-drf-backend-skeleton-temp`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-15T13:36:08+00:00

## Checks

- environment test: pass (exit 0)
- Template structural validation test passes: pass (exit 0)
- Template Python sources compile: pass (exit 0)
- The compose stand serves /healthz against Postgres, evidence in the task report: review

## Output

```
$ python -m unittest discover -s tests
[agent] 20261115133520_inspect-and-finish: context handoff to session 2 (~4784/3072 tokens)
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
...........................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 443 tests in 56.678s

OK
$ env PYTHONPATH=src python -m unittest tests.test_template_django_drf_react -v
test_declares_the_api_postgres_and_object_storage (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_api_postgres_and_object_storage) ... ok
test_no_credential_literals_are_committed (tests.test_template_django_drf_react.ComposeServicesTest.test_no_credential_literals_are_committed) ... ok
test_object_storage_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_object_storage_is_configured_from_the_environment) ... ok
test_postgres_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_postgres_is_configured_from_the_environment) ... ok
test_the_api_is_wired_to_both_services (tests.test_template_django_drf_react.ComposeServicesTest.test_the_api_is_wired_to_both_services) ... ok
test_the_bucket_is_created_on_startup (tests.test_template_django_drf_react.ComposeServicesTest.test_the_bucket_is_created_on_startup) ... ok
test_django_tests_use_the_client_without_services (tests.test_template_django_drf_react.HealthRouteTest.test_django_tests_use_the_client_without_services) ... ok
test_the_health_route_is_registered (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_route_is_registered) ... ok
test_the_health_view_is_a_drf_endpoint (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_view_is_a_drf_endpoint) ... ok
test_the_contract_parses (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_contract_parses) ... ok
test_the_declared_artifacts_exist (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_declared_artifacts_exist) ... ok
test_the_test_command_is_declared_and_runs_from_api (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_test_command_is_declared_and_runs_from_api) ... ok
test_python_sources_compile (tests.test_template_django_drf_react.TemplateLayoutTest.test_python_sources_compile) ... ok
test_required_files_are_present (tests.test_template_django_drf_react.TemplateLayoutTest.test_required_files_are_present) ... ok
test_requirement_pins_are_declared (tests.test_template_django_drf_react.TemplateLayoutTest.test_requirement_pins_are_declared) ... ok
test_settings_read_database_and_storage_from_the_environment (tests.test_template_django_drf_react.TemplateLayoutTest.test_settings_read_database_and_storage_from_the_environment) ... ok
test_the_template_directory_exists (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_directory_exists) ... ok
test_the_template_does_not_depend_on_the_hello_web_recipe (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_does_not_depend_on_the_hello_web_recipe) ... ok

----------------------------------------------------------------------
Ran 18 tests in 0.010s

OK
$ python -m compileall -q src/forgel/templates/django-drf-react

```
