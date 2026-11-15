# Task QA: Add the React SPA and isolated-stand e2e QA scenario to the template

- Task: `20261115105954_add-the-react-spa-and-isolated-stand-e2e`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-15T17:17:54+00:00

## Checks

- environment test: pass (exit 0)
- environment e2e: pass (exit 0)
- Structural test covers web, qa profile, scenario file and e2e command: pass (exit 0)
- The template environment.yaml parses through src/forgel/environment.py with a test and an e2e command: pass (exit 0)
- The e2e scenario passes in the isolated compose stand, with actual output in the task report: review

## Output

```
$ python -m unittest discover -s tests
[agent] 20261115171703_inspect-and-finish: context handoff to session 2 (~4817/3072 tokens)
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
Ran 477 tests in 58.708s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-f9f36717']]
PASS FORGEL_MODEL_MODE=script [script]
PASS the task stopped at the staging approval gate [review]
PASS task QA passed [pass]
PASS task review passed [pass]
PASS acceptance is pending a human decision [pending]
PASS the project never reached done [None]
PASS self-hosting gate is green and parked for human approval
$ env PYTHONPATH=src python -m unittest tests.test_template_django_drf_react -v
test_declares_the_api_postgres_and_object_storage (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_api_postgres_and_object_storage) ... ok
test_declares_the_api_web_postgres_and_object_storage (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_api_web_postgres_and_object_storage) ... ok
test_declares_the_web_service (tests.test_template_django_drf_react.ComposeServicesTest.test_declares_the_web_service) ... ok
test_no_credential_literals_are_committed (tests.test_template_django_drf_react.ComposeServicesTest.test_no_credential_literals_are_committed) ... ok
test_object_storage_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_object_storage_is_configured_from_the_environment) ... ok
test_postgres_is_configured_from_the_environment (tests.test_template_django_drf_react.ComposeServicesTest.test_postgres_is_configured_from_the_environment) ... ok
test_the_api_is_wired_to_both_services (tests.test_template_django_drf_react.ComposeServicesTest.test_the_api_is_wired_to_both_services) ... ok
test_the_bucket_is_created_on_startup (tests.test_template_django_drf_react.ComposeServicesTest.test_the_bucket_is_created_on_startup) ... ok
test_the_default_object_storage_image_is_minio (tests.test_template_django_drf_react.ComposeServicesTest.test_the_default_object_storage_image_is_minio) ... ok
test_django_tests_use_the_client_without_services (tests.test_template_django_drf_react.HealthRouteTest.test_django_tests_use_the_client_without_services) ... ok
test_the_health_route_is_registered (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_route_is_registered) ... ok
test_the_health_view_is_a_drf_endpoint (tests.test_template_django_drf_react.HealthRouteTest.test_the_health_view_is_a_drf_endpoint) ... ok
test_the_browser_scenario_runs_in_a_headless_browser (tests.test_template_django_drf_react.QaStandTest.test_the_browser_scenario_runs_in_a_headless_browser) ... ok
test_the_scenario_runs_in_the_qa_profile (tests.test_template_django_drf_react.QaStandTest.test_the_scenario_runs_in_the_qa_profile) ... ok
test_the_stand_is_isolated_from_the_host_and_the_internet (tests.test_template_django_drf_react.QaStandTest.test_the_stand_is_isolated_from_the_host_and_the_internet) ... ok
test_the_stand_runs_every_service_of_the_slice (tests.test_template_django_drf_react.QaStandTest.test_the_stand_runs_every_service_of_the_slice) ... ok
test_the_contract_parses (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_contract_parses) ... ok
test_the_declared_artifacts_exist (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_declared_artifacts_exist) ... ok
test_the_e2e_command_is_a_well_formed_argument_list (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_e2e_command_is_a_well_formed_argument_list) ... ok
test_the_e2e_command_is_declared_and_builds_the_qa_stand (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_e2e_command_is_declared_and_builds_the_qa_stand) ... ok
test_the_test_command_is_declared_and_runs_from_api (tests.test_template_django_drf_react.TemplateEnvironmentTest.test_the_test_command_is_declared_and_runs_from_api) ... ok
test_python_sources_compile (tests.test_template_django_drf_react.TemplateLayoutTest.test_python_sources_compile) ... ok
test_required_files_are_present (tests.test_template_django_drf_react.TemplateLayoutTest.test_required_files_are_present) ... ok
test_requirement_pins_are_declared (tests.test_template_django_drf_react.TemplateLayoutTest.test_requirement_pins_are_declared) ... ok
test_settings_read_database_and_storage_from_the_environment (tests.test_template_django_drf_react.TemplateLayoutTest.test_settings_read_database_and_storage_from_the_environment) ... ok
test_the_template_directory_exists (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_directory_exists) ... ok
test_the_template_does_not_depend_on_the_hello_web_recipe (tests.test_template_django_drf_react.TemplateLayoutTest.test_the_template_does_not_depend_on_the_hello_web_recipe) ... ok
test_compose_uses_the_web_image (tests.test_template_django_drf_react.WebAppTest.test_compose_uses_the_web_image) ... ok
test_the_spa_fetches_the_health_endpoint (tests.test_template_django_drf_react.WebAppTest.test_the_spa_fetches_the_health_endpoint) ... ok
test_the_spa_is_bundled_and_served_by_nginx (tests.test_template_django_drf_react.WebAppTest.test_the_spa_is_bundled_and_served_by_nginx) ... ok

----------------------------------------------------------------------
Ran 30 tests in 0.017s

OK
$ env PYTHONPATH=src python -m unittest tests.test_environment -v
test_empty_command_is_rejected (tests.test_environment.CommandArgvTest.test_empty_command_is_rejected) ... ok
test_other_executables_are_kept (tests.test_environment.CommandArgvTest.test_other_executables_are_kept) ... ok
test_python_is_resolved_to_the_running_interpreter (tests.test_environment.CommandArgvTest.test_python_is_resolved_to_the_running_interpreter) ... ok
test_a_single_repository_contract_is_discovered (tests.test_environment.LoadEnvironmentTest.test_a_single_repository_contract_is_discovered) ... ok
test_explicit_repository_is_the_workdir (tests.test_environment.LoadEnvironmentTest.test_explicit_repository_is_the_workdir) ... ok
test_legacy_contract_is_loaded_from_the_project_root (tests.test_environment.LoadEnvironmentTest.test_legacy_contract_is_loaded_from_the_project_root) ... ok
test_malformed_contract_raises_instead_of_falling_back (tests.test_environment.LoadEnvironmentTest.test_malformed_contract_raises_instead_of_falling_back) ... ok
test_missing_build_path_is_rejected (tests.test_environment.LoadEnvironmentTest.test_missing_build_path_is_rejected) ... ok
test_missing_contract_returns_none (tests.test_environment.LoadEnvironmentTest.test_missing_contract_returns_none) ... ok
test_several_repositories_default_to_the_project_root (tests.test_environment.LoadEnvironmentTest.test_several_repositories_default_to_the_project_root) ... ok
test_sole_repository_is_the_default_workdir (tests.test_environment.LoadEnvironmentTest.test_sole_repository_is_the_default_workdir) ... ok
test_the_control_repository_contract_wins (tests.test_environment.LoadEnvironmentTest.test_the_control_repository_contract_wins) ... ok
test_unknown_mount_repository_is_rejected (tests.test_environment.LoadEnvironmentTest.test_unknown_mount_repository_is_rejected) ... ok
test_unknown_repository_is_rejected (tests.test_environment.LoadEnvironmentTest.test_unknown_repository_is_rejected) ... ok
test_absolute_build_path_is_rejected (tests.test_environment.ParseEnvironmentTest.test_absolute_build_path_is_rejected) ... ok
test_block_list_and_flow_list_are_equivalent (tests.test_environment.ParseEnvironmentTest.test_block_list_and_flow_list_are_equivalent) ... ok
test_build_is_an_alternative_to_image (tests.test_environment.ParseEnvironmentTest.test_build_is_an_alternative_to_image) ... ok
test_comments_and_quotes (tests.test_environment.ParseEnvironmentTest.test_comments_and_quotes) ... ok
test_duplicate_key_is_rejected (tests.test_environment.ParseEnvironmentTest.test_duplicate_key_is_rejected) ... ok
test_empty_contract_is_rejected (tests.test_environment.ParseEnvironmentTest.test_empty_contract_is_rejected) ... ok
test_env_cannot_override_the_sandbox_home (tests.test_environment.ParseEnvironmentTest.test_env_cannot_override_the_sandbox_home) ... ok
test_env_mapping_is_parsed (tests.test_environment.ParseEnvironmentTest.test_env_mapping_is_parsed) ... ok
test_env_must_be_a_mapping (tests.test_environment.ParseEnvironmentTest.test_env_must_be_a_mapping) ... ok
test_escaping_build_path_is_rejected (tests.test_environment.ParseEnvironmentTest.test_escaping_build_path_is_rejected) ... ok
test_image_and_build_together_are_rejected (tests.test_environment.ParseEnvironmentTest.test_image_and_build_together_are_rejected) ... ok
test_image_may_contain_a_colon (tests.test_environment.ParseEnvironmentTest.test_image_may_contain_a_colon) ... ok
test_invalid_env_name_is_rejected (tests.test_environment.ParseEnvironmentTest.test_invalid_env_name_is_rejected) ... ok
test_invalid_health_is_rejected (tests.test_environment.ParseEnvironmentTest.test_invalid_health_is_rejected) ... ok
test_invalid_ports_are_rejected (tests.test_environment.ParseEnvironmentTest.test_invalid_ports_are_rejected) ... ok
test_invalid_repo_name_is_rejected (tests.test_environment.ParseEnvironmentTest.test_invalid_repo_name_is_rejected) ... ok
test_mounting_the_working_repository_is_rejected (tests.test_environment.ParseEnvironmentTest.test_mounting_the_working_repository_is_rejected) ... ok
test_parses_every_contract_field (tests.test_environment.ParseEnvironmentTest.test_parses_every_contract_field) ... ok
test_render_round_trips (tests.test_environment.ParseEnvironmentTest.test_render_round_trips) ... ok
test_single_command_string_is_normalized (tests.test_environment.ParseEnvironmentTest.test_single_command_string_is_normalized) ... ok
test_unexpected_indentation_is_rejected (tests.test_environment.ParseEnvironmentTest.test_unexpected_indentation_is_rejected) ... ok
test_unknown_field_is_rejected (tests.test_environment.ParseEnvironmentTest.test_unknown_field_is_rejected) ... ok
test_unterminated_flow_list_is_rejected (tests.test_environment.ParseEnvironmentTest.test_unterminated_flow_list_is_rejected) ... ok
test_the_repository_declares_a_self_hosting_e2e_gate (tests.test_environment.RepositoryEnvironmentTest.test_the_repository_declares_a_self_hosting_e2e_gate) ... ok
test_the_repository_environment_contract_is_valid (tests.test_environment.RepositoryEnvironmentTest.test_the_repository_environment_contract_is_valid) ... ok

----------------------------------------------------------------------
Ran 39 tests in 0.035s

OK

```
