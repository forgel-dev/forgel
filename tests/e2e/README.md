# Forgel E2E

Three end-to-end drivers live here:

- `run_self_hosting_e2e.py` — the offline self-hosting gate declared in
  `environment.yaml`.
- `run_client_e2e.py` — the cross-repository engine + Forgel Code gate declared
  in `environment.yaml`.
- `run_blog_e2e.py` — a manual end-to-end test of the Forgel harness.

## Self-hosting gate

`environment.yaml` declares `test` and two `e2e` commands. The first is the
self-hosting smoke:

```bash
env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_self_hosting_e2e.py
```

The driver is an offline smoke of Forgel on itself:

1. adopt a local fixture repository (a tiny git repository made in a
   temporary directory);
2. plan a milestone with the scripted model (`FORGEL_MODEL_MODE=script`);
3. run one task through the coding agent, task QA and task review;
4. stop at the approval gate.

The run never touches the network, Docker or cloud resources. The product
default is automatic acceptance (`FORGEL_TASK_ACCEPT=auto`); the driver opts
into `FORGEL_TASK_ACCEPT=human` to exercise the task acceptance gate: the task
parks in `review` status with a pending acceptance record, and the driver
asserts the project never reaches `done` on its own. The temporary home and
fixture repository are removed on exit.

The driver exits non-zero when any gate is red (missing scripted model, a task
that did not stop at the gate, QA or review failure, or a pipeline that ran
through to `done`). `tests/test_e2e.py` invokes every declared `e2e` command
and asserts exit code 0, so the suite covers both gates.

## Client gate

The second `e2e` command is the cross-repository integration gate:

```bash
env FORGEL_MODEL_MODE=script PYTHONPATH=src python tests/e2e/run_client_e2e.py
```

It runs the **real engine** from this repository and the **real client** from
the `code` repository, each as a separate process, over the machine-readable
JSON contract. The scenario:

1. create a temporary project and home;
2. `forgel-code projects` sees the project;
3. `forgel-code use <id>` selects it;
4. `forgel-code status` and `forgel-code session` pass `--project <id>` to the
   engine and get the project back;
5. `forgel-code say "..."` sends the phrase in `--text`, the engine answers
   with the scripted model, and the client parses the answer.

The client repository is located through `FORGEL_REPO_CODE`. The environment
contract declares `mounts: [code]`, so the QA runner points this variable at the
real sibling path locally and at `/code` inside the sandbox. Without the
variable the driver falls back to `../code` next to this repository. No
network, Docker or provider model is used.

This gate caught a real contract defect on its first run: the client sent the
phrase as a positional argument to `forgel say`, but the engine reserves that
positional for the project key, so the phrase was consumed and the call failed
with `say needs text`. The client now sends `--text`; its unit tests alone could
not see this because they run against a fake engine.

## Where the e2e lives

The program e2e suite lives in the project's main repository — the one the
project started from. For a project that was multi-repo from the start, it
lives in the control repository. It is not duplicated into every repository;
sibling repositories are exposed to it through `environment.yaml`'s `mounts`
(`FORGEL_REPO_<ID>` locally and `/<id>` in the sandbox).

A program e2e is required when repositories interact through a `depends_on`
edge, when the project has a frontend/acceptance or mobile repository, or when
the environment mounts siblings. A database or cache covered by the unit-test
framework does not by itself require a program e2e; a browser, a mobile
simulator/emulator or an external tool without a standard test harness belongs
in the task specification's real-interface command check. The planner refuses
to plan such a project without an e2e command; QA fails a task whose project
needs one and does not declare it. A red e2e is returned to the coding agent
with the command, workdir and output.

Heavy tools are declared in `e2e_requires` (`ios-simulator`,
`android-emulator`, `mobile-simulator`, `docker`). The QA runner probes them on
the current machine; when one is absent, the e2e step is recorded as `skipped`
with an explanation and installation instructions instead of failing the task.
A mobile simulator is deferred, never a hard blocker, and the e2e can be added
later once the tool is installed. A browser is not probed: it is installable
almost everywhere and a missing browser is reported by the e2e command itself.

## Blog harness

A manual end-to-end test of the Forgel harness: a local daemon receives a task,
a coding agent builds a minimal blog platform from scratch, and an external
validator checks the result.

This is the foundation for testing Forgel while the development process moves
onto Forgel itself. It is deliberately small, local and budget-gated. It can
later be moved to a separate repository or wired into a pre-release process.

