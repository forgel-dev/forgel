# Release plan 20261124145530795459_make-forgel-and-forgel-code-install-and-run-as-o

- Project: `forgel-1d2bf685`
- Request: Make Forgel and Forgel Code install and run as one working pair: give the engine `forgel` its own installer, add a mode of the Forgel Code installer that installs both binaries together (offered by default in the README, idempotent — when the engine is already present it compares versions and installs only a strictly newer one), and introduce a declared minimum supported engine version for Forgel Code, checked at startup, so a missing or too-old engine produces a clear actionable message instead of `engine forgel: executable not found: forgel`.
- Class: minor
- Status: running
- Created: 2026-11-24T15:22:48+00:00
- Plan: `20261124145600_make-forgel-and-forgel-code-install-and-`

## Request

Make Forgel and Forgel Code install and run as one working pair: give the engine `forgel` its own installer, add a mode of the Forgel Code installer that installs both binaries together (offered by default in the README, idempotent — when the engine is already present it compares versions and installs only a strictly newer one), and introduce a declared minimum supported engine version for Forgel Code, checked at startup, so a missing or too-old engine produces a clear actionable message instead of `engine forgel: executable not found: forgel`.

## Repositories

- `code` — pending, preset python, base 0.2.0, planned 0.3.0
- `main` — pending, preset python, planned 0.1.0

## Tasks

- `20261124152248_add-the-combined-engine-and-client-insta` — Add the combined engine and client install mode (code, done)
- `20261124152248_add-the-engine-s-one-command-installer-w` — Add the engine's one-command installer with pre-install version resolution (main, done)
- `20261124152248_check-the-engine-version-at-client-start` — Check the engine version at client startup (code, done)
- `20261124152248_declare-the-minimum-supported-engine-ver` — Declare the minimum supported engine version in the client (code, done)
- `20261124152248_document-the-combined-install-and-minimu` — Document the combined install and minimum engine version (code, done)
- `20261124152248_document-the-engine-installer-and-versio` — Document the engine installer and version contract (main, done)
- `20261124152248_emit-a-machine-readable-engine-version` — Emit a machine-readable engine version (main, done)
- `20261128085012_release-audit-engine-present-version-run` — Release audit: `engine_present_version` runs `forgel --version --json` and reads `payload["engi (code, pending)
- `20261128085012_release-audit-the-combined-install-tests` — Release audit: The combined-install tests use `tests/stub_engine_install.py`, which encodes the (code, pending)
- `20261128085012_release-audit-the-combined-installer-inv` — Release audit: The combined installer invokes `"$ENGINE_INSTALLER" --source ... --available-ver (code, pending)
- `20261128085012_release-audit-the-main-repository-diff-c` — Release audit: The main repository diff contains changes to `src/forgel/daemon.py` and `tests/t (main, pending)

## Audit

- Rounds: 1
- Verdict: fail
- Report: `docs/program/releases/20261124145530795459_make-forgel-and-forgel-code-install-and-run-as-o/audit.md`
