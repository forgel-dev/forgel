# Task QA: Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw

- Task: `20261124003849_release-audit-the-session-keeps-unredact`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-24T04:51:16+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- When the engine returns an answer whose text contains key material, nothing the client retains for the session contains that value in readable form.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- An answer or error without key material is retained and shown exactly as before.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261124044503_inspect-and-finish: context handoff to session 2 (~6216/3072 tokens)
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
[github] demo-3d93260a: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
..............................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
...........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 755 tests in 179.958s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-6e4969b4']]
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
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-f9bb59ba  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-f9bb59ba", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-f9bb59ba", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-f9bb59ba) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-f9bb59ba", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-f9bb59ba", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-f9bb59ba: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-f9bb59ba", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-f9bb59ba", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-f9bb59ba).", "error": "", "session": "local", "project": {"id": "client-e2e-f9bb59ba", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-f9bb59ba", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-f9bb59ba --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-f9bb59ba --json]
PASS client e2e is green
$ python -m pytest -q
# cwd: /Users/okalistratov/Documents/sites/code
.............................................................................................. [ 29%]
........................................................................ [ 52%]
.......................................................................................... [ 81%]
................................................... [ 97%]
.......                                          [100%]
314 passed, 293 subtests passed in 206.27s (0:03:26)
$ python -m pytest tests/test_redact.py -q
# cwd: /Users/okalistratov/Documents/sites/code
..................................                  [100%]
34 passed, 93 subtests passed in 3.86s

```
