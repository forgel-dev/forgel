# Task Review: Declare an offline e2e gate for Forgel's own self-hosting pipeline

- Task: `20261115105954_declare-an-offline-e2e-gate-for-forgel-s`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-15T14:30:59+00:00

## Summary

The attributed change adds a real `e2e` entry to `environment.yaml` (a single-element command list) that sets `FORGEL_MODEL_MODE=script` and runs `tests/e2e/run_self_hosting_e2e.py`, a new driver that builds a local git fixture, adopts it, plans one milestone with a `ScriptedModelClient`, runs one task through the agent, task QA and task review, and then asserts the task is parked in `review` with a pending acceptance decision, that QA and review passed, that the model mode is `script`, and that the project checkpoint never reaches `done`; it exits 1 on any red gate, a crash, or an empty check list. The driver forces `sandbox="local"`, `qa_runtime="local"`, `task_accept="human"` and `peak_policy="always"`, so no Docker, network or cloud path is taken, and it cleans up the temporary home/fixture in a `finally`. `tests/test_e2e.py` gains a test that loads the declared environment, parses the e2e command, runs it with a 240s timeout and asserts exit 0 plus the green marker, so the suite covers the gate; the environment test extension in `tests/test_environment.py` is part of the change and its focused run passed. No tests were removed or weakened. The one nuance is that for a brownfield linked project the human stop is realized as the task acceptance gate rather than an orchestrator staging descriptor; the driver documents this and still proves the pipeline cannot reach `done` without an approval.

## Requirements

- environment.yaml declares an `e2e` command list that runs an offline self-hosting smoke (adopt local fixture, plan milestone with scripted model, run one task through agent/QA/review, stop at approval gate): pass — environment.yaml: `e2e: ["env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py"]`; the driver performs adopt -> plan -> agent -> QA -> review and stops at a pending human acceptance.
- The e2e runs with FORGEL_MODEL_MODE=script, without network/Docker/cloud, and finishes within a couple of minutes: pass — Command exports FORGEL_MODEL_MODE=script and the driver asserts it is `script`; Settings use sandbox="local", qa_runtime="local", peak_policy="always" and an injected ScriptedModelClient, so no provider/Docker/network calls occur; tests/test_e2e.py bounds the run at 240s.
- Add tests/e2e self-hosting driver invoked by the environment.yaml e2e command that exits non-zero on a red gate: pass — tests/e2e/run_self_hosting_e2e.py returns 1 on a crashed run, an empty check list, or any failed check, and 0 only when every gate is green.
- Extend tests/test_environment.py to assert environment.yaml declares both test and e2e and that the e2e command parses into a non-empty argument list: pass — tests/test_environment.py is in the attributed change and the focused environment run passed (exit 0); tests/test_e2e.py additionally loads the environment, asserts `environment.e2e` is non-empty, and parses the first command via `command_argv`, requiring a non-empty argv.
- Acceptance: the self-hosting e2e command exits 0 in the repository sandbox, asserted by the suite run that invokes it: pass — The new SelfHostingE2ETest loads the declared e2e command, executes it at the repo root and asserts returncode 0 plus the 'self-hosting gate is green' marker.
- Acceptance: the e2e run stops at the staging approval gate and never reaches done without an approval, asserted by the driver: pass — The driver asserts status == 'review', qa/review pass, acceptance.status == 'pending', and ledger checkpoint != 'done'; for a brownfield linked project the hard human stop is the task acceptance gate, which is documented in the driver and README.
- Constraints: deterministic output, temporary directories cleaned up, no weakened or deleted tests, suite kept green: pass — Fixed fixture content and commit identity, peak_policy forced to 'always', temp home removed via shutil.rmtree in a finally; no test removals were detected and existing tests were only extended.

## Blocking

- none

## Test Removals

- none


