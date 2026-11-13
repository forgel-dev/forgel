# Contributing to Forgel

Thanks for your interest. Forgel is pre-alpha; read [PLAN.md](PLAN.md) before making a significant change.

## Ways to Contribute

- **Bug reports** — a minimal reproduction and the expected behavior.
- **RFCs** — for anything that changes the architecture, the plugin contract, the registry format, or the process. Open an issue with the `rfc` label before writing code.
- **Code** — bug fixes, tests, documentation, CLI ergonomics.
- **Plugins and recipes** — see below.
- **Docs** — examples, tutorials, corrections.

## Language

All public artifacts are in English (D-025): issues, pull requests, commit messages, documentation, and code comments. Code identifiers and file names are English.

## Licensing and DCO

- The core is **AGPL-3.0-or-later**.
- The plugin SDK, official plugins, templates and schemas are **Apache-2.0**.
- Inbound contributions are licensed under the same terms as the component they touch (inbound = outbound).
- Every commit must be signed off: `git commit -s`. This certifies the [Developer Certificate of Origin 1.1](https://developercertificate.org/). There is no CLA.

## Development Setup

Requires Python 3.11 or newer.

```bash
git clone https://github.com/forgel-dev/forgel.git
cd forgel
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
make test
make lint
```

Run the M0 end-to-end skeleton:

```bash
make demo
```

The demo creates a project under `.forgel-demo/`, runs the pipeline, and writes a staging descriptor. The pipeline parks at the staging approval gate. Inspect and close it with:

```bash
PYTHONPATH=src python3 -m forgel status <project-id> --home .forgel-demo
PYTHONPATH=src python3 -m forgel approve <project-id> --scope staging
PYTHONPATH=src python3 -m forgel run <project-id> --home .forgel-demo
```

`forgel telegram` runs the same core behind a Telegram chat interface; see the
README. It needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_CHAT_IDS` and is
closed to every other chat.

## Project Layout

| Path | Purpose |
|---|---|
| `src/forgel/` | Core: orchestrator, ledger, state machine, registry, CLI |
| `src/forgel/templates/` | Project templates used by recipes |
| `plugins/official/` | Official plugins (created in M2) |
| `registry/` | Recipe registry data |
| `tests/` | `unittest` suite |
| `docs/` | Public documentation |
| `PLAN.md` | Product and architecture plan |
| `INTERNAL.md` | Internal notes — gitignored, never committed |

## Pull Requests

1. Open an issue or RFC first for a significant change.
2. Keep one logical change per pull request.
3. Add a test for behavior; update docs for user-facing changes.
4. Run `make test` and `make lint`.
5. In the PR description, state: what changed, why, how it was tested, and any risks.

Small fixes (typos, broken links) can go straight to a PR.

## Commit Messages

- English, imperative mood, subject at most 72 characters.
- The body explains **why**, not what the diff already shows.
- Sign off with `-s`.
- Conventional Commits are welcome but not required.

## Plugins and Recipes

The plugin SDK and the conformance kit land in M2. Until then, propose a plugin or recipe in an issue with:

- the capability it provides;
- the manifest it would declare;
- how it would pass `provision → apply → verify → rollback → destroy`;
- the license (Apache-2.0 for official plugins).

A recipe is a named composition of plugins, not free-form code. The registry is data; changes require a conformance report.

## Security

Do not open a public issue for a vulnerability. Use the repository's **Security → Report a vulnerability** flow (GitHub Security Advisories). Include a minimal reproduction and the affected version.

## Code of Conduct

Be respectful, assume good faith, and do not harass anyone. Maintainers may remove harmful content and restrict participation. A formal code of conduct will be published before the public alpha.

## Good First Issues

Issues labeled `good first issue` are scoped for new contributors. If you want to take one, comment on it so work is not duplicated.
