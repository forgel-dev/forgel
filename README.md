# Forgel

Open-source autonomous software studio. Describe a product; get a working web app with specs, independent QA, and a deploy — on your infrastructure, with your model key.

**Status:** pre-alpha. The plan is in [PLAN.md](PLAN.md).

## Try the M0 Skeleton

Requires Python 3.11+.

```bash
make demo
```

This creates `.forgel-demo/`, runs the full pipeline from brief to staging, and
prints the staging URL. Inspect the ledger and the generated artifacts:

```bash
PYTHONPATH=src python3 -m forgel list --home .forgel-demo
PYTHONPATH=src python3 -m forgel status <project-id> --home .forgel-demo
PYTHONPATH=src python3 -m forgel serve <project-id> --home .forgel-demo
```

Run the tests:

```bash
make test
```

Run the core from the Docker image:

```bash
docker compose run --rm forgel demo
```

## Edit Outside Forgel

Forgel never regenerates or overwrites external work. After editing a generated
project by hand or in another harness:

```bash
forgel sync <project-id>
forgel run <project-id>
```

`sync` records the diff in `docs/program/external-changes.md`, starts a new
ledger generation, and re-runs the affected gates from `review`.

## What it will do

- Chat interface (Telegram) → requirements → a validated recipe (stack + cloud + integrations).
- Multi-repo project: backend, frontend, infrastructure, E2E.
- Spec-driven development with clean-context roles: spec writer, developer, reviewer, QA, acceptor.
- Independent end-to-end QA and acceptance evidence — not "the agent said it works".
- Jurisdiction packs: legal constraints become default requirements and evidence — not a document attached at the end. A draft pack is usable; production carries an explicit compliance acknowledgement.
- Staging deploy; production behind human gates.
- Plugins for stacks, clouds, QA drivers, models, domain and jurisdiction packs.

## Principles

- **Own it** — your server, your model key, your code.
- **Prove it** — spec → review → independent QA → acceptance; jurisdiction evidence and an auditable trail.
- **Extend it** — plugins and a recipe registry instead of a monolith.

## Not

- Not a code generator: the output is repositories and a running staging environment.
- Not no-code: the code is yours and exportable.
- Not an agency: humans only where the law or a platform requires them.

## Compliance Disclaimer

Forgel is a software development tool, not a law firm. Jurisdiction packs are draft
guidance, may be incomplete or out of date, and are not legal advice. Forgel does not
warrant that a generated product complies with the laws of any jurisdiction. The user
is responsible for regulatory compliance; approving a production deploy confirms that
responsibility. See [PLAN.md](PLAN.md) and [jurisdiction/README.md](jurisdiction/README.md).

## License

Core: AGPL-3.0-or-later. Plugin SDK, official plugins and templates: Apache-2.0. Generated project code belongs to the user. See [LICENSE](LICENSE).

## Agent Instructions

- [AGENTS.md](AGENTS.md) — cross-harness canon.
- [FORGEL.md](FORGEL.md) — native Forgel instructions, read first.

## Contributing

Public roadmap, RFC process, DCO instead of CLA. See [PLAN.md](PLAN.md) §14.
