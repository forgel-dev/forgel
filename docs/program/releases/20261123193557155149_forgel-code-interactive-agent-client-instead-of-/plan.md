# Release plan 20261123193557155149_forgel-code-interactive-agent-client-instead-of-

- Project: `forgel-1d2bf685`
- Request: Forgel Code: interactive agent client instead of a command wrapper
- Class: minor
- Status: running
- Created: 2026-11-23T19:35:57+00:00


## Request

The Forgel Code client stops being only a set of one-shot, argument-driven wrappers. Opened without arguments it starts an interactive session in which the owner describes work in plain language, reads the agent's answers, follows the plan and the progress of tasks and releases, and accepts work or sends it back with remarks without leaving the session. Adopting a repository, creating a project, secrets and configuration stay explicit. One-shot scripted usage and its machine-readable output remain unchanged, and the client stays thin: the model, the sandbox, independent checks, review and releases stay in the engine. The requirements below follow the existing feature document named by the owner and the client's documented contract; they are behaviour, not implementation.

## Repositories

- `code` — pending, preset python, base 0.1.1, planned 0.2.0

## Tasks

- `20261123193557_forgel-code-interactive-agent-client-ins` — Forgel Code: interactive agent client instead of a command wrapper (code, done)
- `20261123213155_release-audit-forgel-code-interactive-py` — Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the (code, done)
- `20261123213155_release-audit-localization-does-not-sati` — Release audit: Localization does not satisfy the requirement that every reply follow the owner' (code, done)
- `20261123213155_release-audit-the-session-does-not-refre` — Release audit: The session does not refresh task and release state on its own while the owner i (code, done)
- `20261124003849_release-audit-quoted-secret-labels-are-n` — Release audit: Quoted secret labels are not fully redacted. For a message such as `'token': 'ab (code, done)
- `20261124003849_release-audit-redaction-misses-values-se` — Release audit: Redaction misses values separated from a secret label by a newline and values be (code, done)
- `20261124003849_release-audit-the-session-keeps-unredact` — Release audit: The session keeps unredacted engine text in memory. `show_state` assigns the raw (code, done)
- `20261124045451_release-audit-redact-in-forgel-code-inte` — Release audit: `redact()` in `forgel_code/interactive.py` treats the first word after a recogni (code, pending)

## Audit

- Rounds: 3
- Verdict: fail
- Report: `docs/program/releases/20261123193557155149_forgel-code-interactive-agent-client-instead-of-/audit.md`
