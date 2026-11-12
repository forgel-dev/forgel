# FORGEL.md

Native context file for Forgel. Forgel reads this file first, then `AGENTS.md`,
then `CLAUDE.md` if it is present.

## What Forgel Is

Forgel is an open-source autonomous software studio. The product plan and
decisions live in `PLAN.md`.

## Native Rules

- The source of truth for agent instructions is `AGENTS.md`. This file adds
  Forgel-specific rules and the read order.
- Generated projects carry `FORGEL.md` and `AGENTS.md`. Forgel does not generate
  `CLAUDE.md`.
- Jurisdiction packs are advisory. Never claim legal compliance; the user is
  responsible. Production requires the compliance acknowledgement.
- Generated project code belongs to the user.
- Public artifacts are English; internal working documents may be Russian.

## Read Order

1. `FORGEL.md` (this file)
2. `AGENTS.md`
3. `CLAUDE.md` (local compatibility shim, not committed)

## Start Here

Read `PLAN.md`, then `CONTRIBUTING.md`. For a significant change, open an RFC.
