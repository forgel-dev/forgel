# Task QA: Make install.sh put forgel-code on PATH for a new terminal

- Task: `20261122062911_make-install-sh-put-forgel-code-on-path-`
- Project: `forgel-1d2bf685`
- Runtime: local + environment.yaml
- Verdict: **PASS**
- Exit code: 0
- Finished: 2026-11-22T07:17:01+00:00

## Checks

- environment test: pass (exit 0) [environment project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- environment e2e: pass (exit 0) [e2e project @ /Users/okalistratov/Documents/sites/metaharness]
- After a successful install a login shell of the detected shell, started from a cleared environment, resolves forgel-code to the installed launcher without any manual PATH edit.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- An install that cannot make forgel-code resolvable exits non-zero and prints the edited file, the written block, the shell checked and the PATH that shell sees.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- Running the installer twice leaves exactly one marked block and exactly one occurrence of the launcher directory in PATH.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- Sourcing several profile files that carry the block yields exactly one occurrence of the launcher directory in PATH.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- --uninstall removes the marked block from every profile file the installer can have written, keeps every unrelated line byte-identical and creates no file.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- A zsh login shell with $SHELL unset receives the block in ~/.zshrc; a bash login shell with an existing ~/.bash_profile receives it there; a bash login shell with no bash startup file gets ~/.bash_profile created; an unrecognised shell receives it in ~/.profile with a warning naming that file.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- tests/test_install.py passes with the new cases, and the full repository test suite passes with no existing installer test weakened.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The full repository test suite passes.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- Installation through a shell reading install.sh from stdin still works and the script never consumes stdin.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The script is POSIX sh and parses under dash.: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- The README install-section guards still hold (one install command, no alternative main path, one update and one uninstall line).: pass (exit 0) [task code @ /Users/okalistratov/Documents/sites/code]
- No existing installer test was weakened or deleted, only adapted to the guarded block and the new stderr warning.: review
- README.md describes the behaviour the installer now implements and no step the installer no longer needs.: review

## Output

```
$ python -m unittest discover -s tests
# cwd: /Users/okalistratov/Documents/sites/metaharness
[agent] 20261122071249_inspect-and-finish: context handoff to session 2 (~5829/3072 tokens)
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
[github] demo-37504776: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
...................................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
........error: say needs text: --text "..." or a trailing argument
.....................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 690 tests in 109.423s

OK
$ env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
# cwd: /Users/okalistratov/Documents/sites/metaharness
=== SELF-HOSTING E2E ===
PASS a milestone was planned [1]
PASS the daemon ran the task [['selfhost-876fbb62']]
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
PASS the client reads the project list [{"command": "projects", "project": null, "ok": true, "result": {"ok": true, "kind": "projects", "text": "Projects: 1\n  client-e2e-3ba8cc06  client e2e\n    gen 1  adopted", "error": "", "session": "local", "projects": [{"id": "client-e2e-3ba8cc06", "name": "client e2e", "generation": 1, "state": "adopted", "selected": false}]}}
]
PASS the client selects the project [{"command": "use", "project": "client-e2e-3ba8cc06", "ok": true, "result": {"ok": true, "kind": "use", "text": "Selected client e2e (client-e2e-3ba8cc06) for session local.", "error": "", "session": "local", "project": {"id": "client-e2e-3ba8cc06", "name": "client e2e"}}}
]
PASS status carries the selected project [{"command": "status", "project": "client-e2e-3ba8cc06", "ok": true, "result": {"ok": true, "kind": "status", "text": "client-e2e-3ba8cc06: adopted (generation 1, checkpoint none)", "error": "", "project": {"id": "client-e2e-3ba8cc06", "name": "client e2e", "layout": "container", "recipe": null, "generation": 1, "checkpoint": "none", "state": "adopted", "task": null, "staging": null, "approvals": {"staging": null, "production": null}, "reconciliation": "none", "proposals": 0, "events": []}}}
]
PASS the engine session points to the project [{"command": "session", "project": "client-e2e-3ba8cc06", "ok": true, "result": {"ok": true, "kind": "session", "text": "Session local selects client e2e (client-e2e-3ba8cc06).", "error": "", "session": "local", "project": {"id": "client-e2e-3ba8cc06", "name": "client e2e"}}}
]
PASS say reaches the engine through --text [{"command": "say", "project": "client-e2e-3ba8cc06", "ok": true, "result": {"ok": true, "kind": "answer", "text": "Integration answer.", "error": ""}}
]
PASS the engine receives --project on status [status --project client-e2e-3ba8cc06 --json]
PASS say sends --text and --project [say --text hello integration --project client-e2e-3ba8cc06 --json]
PASS client e2e is green
$ python -m pytest -q tests/test_install.py -k login_shell_resolves
# cwd: /Users/okalistratov/Documents/sites/code
.                                                                        [100%]
1 passed, 35 deselected in 1.55s
$ python -m pytest -q tests/test_install.py -k failed_verification
# cwd: /Users/okalistratov/Documents/sites/code
.                                                                        [100%]
1 passed, 35 deselected in 1.45s
$ python -m pytest -q tests/test_install.py -k repeated_install
# cwd: /Users/okalistratov/Documents/sites/code
.                                                                        [100%]
1 passed, 35 deselected in 2.72s
$ python -m pytest -q tests/test_install.py -k guard
# cwd: /Users/okalistratov/Documents/sites/code
.                                                                        [100%]
1 passed, 35 deselected in 1.54s
$ python -m pytest -q tests/test_install.py -k uninstall
# cwd: /Users/okalistratov/Documents/sites/code
............                                                             [100%]
12 passed, 24 deselected in 9.40s
$ python -m pytest -q tests/test_install.py -k 'zsh or bash_profile or unknown_shell'
# cwd: /Users/okalistratov/Documents/sites/code
....                                                                     [100%]
4 passed, 32 deselected in 6.68s
$ python -m pytest -q tests/test_install.py
# cwd: /Users/okalistratov/Documents/sites/code
....................................                                     [100%]
36 passed in 44.66s
$ python -m pytest -q
# cwd: /Users/okalistratov/Documents/sites/code
...................................................... [ 29%]
................................................. [ 55%]
........................................................................ [ 95%]
.........                                        [100%]
184 passed, 137 subtests passed in 80.88s (0:01:20)
$ python -m pytest -q tests/test_install.py -k 'piped or stdin'
# cwd: /Users/okalistratov/Documents/sites/code
.                                                                        [100%]
1 passed, 35 deselected in 1.71s
$ sh -n install.sh
# cwd: /Users/okalistratov/Documents/sites/code
$ python -m pytest -q tests/test_readme_install.py
# cwd: /Users/okalistratov/Documents/sites/code
..........................                                               [100%]
26 passed in 0.04s

```