**Not part of `make test`.** Run it only on explicit instruction. `api` mode
spends provider budget.

### Scope

Included:

- a minimal blog platform written from scratch in a local git repository;
- a local daemon and a local SQLite database;
- Python standard library only, no third-party dependencies;
- deterministic external acceptance checks.

Excluded by design:

- any third-party API integration; everything works and is tested locally;
- an external repository or GitHub; only local `.git`;
- deployment; everything runs locally;
- Telegram; interaction is through the CLI.

### Run

Deterministic harness check (free; no model calls):

```bash
make e2e-blog
# or
python tests/e2e/run_blog_e2e.py --mode script --strict
```

Bridge mode: the daemon's model calls are served by an external driver, which
can be a subagent CLI or another harness. The command reads a prompt on stdin
and prints the answer. No provider budget is spent inside Forgel.

```bash
python tests/e2e/run_blog_e2e.py --mode bridge --strict \
  --driver-command "your-agent-cli --print"
```

The bridge protocol is files: `<id>.request.json` in
`$FORGEL_HOME/model-bridge`, answered with `<id>.response.json`
(`{"content": "..."}`), a raw `<id>.response.txt`, or `<id>.error.json`.
`subagent_driver.py` implements the watching loop. `scripted_responder.py` is a
bridge test double, not a model. A manual run can start the e2e with
`--home <empty-dir> --mode bridge` and write `response.txt` files itself (for
example, an external subagent can write one per request).

Sandbox mode: `--sandbox docker` runs the agent's commands in a per-project
container on the Docker daemon behind `DOCKER_HOST` (a remote engine or the
output of `deploy/compose.yaml --profile sandbox`). The project gets only its
own repository, `network=none` by default, and the image from its
`environment.yaml`. The local mode stays the default and needs no daemon.

```bash
DOCKER_HOST=tcp://127.0.0.1:2375 \
python tests/e2e/run_blog_e2e.py --mode script --strict --sandbox docker
```

API mode: a real OpenAI-compatible model. Requires a key and explicit `--yes`:

```bash
export FORGEL_MODEL_API_KEY=...
python tests/e2e/run_blog_e2e.py --mode api --strict --yes
```

The script prints the artifacts directory; `--clean` removes it.

### The task

The generated task is stored in the project's control repository under
`docs/program/tasks/`. It asks for:

- `python app.py --host 127.0.0.1 --port <port>` starts the app; the SQLite
  path comes from `BLOG_DB`;
- `GET /health` returns `{"status":"ok"}`;
- `GET /` shows "Mini Blog", a create form and the post list;
- `POST /posts` stores the form fields `title` and `body` and redirects;
- `GET /posts/<id>` shows the post; unknown ids return 404;
- posts persist across restarts;
- tests under `tests/` pass with `python -m unittest discover -s tests`;
- `README.md` documents run and test commands.

Constraints: standard library only, no external calls, no deployment, no
Telegram, no unrequested features, no secrets or database files in git.

The task also fixes the **run contract** (the command, port and form fields).
Without that contract the acceptance would depend on an implementation guess.
Everything else — file layout, HTML, SQL schema — is the agent's decision.

### Acceptance

Two independent groups, reported separately.

#### Product (depends on the model)

`validate_blog.py` is an external, deterministic validator. It starts the app,
checks the HTTP behaviour, restarts it for persistence, runs the unit tests and
scans for third-party imports, external URLs and secret files.

An independent external reviewer can be run after the validator:

```bash
python tests/e2e/run_blog_e2e.py --mode script --strict \
  --review-command "your-agent-cli --print"
```

The reviewer receives the task and repository path, must not modify the code,
and checks adherence to the explicit requirements plus safety and scope.

#### Harness (independent of model quality)

These must hold even when the model produces bad code:

- the daemon starts and exits cleanly;
- the pending task is picked up and reaches `done` or `failed`;
- the agent report is written;
- a committed change exists when the task is `done`, and the worktree is clean;
- the task result carries a summary;
- a failed model run is reported as a product failure, not a harness failure.

A harness failure means the orchestration, tool loop, ledger, git or reporting
broke. A product failure with a passing harness is a model/implementation
quality result.

Exit codes: `0` harness passed (and product passed in `--strict`), `1` harness
failed, `2` product failed in `--strict`, `3` configuration error.
