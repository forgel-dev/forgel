# Agent Run: Declare an offline e2e gate for Forgel's own self-hosting pipeline

- Task: `20261115105954_declare-an-offline-e2e-gate-for-forgel-s`
- Status: `failed`
- Repository: `main`
- Steps: 3
- Finished: 2026-11-15T13:47:28+00:00

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

- none

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 991808)
- Sessions: 1
- Handoffs: 0
- Model calls: 2
- Estimated input tokens (all calls): 28108
- Provider input/output tokens: 19555 / 151
- Estimated prompt at the end: 9527 tokens
- State: not needed

## Summary

model call failed: model endpoint returned an empty answer

## Files Changed

- none

## Commands

- none

## Final Test Output

```
not run
```

## Actions

- read_file: environment.yaml
