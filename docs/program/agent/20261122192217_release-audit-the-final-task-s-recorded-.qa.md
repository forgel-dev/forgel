# Task QA: Release audit: The final task's recorded test run shows only `timed out after 120s` and partial

- Task: `20261122192217_release-audit-the-final-task-s-recorded-`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **FAIL**
- Failure kind: `infrastructure`
- Exit code: 127
- Finished: 2026-11-23T04:13:37+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- AC1 and AC2: the full suite exits 0 and fits the 120 s bound: fail (exit 127) [task code @ /Users/okalistratov/Documents/sites/code]
- AC4: the real installer scenarios still run and pass individually: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC5: test modules remain independently runnable: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC6: the README Tests section states the runtime bound: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC7: CHANGELOG [Unreleased] records the change: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- task test command: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC3: no test method, assertion, scenario or skip was weakened: review
- AC8: measured before/after durations justify that the bound is met: review

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261123040851_inspect-and-finish: context handoff to session 2 (~6081/3072 tokens)
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
[github] GitHub API is unreachable; the branch is pushed without pull-request checks
[github] demo-aab565ec: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
..............................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
..........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 722 tests in 148.743s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-e64379db']]
PASS FORGEL_MODEL_MODE=script [script]
PASS the task stopped at the staging approval gate [review]
PASS task QA passed [pass]
PASS task review passed [pass]
PASS acceptance is pending a human decision [pending]
PASS the project never reached done [None]
PASS self-hosting gate is green and parked for human approval
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_client_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== CLIENT E2E ===
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-e2062da8  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-e2062da8", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-e2062da8", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-e2062da8) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-e2062da8", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-e2062da8", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-e2062da8: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-e2062da8", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-e2062da8", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-e2062da8).", "error": "", "session": "local", "project": {"id": "client-e2e-e2062da8", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-e2062da8", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-e2062da8 --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-e2062da8 --json]
PASS client e2e is green
$ sh -c 'timeout 120 python -m unittest discover -s tests'
# cwd: /Users/okalistratov/Documents/sites/code
timeout: не удалось выполнить команду «python»: No such file or directory
$ python -m unittest tests.test_install -v
# cwd: /Users/okalistratov/Documents/sites/code
test_remove_profile_block_is_idempotent (tests.test_install.InstallerBlockRemovalTest.test_remove_profile_block_is_idempotent) ... ok
test_remove_profile_block_preserves_orphan_end_marker (tests.test_install.InstallerBlockRemovalTest.test_remove_profile_block_preserves_orphan_end_marker) ... ok
test_remove_profile_block_removes_only_wellformed_block (tests.test_install.InstallerBlockRemovalTest.test_remove_profile_block_removes_only_wellformed_block) ... ok
test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged (tests.test_install.InstallerBlockRemovalTest.test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged) ... ok
test_check_directory_is_owner_only_and_then_removed (tests.test_install.InstallerBoundedCheckTest.test_check_directory_is_owner_only_and_then_removed)
The check writes into a private directory nobody else can read. ... ok
test_failed_check_leaves_no_temporary_entry (tests.test_install.InstallerBoundedCheckTest.test_failed_check_leaves_no_temporary_entry) ... ok
test_shell_that_ignores_the_stop_is_still_bounded (tests.test_install.InstallerBoundedCheckTest.test_shell_that_ignores_the_stop_is_still_bounded)
A shell that ignores the graceful stop is forcefully stopped in time. ... ok
test_successful_check_leaves_no_temporary_entry (tests.test_install.InstallerBoundedCheckTest.test_successful_check_leaves_no_temporary_entry) ... ok
test_install_sh_never_invokes_gnu_timeout (tests.test_install.InstallerBoundedToolsTest.test_install_sh_never_invokes_gnu_timeout) ... ok
test_install_succeeds_with_a_failing_timeout_first_on_path (tests.test_install.InstallerBoundedToolsTest.test_install_succeeds_with_a_failing_timeout_first_on_path)
A missing ``timeout`` cannot break the install: it is never called. ... ok
test_legacy_opt_out_name_is_honoured_too (tests.test_install.InstallerOptOutTest.test_legacy_opt_out_name_is_honoured_too) ... ok
test_opt_out_leaves_the_profile_untouched (tests.test_install.InstallerOptOutTest.test_opt_out_leaves_the_profile_untouched) ... ok
test_opt_out_writes_nothing_outside_the_target_directories (tests.test_install.InstallerOptOutTest.test_opt_out_writes_nothing_outside_the_target_directories) ... ok
test_install_rerun_then_uninstall_preserves_profile (tests.test_install.InstallerProfileByteStabilityTest.test_install_rerun_then_uninstall_preserves_profile)
Two installs and an uninstall keep every unrelated profile line. ... ok
test_profile_with_a_final_newline_is_byte_stable (tests.test_install.InstallerProfileByteStabilityTest.test_profile_with_a_final_newline_is_byte_stable) ... ok
test_profile_without_a_final_newline_is_byte_stable (tests.test_install.InstallerProfileByteStabilityTest.test_profile_without_a_final_newline_is_byte_stable) ... ok
test_repeated_install_does_not_accumulate_blank_lines (tests.test_install.InstallerProfileByteStabilityTest.test_repeated_install_does_not_accumulate_blank_lines) ... ok
test_override_naming_a_standard_profile_is_cleaned_once (tests.test_install.InstallerProfileOverrideUninstallTest.test_override_naming_a_standard_profile_is_cleaned_once) ... ok
test_uninstall_leaves_a_marker_free_override_profile_alone (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_leaves_a_marker_free_override_profile_alone) ... ok
test_uninstall_removes_the_block_a_failed_install_left (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_removes_the_block_a_failed_install_left) ... ok
test_uninstall_removes_the_block_from_the_override_profile (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_removes_the_block_from_the_override_profile) ... ok
test_uninstall_removes_the_block_of_an_override_that_installed (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_removes_the_block_of_an_override_that_installed) ... ok
test_uninstall_tolerates_a_missing_override_profile (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_tolerates_a_missing_override_profile) ... ok
test_uninstall_without_the_override_cleans_the_standard_profile (tests.test_install.InstallerProfileOverrideUninstallTest.test_uninstall_without_the_override_cleans_the_standard_profile) ... ok
test_bash_creates_a_bash_profile_when_none_exists (tests.test_install.InstallerShellDetectionTest.test_bash_creates_a_bash_profile_when_none_exists) ... ok
test_bash_uses_an_existing_bash_profile (tests.test_install.InstallerShellDetectionTest.test_bash_uses_an_existing_bash_profile) ... ok
test_unknown_shell_writes_profile_and_warns (tests.test_install.InstallerShellDetectionTest.test_unknown_shell_writes_profile_and_warns)
A POSIX shell outside zsh and bash gets ~/.profile plus a warning. ... ok
test_unset_shell_puts_the_block_in_zshrc (tests.test_install.InstallerShellDetectionTest.test_unset_shell_puts_the_block_in_zshrc)
Without $SHELL at all the account login shell still decides. ... ok
test_zsh_without_shell_puts_the_block_in_zshrc (tests.test_install.InstallerShellDetectionTest.test_zsh_without_shell_puts_the_block_in_zshrc) ... ok
test_failed_verification_reports_file_block_shell_and_path (tests.test_install.InstallerTest.test_failed_verification_reports_file_block_shell_and_path) ... ok
test_guard_keeps_one_entry_when_several_profiles_are_sourced (tests.test_install.InstallerTest.test_guard_keeps_one_entry_when_several_profiles_are_sourced)
Sourcing each profile that carries the block adds the entry once. ... ok
test_install_creates_the_launcher_in_the_bin_directory (tests.test_install.InstallerTest.test_install_creates_the_launcher_in_the_bin_directory) ... ok
test_install_exits_zero_and_prints_the_version (tests.test_install.InstallerTest.test_install_exits_zero_and_prints_the_version) ... ok
test_install_reports_the_shell_profile_and_the_fresh_check (tests.test_install.InstallerTest.test_install_reports_the_shell_profile_and_the_fresh_check) ... ok
test_launcher_prints_the_installed_version (tests.test_install.InstallerTest.test_launcher_prints_the_installed_version) ... ok
test_login_shell_resolves_forgel_code_after_install (tests.test_install.InstallerTest.test_login_shell_resolves_forgel_code_after_install)
A cleared, freshly started login shell finds the launcher unaided. ... ok
test_missing_interpreter_fails_with_a_message (tests.test_install.InstallerTest.test_missing_interpreter_fails_with_a_message) ... ok
test_piped_install_does_not_read_the_script_from_stdin (tests.test_install.InstallerTest.test_piped_install_does_not_read_the_script_from_stdin)
The installer leaves the rest of stdin to the shell that read it. ... ok
test_piped_install_reads_the_script_from_stdin (tests.test_install.InstallerTest.test_piped_install_reads_the_script_from_stdin)
The documented ``curl ... | sh`` shape, with the script on stdin. ... ok
test_profile_gets_one_marked_path_block (tests.test_install.InstallerTest.test_profile_gets_one_marked_path_block) ... ok
test_profile_the_login_shell_ignores_fails_verification (tests.test_install.InstallerTest.test_profile_the_login_shel
... [truncated, 32136 chars]
```
