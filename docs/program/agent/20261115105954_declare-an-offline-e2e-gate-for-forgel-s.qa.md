# Task QA: Declare an offline e2e gate for Forgel's own self-hosting pipeline

- Task: `20261115105954_declare-an-offline-e2e-gate-for-forgel-s`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-15T14:30:25+00:00

## Checks

- environment test: pass (exit 0)
- environment e2e: pass (exit 0)
- environment.yaml declares test and e2e and the e2e command parses: pass (exit 0)
- Self-hosting e2e driver exits 0 and parks at the staging gate: pass (exit 0)

## Output

```
$ python -m unittest discover -s tests
[agent] 20261115142929_inspect-and-finish: context handoff to session 2 (~4785/3072 tokens)
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
..............................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 446 tests in 54.599s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-7ed59213']]
PASS FORGEL_MODEL_MODE=script [script]
PASS the task stopped at the staging approval gate [review]
PASS task QA passed [pass]
PASS task review passed [pass]
PASS acceptance is pending a human decision [pending]
PASS the project never reached done [None]
PASS self-hosting gate is green and parked for human approval
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
Ran 39 tests in 0.023s

OK
$ env PYTHONPATH=src python -m unittest tests.test_e2e -v
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
test_pipeline_reaches_done (tests.test_e2e.EndToEndTest.test_pipeline_reaches_done) ... ok
test_resume_is_idempotent (tests.test_e2e.EndToEndTest.test_resume_is_idempotent) ... ok
test_rollback_restores_the_external_change (tests.test_e2e.EndToEndTest.test_rollback_restores_the_external_change) ... ok
test_sync_starts_new_generation_after_external_edit (tests.test_e2e.EndToEndTest.test_sync_starts_new_generation_after_external_edit) ... ok
test_the_declared_e2e_command_exits_zero (tests.test_e2e.SelfHostingE2ETest.test_the_declared_e2e_command_exits_zero) ... ok

----------------------------------------------------------------------
Ran 5 tests in 8.101s

OK

```
