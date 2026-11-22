# Task QA: Fix install.sh so a new terminal finds forgel-code on PATH

- Task: `20261122025705_fix-install-sh-so-a-new-terminal-finds-f`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-22T03:39:41+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- With SHELL unset and a zsh login shell the block lands in $HOME/.zshrc and a fresh `env -i` zsh resolves forgel-code to the installed launcher.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- `sh -n install.sh` exits 0.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The full test suite passes.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261122033650_inspect-and-finish: context handoff to session 2 (~5826/3072 tokens)
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
[github] demo-199aea39: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
..................................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
...............................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 683 tests in 108.130s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-9ba30ad7']]
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
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-58f42b73  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-58f42b73", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-58f42b73", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-58f42b73) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-58f42b73", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-58f42b73", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-58f42b73: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-58f42b73", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-58f42b73", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-58f42b73).", "error": "", "session": "local", "project": {"id": "client-e2e-58f42b73", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-58f42b73", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-58f42b73 --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-58f42b73 --json]
PASS client e2e is green
$ python -m unittest tests.test_install -v
# cwd: /Users/okalistratov/Documents/sites/code
test_legacy_opt_out_name_is_honoured_too (tests.test_install.InstallerOptOutTest.test_legacy_opt_out_name_is_honoured_too) ... ok
test_opt_out_leaves_the_profile_untouched (tests.test_install.InstallerOptOutTest.test_opt_out_leaves_the_profile_untouched) ... ok
test_opt_out_writes_nothing_outside_the_target_directories (tests.test_install.InstallerOptOutTest.test_opt_out_writes_nothing_outside_the_target_directories) ... ok
test_bash_creates_a_bash_profile_when_none_exists (tests.test_install.InstallerShellDetectionTest.test_bash_creates_a_bash_profile_when_none_exists) ... ok
test_bash_uses_an_existing_bash_profile (tests.test_install.InstallerShellDetectionTest.test_bash_uses_an_existing_bash_profile) ... ok
test_unset_shell_puts_the_block_in_zshrc (tests.test_install.InstallerShellDetectionTest.test_unset_shell_puts_the_block_in_zshrc) ... ok
test_install_creates_the_launcher_in_the_bin_directory (tests.test_install.InstallerTest.test_install_creates_the_launcher_in_the_bin_directory) ... ok
test_install_exits_zero_and_prints_the_version (tests.test_install.InstallerTest.test_install_exits_zero_and_prints_the_version) ... ok
test_install_reports_the_shell_profile_and_the_fresh_check (tests.test_install.InstallerTest.test_install_reports_the_shell_profile_and_the_fresh_check) ... ok
test_launcher_prints_the_installed_version (tests.test_install.InstallerTest.test_launcher_prints_the_installed_version) ... ok
test_missing_interpreter_fails_with_a_message (tests.test_install.InstallerTest.test_missing_interpreter_fails_with_a_message) ... ok
test_piped_install_does_not_read_the_script_from_stdin (tests.test_install.InstallerTest.test_piped_install_does_not_read_the_script_from_stdin)
The documented ``curl ... | sh`` shape, with the script on stdin. ... ok
test_profile_gets_one_marked_path_block (tests.test_install.InstallerTest.test_profile_gets_one_marked_path_block) ... ok
test_profile_the_login_shell_ignores_fails_verification (tests.test_install.InstallerTest.test_profile_the_login_shell_ignores_fails_verification) ... ok
test_script_is_executable_and_parses_with_sh (tests.test_install.InstallerTest.test_script_is_executable_and_parses_with_sh) ... ok
test_second_run_is_idempotent (tests.test_install.InstallerTest.test_second_run_is_idempotent) ... ok
test_uninstall_clears_every_candidate_profile (tests.test_install.InstallerUninstallTest.test_uninstall_clears_every_candidate_profile) ... ok
test_uninstall_keeps_the_rest_of_the_profile (tests.test_install.InstallerUninstallTest.test_uninstall_keeps_the_rest_of_the_profile) ... ok
test_uninstall_removes_everything (tests.test_install.InstallerUninstallTest.test_uninstall_removes_everything) ... ok
test_console_script_prints_the_installed_version (tests.test_install.PlainPipInstallTest.test_console_script_prints_the_installed_version) ... ok
test_install_exits_zero (tests.test_install.PlainPipInstallTest.test_install_exits_zero) ... ok
test_install_needs_no_network_and_no_build_requirements (tests.test_install.PlainPipInstallTest.test_install_needs_no_network_and_no_build_requirements) ... ok
test_module_entry_point_prints_the_installed_version (tests.test_install.PlainPipInstallTest.test_module_entry_point_prints_the_installed_version) ... ok

----------------------------------------------------------------------
Ran 23 tests in 25.242s

OK
$ sh -n install.sh
# cwd: /Users/okalistratov/Documents/sites/code
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/code
...........................................................................................................................................................................
----------------------------------------------------------------------
Ran 171 tests in 54.952s

OK

```
