# Task QA: Release audit: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block

- Task: `20261122034544_release-audit-uninstall-no-longer-honors`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-22T03:54:49+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- AC1: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC2: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC3: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC4: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC5: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- Shell syntax of the edited script: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- AC6: review
- AC7: review

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261122035207_inspect-and-finish: context handoff to session 2 (~5826/3072 tokens)
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
[github] demo-3e2c3932: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
..................................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
...............................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 683 tests in 105.088s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-04a0b3f8']]
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
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-ddc8a786  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-ddc8a786", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-ddc8a786", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-ddc8a786) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-ddc8a786", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-ddc8a786", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-ddc8a786: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-ddc8a786", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-ddc8a786", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-ddc8a786).", "error": "", "session": "local", "project": {"id": "client-e2e-ddc8a786", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-ddc8a786", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-ddc8a786 --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-ddc8a786 --json]
PASS client e2e is green
$ sh -c 'set -e; d=$(mktemp -d); trap '"'"'rm -rf "$d"'"'"' EXIT; mkdir -p "$d/home"; p="$d/home/custom_profile"; printf '"'"'# keep-before\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n# keep-after\n'"'"' "$d" > "$p"; HOME="$d/home" FORGEL_CODE_PROFILE="$p" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$p")" = "$(printf '"'"'# keep-before\n# keep-after'"'"')"; ! grep -q '"'"'forgel-code >>>'"'"' "$p"'
# cwd: /Users/okalistratov/Documents/sites/code
Removed the PATH block from /var/folders/2g/9_qkdxhs6hx0fm8bm1wtlshr0000gq/T/tmp.Rm3c0M9hcJ/home/custom_profile
Forgel Code is uninstalled.
$ sh -c 'set -e; d=$(mktemp -d); trap '"'"'rm -rf "$d"'"'"' EXIT; mkdir -p "$d/home"; printf '"'"'# keep\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n'"'"' "$d" > "$d/home/.profile"; HOME="$d/home" SHELL=/bin/sh FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$d/home/.profile")" = "# keep"'
# cwd: /Users/okalistratov/Documents/sites/code
Removed the PATH block from /var/folders/2g/9_qkdxhs6hx0fm8bm1wtlshr0000gq/T/tmp.uL0YbrV894/home/.profile
Forgel Code is uninstalled.
$ sh -c 'set -e; d=$(mktemp -d); trap '"'"'rm -rf "$d"'"'"' EXIT; mkdir -p "$d/home"; printf '"'"'no markers here\n'"'"' > "$d/home/plain_profile"; HOME="$d/home" FORGEL_CODE_PROFILE="$d/home/absent_profile" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test ! -e "$d/home/absent_profile"; test "$(cat "$d/home/plain_profile")" = "no markers here"'
# cwd: /Users/okalistratov/Documents/sites/code
Forgel Code is uninstalled.
$ sh -c 'set -e; d=$(mktemp -d); trap '"'"'rm -rf "$d"'"'"' EXIT; mkdir -p "$d/home"; printf '"'"'# keep\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n# tail\n'"'"' "$d" > "$d/home/.profile"; HOME="$d/home" SHELL=/bin/sh FORGEL_CODE_PROFILE="$d/home/.profile" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$d/home/.profile")" = "$(printf '"'"'# keep\n# tail'"'"')"'
# cwd: /Users/okalistratov/Documents/sites/code
Removed the PATH block from /var/folders/2g/9_qkdxhs6hx0fm8bm1wtlshr0000gq/T/tmp.xk8CPpN7Iz/home/.profile
Forgel Code is uninstalled.
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/code
..................................................................................................................................................................................
----------------------------------------------------------------------
Ran 178 tests in 68.112s

OK
$ sh -n install.sh
# cwd: /Users/okalistratov/Documents/sites/code

```
