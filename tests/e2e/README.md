# Forgel Blog E2E

A manual end-to-end test of the Forgel harness: a local daemon receives a task,
a coding agent builds a minimal blog platform from scratch, and an external
validator checks the result.

This is the foundation for testing Forgel while the development process moves
onto Forgel itself. It is deliberately small, local and budget-gated. It can
later be moved to a separate repository or wired into a pre-release process.

**Not part of `make test`.** Run it only on explicit instruction. `api` mode
spends provider budget.

## Scope

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

## Run

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
example, a Claude Code subagent can write one per request).

API mode: a real OpenAI-compatible model. Requires a key and explicit `--yes`:

```bash
export FORGEL_MODEL_API_KEY=...
python tests/e2e/run_blog_e2e.py --mode api --strict --yes
```

The script prints the artifacts directory; `--clean` removes it.

## The task

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

## Acceptance

Two independent groups, reported separately.

### Product (depends on the model)

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

### Harness (independent of model quality)

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
