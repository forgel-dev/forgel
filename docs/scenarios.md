# Scenario Sandbox

A scenario sandbox runs real Forgel workflows with a real model in an isolated
tree. It is a permanent part of the engine, not a one-off script.

## What It Guarantees

- A separate `FORGEL_HOME` and workspace for every run.
- A local clone of a fixture repository with **no remote**; the clone is
  checked out at the scenario snapshot.
- Repository creation and repository addition are local: a git repository in
  the sandbox workspace, never a provider repository.
- Repository publication is simulated with a bare git repository under the
  sandbox root; nothing leaves the machine.
- GitHub credentials are removed from the environment for the duration of the
  run.
- No push, no provider release, no production action.
- The real `CommandRouter`, project agent, planner, task pipeline and release
  train are used; the scenario exercises the runtime, not a mock console.

The model endpoint is the only external service a scenario may call. Use a
scripted model client or `FORGEL_MODEL_MODE=script` when the run must be fully
offline.

## Usage

```bash
forgel scenario --scenario tests/scenarios/forgel-code.json
make scenario            # the same replay, keeping the sandbox
make scenario-execute    # the replay with the daemon in the sandbox
make scenario-test       # sandbox unit tests, scripted model, no tokens
```

Scenario runs are a separate category and are executed only on explicit
request. They are **not** part of `make test`:

| Target | Model | Tokens | Purpose |
| --- | --- | --- | --- |
| `make test` | none | none | the normal unit suite |
| `make scenario-test` | scripted | none | the sandbox core: local repositories, router, recording |
| `make scenario` | configured real model | yes | the product intake/plan replay |
| `make scenario-execute` | configured real model | yes | the full replay with the daemon in the sandbox |

`make test` discovers only `tests/`; the sandbox tests live in
`sandbox_tests/` and the scenario fixture in `tests/scenarios/` is not a test
module.

A scenario file is JSON:

```json
{
  "fixture": ".",
  "snapshot": "<git commit>",
  "messages": ["first user message", "next user message"]
}
```

Options:

| Option | Effect |
| --- | --- |
| `--fixture PATH` | Git repository used as the fixture; defaults to the scenario file or `.` |
| `--snapshot SHA` | Commit checked out in the sandbox clone |
| `--message TEXT` | Add a message; may be repeated |
| `--execute` | After the messages, run the daemon in the sandbox until it idles |
| `--keep` | Keep the sandbox tree for inspection |
| `--root PATH` | Put the sandbox at a chosen directory |
| `--home PATH` | Home used only to load the local environment |

The sandbox path is printed at the start. Without `--keep`, it is removed at
the end.

## Reading a Run

The console output is the real transcript: the agent's reply, the actions it
chose, the plan reply and, with `--execute`, the daemon and release reports.
Inspect the sandbox while it is kept:

```text
<root>/home/                       # ledger, secrets, conversation
<root>/home/projects/<id>/program/ # requests, plans, specs, tasks, releases
<root>/home/projects/<id>/repos/   # the fixture clone and created repositories
```

The conversation is `program/.forgel/conversations/0.jsonl`; the release
records are under `program/docs/program/releases/`.

## Safety Rules

- Never point the sandbox at a fixture that is not a git repository.
- Never add a remote to a sandbox repository.
- Never run a scenario with a provider token in the environment; the runner
  strips the GitHub variables, but a provider-specific plugin may read other
  names.
- A scenario that needs an external service is not a sandbox scenario; use the
  e2e suite with its explicit environment contract instead.
