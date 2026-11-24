# Task Spec: Add the engine's one-command installer with pre-install version resolution

## Document Information

| Field | Value |
|-------|-------|
| Feature | Add the engine's one-command installer with pre-install version resolution |
| Project | — |
| Task | `20261124152248_add-the-engine-s-one-command-installer-w` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `main` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-24T15:22:48+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

Ship an installer for the engine that performs a per-user install into a private prefix, writes a `forgel` launcher on PATH through a marked profile block verified in a fresh login shell, is idempotent on re-run, supports uninstall, and prints the version it installed. Before installing, it reports the version provided by a configured target source or ref without changing anything, so another installer can compare against an installed engine and decide whether to install. Source, ref and interpreter configuration come from its environment.

**Outcome:** The owner decides this task's scope before it can be implemented.

## Product Intent

—

## User Experience

—

## Roadmap

—

## Goals

- None stated.

## Non-Goals

- None stated.

## User Decisions

| — | No explicit user decisions were recorded in this conversation. | — |

## Functional Requirements

- None stated.

## User Stories

- None stated.

## Acceptance Criteria

- None stated.

## Scope Boundaries

- None stated.

## Risks

- the dependency scout exceeded its step limit

## Open Questions

- the dependency scout exceeded its step limit

## Assumptions

- None stated.

## Related Documents

- `docs/program/decisions.md`

## Revision History

- 1.0.0 — blocked: the specification needs a decision
