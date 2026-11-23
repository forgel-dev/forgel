# Release plan 20261123193557155149_forgel-code-interactive-agent-client-instead-of-

- Project: `forgel-1d2bf685`
- Request: Forgel Code: interactive agent client instead of a command wrapper
- Class: minor
- Status: planned
- Created: 2026-11-23T19:35:57+00:00


## Request

The Forgel Code client stops being only a set of one-shot, argument-driven wrappers. Opened without arguments it starts an interactive session in which the owner describes work in plain language, reads the agent's answers, follows the plan and the progress of tasks and releases, and accepts work or sends it back with remarks without leaving the session. Adopting a repository, creating a project, secrets and configuration stay explicit. One-shot scripted usage and its machine-readable output remain unchanged, and the client stays thin: the model, the sandbox, independent checks, review and releases stay in the engine. The requirements below follow the existing feature document named by the owner and the client's documented contract; they are behaviour, not implementation.

## Repositories

- `code` — pending, preset python, base 0.1.1, planned 0.2.0

## Tasks

- `20261123193557_forgel-code-interactive-agent-client-ins` — Forgel Code: interactive agent client instead of a command wrapper (code, pending)

## Audit

- Rounds: 0
- Verdict: not run
- Report: `—`
