# Task Review: Add the engine's one-command installer with pre-install version resolution

- Task: `20261124152248_add-the-engine-s-one-command-installer-w`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-28T00:31:26+00:00

## Summary

The change adds a single POSIX shell installer (install.sh) with three modes — install, read-only resolve and uninstall — plus docs/install.md, a README section and an end-to-end test module that drives the real script in an isolated home directory. The installer installs under the user's own home only, keeps stdout to one plain value for install and resolve, verifies reachability in a freshly started login shell, delimits its start-up contribution in a marked block, stages and checks the new tree before replacing the live one, and keeps engine data out of the install root so removal leaves it intact. Inputs (source, ref, interpreter, locations) come from the environment with documented defaults and no prompting; the minimum interpreter version (3.11) matches the project's declared requires-python, and failures carry a cause and next action on stderr. Documentation is in English, states behaviour and stable interfaces only, and is not read by any test. The attributed commit contains only the four task files; the remaining worktree entries are runtime/agent artifacts outside the task.

## Requirements

- FR-1/AC-1: installs for the invoking user only, without elevated rights, changing no other user's or machine-wide settings: pass — Every path is under HOME or the user-chosen install root; tests run with an isolated HOME and assert no writes outside it.
- FR-2/AC-2: a successful install reports the installed engine version as one plain value on one line, equal to what the installed engine reports about itself: pass — Stdout carries only the version; tests compare it with `forgel version --json` from the installed launcher. docs/install.md states the same contract.
- FR-3/AC-3: engine runnable by name in a newly started terminal session with no user action: pass — A start-up block on the login shell's profile makes `command -v forgel` succeed in a fresh `sh -i -l` session; covered by a test.
- FR-4/AC-5/AC-4: start-up contribution is identifiable and delimited, other settings preserved, repeated installs do not duplicate; unreachable or shadowed engine makes the install fail with cause and next action: pass — A marked BEGIN/END block is rewritten in place rather than appended; tests assert preservation of surrounding lines and non-duplication, and the post-install reachability probe fails the run when the resolved command is not the installed one.
- FR-5/AC-6: re-running for the same target succeeds, reports the same version and leaves exactly one engine: pass — Covered by the repeat-install test asserting a single versioned install directory and an identical reported version.
- FR-6/AC-7: re-running for a newer target installs and reports it, leaves no older engine competing, needs no prior removal and leaves nothing half-replaced: pass — The new target is staged and checked in a versioned directory before the launcher is republished; the upgrade test asserts one reachable engine at the newer version.
- FR-7/AC-8: removal takes back exactly the installed engine and the start-up contribution, leaves other settings unchanged and the engine unreachable in a new session: pass — Uninstall removes the marked block and the install root only; tests assert the profile matches its pre-install content and the command is gone.
- FR-8/AC-9/AC-10: removal keeps engine data and succeeds with a 'nothing was installed' message when nothing is present: pass — Data lives outside the install root and is untouched by removal; the no-op uninstall succeeds and prints the message.
- FR-9/AC-11: read-only resolution mode reports the version the chosen target would install and succeeds with or without an installed engine: pass — `--resolve` answers from the target's version information only; tests cover the fresh-home and post-install cases.
- FR-10/AC-12: resolution mode changes nothing, including an existing installation's version: pass — Resolve path performs no write; the test asserts the home directory stays empty and the installed version is unchanged.
- FR-11/AC-14: resolve prints one plain version on one line and, when the version cannot be determined, fails naming cause and next action with no version: pass — Unreachable source, unknown reference and version-less target all raise a failure written to stderr with `error:`/`next:`; the test asserts empty stdout and non-zero exit.
- FR-12/AC-15: source, reference and interpreter are non-interactive inputs with documented defaults (official channel, latest stable release, a supported interpreter on the machine): pass — FORGEL_SOURCE/FORGEL_REF/FORGEL_PYTHON plus location inputs, all documented in docs/install.md; both modes read the same inputs and stdin is closed in tests.
- FR-13/AC-16/AC-17: requires an interpreter at or above the engine minimum, stops before changing anything with the minimum and what to obtain, and any failure leaves the previous version working: pass — MIN 3.11 matches pyproject requires-python; the interpreter check runs before any write, and the live install is only replaced after the staged tree is verified.
- No automated check reads a documentation file; documentation is judged by review: pass — tests/test_install.py drives the installer only; no test opens README.md or docs/install.md.
- Documentation is accurate, in English, and states behaviour and stable interfaces without volatile implementation detail: pass — docs/install.md and the README section describe modes, inputs, defaults, streams and outcomes consistently with the script's contract; no internal structure, timings or local-environment detail.
- The committed change contains only files the task needs and no unrelated, temporary, debug or generated file: pass — The attributed commit touches README.md, docs/install.md, install.sh and tests/test_install.py; the remaining worktree entries are runtime/agent artifacts outside the task commit.
- No existing test was weakened or deleted: pass — The change adds tests only; no removals detected in the attributed commit.

## Blocking

- none

## Test Removals

- none


