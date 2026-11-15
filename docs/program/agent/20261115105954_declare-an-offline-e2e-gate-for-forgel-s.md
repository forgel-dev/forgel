# Agent Run: Declare an offline e2e gate for Forgel's own self-hosting pipeline

- Task: `20261115105954_declare-an-offline-e2e-gate-for-forgel-s`
- Status: `done`
- Repository: `main`
- Steps: 84
- Finished: 2026-11-15T14:29:20+00:00

## Requirements

- Add an e2e entry to environment.yaml with a command list that runs an offline end-to-end smoke of Forgel on itself: adopt a local fixture repository, plan a milestone with the scripted model, run one task through coding agent, task QA and review, and stop at the staging approval gate.
- The self-hosting e2e must run with FORGEL_MODEL_MODE=script, must not touch the network, Docker or cloud resources, and must finish within a couple of minutes.
- Add tests/e2e/ self-hosting driver (or extend the existing one) that the environment.yaml e2e command invokes and that exits non-zero on a red gate.
- Extend tests/test_environment.py to assert that environment.yaml declares both test and e2e and that the e2e command parses into a non-empty argument list.

## Acceptance Criteria

- The environment test passes with an e2e declaration.
- The self-hosting e2e command exits 0 in the repository sandbox, asserted by the suite run that invokes it.
- The e2e run stops at the staging approval gate and never reaches done without an approval, asserted by the driver.

## Constraints

- No external services, cloud resources or network calls.
- Deterministic output; clean up temporary directories.
- Do not weaken existing tests; keep the suite green.

## Assumptions

- The task's 'staging approval gate' maps to the human acceptance gate for the self-hosting run: the fixture is adopted in place as a brownfield linked project, which has no orchestrator staging descriptor, so the driver parks the task in `review` with a pending acceptance record (`task_accept="human"`) and asserts the project never reaches `done`.
- The driver takes the model mode from the environment because that is exactly what the declared command sets with `env FORGEL_MODEL_MODE=script`, and it fails red when the variable is not `script`.
- The driver keeps `peak_policy="always"` (set in Settings and also patched into the fixture forge.toml) so the offline gate is deterministic and never defers for DeepSeek pricing.
- The scripted responses are a small ordered queue (plan, one write_file, done, review pass) rather than the blog scenario, so the smoke is fast and exercises coding agent, QA and review in one pass.
- The environment.yaml test also asserts the scripted mode and driver path so the declaration cannot silently drift from the requirement.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 84
- Estimated input tokens (all calls): 10139850
- Provider input/output tokens: 10638574 / 385269
- Estimated prompt at the end: 201113 tokens
- State: not needed

## Summary

Declared an offline self-hosting e2e gate for Forgel itself.

- environment.yaml: added `e2e: ["env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py"]` (test entry unchanged) and documented the gate in the header comment.
- tests/e2e/run_self_hosting_e2e.py (new driver): creates a temporary home plus a local fixture git repository, adopts it in place, plans a milestone with the scripted model (one plan response), then runs one task through the coding agent, task QA and task review via the daemon. It asserts: script model mode is set, the task stopped at the gate in `review`, QA passed, review passed, the acceptance record is `pending`, and the project never reached `done`. It exits 1 on any red gate (and if the driver crashes) and 0 only when green. It uses no network/Docker/cloud, keeps the peak policy at `always` for determinism, and removes the temporary home and fixture in a `finally` block. The gate runs in ~1s.
- tests/test_e2e.py: added `SelfHostingE2ETest` which loads the repository environment contract, resolves the declared e2e command through `command_argv`, runs it from the repository root, and asserts exit 0 with the green marker and no FAIL lines. Existing pipeline tests are untouched.
- tests/test_environment.py: extended `RepositoryEnvironmentTest` with an assertion that environment.yaml declares both `test` and `e2e`, that the e2e command parses into a non-empty argv, that it sets `FORGEL_MODEL_MODE=script`, and that it invokes the self-hosting driver. All existing tests kept intact.
- tests/e2e/README.md: documented the self-hosting gate alongside the existing blog harness.

Tested with the final command `python -m unittest discover -s tests`: 446 tests pass. The declared gate was also run directly (exit 0, all gates PASS) and with `FORGEL_MODEL_MODE=auto` to confirm it fails red (exit 1).

