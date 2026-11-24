# Task QA: Release audit: The redactor recognizes the French password label only as the whitespace-separat

- Task: `20261124123936_release-audit-the-redactor-recognizes-th`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-24T13:04:38+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- For a message containing a hyphen-joined French password label followed by a value, the rendered output and retained session text contain the redaction placeholder instead of the value.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The spaced French password label and all other supported secret labels still redact as before.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- Quoted and bracketed joined French password labels are redacted the same way as their spaced equivalents.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The full test suite passes.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261124125830_inspect-and-finish: context handoff to session 2 (~6216/3072 tokens)
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
[github] demo-2a4c7a43: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
..............................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
...........................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 755 tests in 152.012s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-2ed5245c']]
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
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-54131948  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-54131948", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-54131948", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-54131948) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-54131948", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-54131948", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-54131948: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-54131948", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-54131948", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-54131948).", "error": "", "session": "local", "project": {"id": "client-e2e-54131948", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-54131948", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-54131948 --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-54131948 --json]
PASS client e2e is green
$ python -m pytest tests/test_redact_french_spanish.py -q
# cwd: /Users/okalistratov/Documents/sites/code
........................                                             [100%]
24 passed, 76 subtests passed in 1.88s
$ python -m pytest tests/test_redact.py tests/test_redact_french_spanish.py tests/test_localization.py -q
# cwd: /Users/okalistratov/Documents/sites/code
................................................... [ 60%]
.................................                                               [100%]
84 passed, 302 subtests passed in 27.62s
$ python -m pytest tests/test_redact_quoted_bare.py tests/test_redact_french_spanish.py -q
# cwd: /Users/okalistratov/Documents/sites/code
............................... [ 91%]
...                                                                      [100%]
34 passed, 113 subtests passed in 1.86s
$ python -m pytest -q
# cwd: /Users/okalistratov/Documents/sites/code
.............................................................................................. [ 24%]
........................................................................ [ 43%]
......................................................................... [ 63%]
.................................................................... [ 81%]
.......................................................................                               [100%]
378 passed, 600 subtests passed in 196.49s (0:03:16)

```