## Files Changed

- `environment.yaml`
- `tests/e2e/README.md`
- `tests/e2e/run_self_hosting_e2e.py`
- `tests/test_e2e.py`
- `tests/test_environment.py`

## Commands

- `["python", "-c", "import os,runpy,sys;os.environ['FORGEL_MODEL_MODE']='script';sys.path[:0]=['src','.'];runpy.run_path('tests/e2e/run_self_hosting_e2e.py',run_name='__main__')"]` → exit 0
- `["python", "-m", "unittest", "tests.test_environment", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-c", "import os,runpy,sys;os.environ['FORGEL_MODEL_MODE']='auto';sys.path[:0]=['src','.'];runpy.run_path('tests/e2e/run_self_hosting_e2e.py',run_name='__main__')"]` → exit 1
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "tests.test_e2e.SelfHostingE2ETest", "-v"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261115142834_inspect-and-finish: context handoff to session 2 (~4783/3072 tokens)
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
Ran 446 tests in 54.217s

OK

```

## Actions

- read_file: environment.yaml
- read_file: src/forgel/environment.py
- read_file: tests/test_environment.py
- list_files
- read_file: tests/e2e/run_blog_e2e.py
- read_file: tests/e2e/blog_actions.py
- read_file: tests/test_e2e.py
- read_file: src/forgel/orchestrator.py
- read_file: docs/program/adoption.md
- read_file: src/forgel/daemon.py
- read_file: src/forgel/planner.py
- read_file: src/forgel/model.py
- read_file: src/forgel/adopt.py
- list_files
- read_file: src/forgel/task_qa.py
- read_file: src/forgel/task_review.py
- read_file: src/forgel/approvals.py
- read_file: src/forgel/state.py
- read_file: src/forgel/layout.py
- read_file: src/forgel/config.py
- read_file: docs/program/tasks/20261115105954_declare-an-offline-e2e-gate-for-forgel-s.json
- read_file: src/forgel/ledger.py
- read_file: src/forgel/templates/hello-web/environment.yaml
- read_file: src/forgel/tasks.py
- read_file: src/forgel/git_ops.py
- read_file: src/forgel/program_manifest.py
- read_file: src/forgel/coding_agent.py
- read_file: src/forgel/cli.py
- read_file: src/forgel/sync.py
- read_file: src/forgel/coding_agent.py
- read_file: tests/test_task_qa.py
- read_file: src/forgel/providers/github_auth.py
- read_file: src/forgel/complexity.py
- read_file: src/forgel/project_config.py
- read_file: src/forgel/peak.py
- read_file: src/forgel/secrets.py
- read_file: src/forgel/projects.py
- read_file: docs/program/plans/20261115105954_m1-oss-django-drf-react-spa-postgres-s3-.md
- read_file: src/forgel/templates/hello-web/e2e/check.py
- read_file: tests/e2e/README.md
- read_file: src/forgel/coding_agent.py
- list_files
- write_file: environment.yaml
- read_file: src/forgel/sandbox.py
- read_file: src/forgel/model_profiles.py
- write_file: tests/e2e/run_self_hosting_e2e.py
- write_file: tests/test_environment.py
- run: ['env', 'FORGEL_MODEL_MODE=script', 'PYTHONPATH=src', 'python', 'tests/e2e/run_self_hosting_e2e.py']
- run: ['python', '-c', "import os,runpy,sys;os.environ['FORGEL_MODEL_MODE']='script';sys.path[:0]=['src','.'];runpy.run_path('tests/e2e/run_self_hosting_e2e.py',run_name='__main__')"]
- run: ['python', '-m', 'unittest', 'tests.test_environment', '-v']
- write_file: tests/test_e2e.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: tests/e2e/run_self_hosting_e2e.py
- run: ['python', '-c', "import os,runpy,sys;os.environ['FORGEL_MODEL_MODE']='auto';sys.path[:0]=['src','.'];runpy.run_path('tests/e2e/run_self_hosting_e2e.py',run_name='__main__')"]
- write_file: tests/e2e/README.md
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['python', '-m', 'unittest', 'tests.test_e2e.SelfHostingE2ETest', '-v']
