# Task Spec: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo |
| Project | — |
| Task | `20261123062514_release-audit-readme-md-still-documents-` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T12:02:55+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

README.md tells users to install and uninstall `forgel-code` by piping a script from the `v0.1.0` release tag (`.../v0.1.0/install.sh`). The released `v0.1.0` script predates login-shell detection, fresh-shell verification, the guarded profile block, cross-profile uninstall and `FORGEL_CODE_PROFILE` cleanup. A new user who follows the README therefore still hits the original PATH bug (a new terminal cannot find `forgel-code`), and the documented uninstall can leave the new block, its separator and the override-profile block behind. The documentation contradicts the v0.1.1 behavior the release describes.

**Outcome:** README.md documents the install script URL of the current release for both the install and the uninstall command, so a user who follows the documentation runs the release's actual installer and uninstaller; the stale `v0.1.0` install-script URL is gone from the README and the existing test suite passes.

## Product Intent

A user who installs `forgel-code` from the published instructions must get a terminal in which `forgel-code` is on PATH, and a documented uninstall that fully removes the change. Documentation is part of the release, so it must describe the released behavior, not an earlier one.

## User Experience

A new user copies the install command from README.md, runs it, opens a new terminal and finds `forgel-code` on PATH; later they copy the uninstall command and the shell profile is left clean, with no orphaned block, separator or override-profile block.

## Roadmap

—

## Goals

- Remove the stale `v0.1.0` install-script URL from README.md.
- Make the install and uninstall commands point at the current release's install.sh so documented behavior matches released behavior.
- Keep the existing README test suite green and, where needed, extend it to lock the URL consistency.

## Non-Goals

- Changing install.sh behavior, the guarded block, login-shell detection, fresh-shell verification, cross-profile uninstall or FORGEL_CODE_PROFILE handling.
- Assigning, promising, creating or moving a release tag or a release version.
- Rewriting the published v0.1.0 release notes or release directory.
- Adding installation methods, badges, new documentation sections or new install options.
- Changing the package code (forgel_code/*) or packaging metadata (pyproject.toml, _build_backend.py).

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code. It is a Python client installed as `forgel-code`. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-005: The repository is public and lives in the same organization (`forgel-dev`). | User, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: R1: README.md contains no reference to the `v0.1.0` install script URL (`.../v0.1.0/install.sh`), in the install command or anywhere else.
- **FR-2**: R2: The README install command and the README uninstall command reference exactly the same install-script URL, and that URL is the only install-script URL in README.md.
- **FR-3**: R3: The install-script URL in README.md points at the release whose behavior the documentation describes (the current release, i.e. the v0.1.1 release referenced by the audit finding), not at an earlier tag. The version selector appears exactly once in the URL and both commands inherit it.
- **FR-4**: R4: No other README content changes: the surrounding prose, command shape (`curl -fsSL <url> | bash`), options and section structure stay as they are, except for the URL itself.
- **FR-5**: R5: If the chosen URL names a release tag that is not yet published at commit time, the README names the newest published tag instead and the discrepancy is recorded in the task report; README must never advertise a tag that does not resolve.
- **FR-6**: R6: The existing test suite passes, and tests/test_readme_install.py either already fails on the stale URL (and therefore now passes) or is extended to assert R1 and R2 without weakening any existing assertion.
- **FR-7**: R7: No change to install.sh, forge_code/*, pyproject.toml or the release directories is introduced by this task.

## Technical Requirements

- A published tag is immutable; the fix is a new commit, never a rewrite of the v0.1.0 tag (FORGEL.md, AGENTS.md Release Rules).
- Agents do not assign, promise or rewrite release versions or tags; the release report is the source of truth for the version (AGENTS.md Release Rules).
- All committed artifacts are in English, commit messages imperative with `git commit -s` (AGENTS.md).
- Never weaken a test to make it pass (code/AGENTS.md).
- No tool attribution lines or session references in the commit message.
- Change is reversible and pre-release; proceed without asking (code/AGENTS.md autonomy rule).

## User Stories

- As a new user, I want the README install command to run the current installer so that a new terminal finds `forgel-code` on PATH.
- As an existing user, I want the documented uninstall command to run the current uninstaller so that my shell profile is left clean.
- As a maintainer, I want the README install URLs to be consistent and covered by a test so that a stale tag cannot slip into a release again.

## Tests

- A1: `bash -lc ! grep -q 'v0.1.0/install.sh' README.md`
- A2: `bash -lc test $(grep -oE 'https?://[^ )]*/install\.sh' README.md | sort -u | wc -l) -eq 1 && test $(grep -coE 'https?://[^ )]*/install\.sh' README.md) -ge 2`
- A3: `bash -lc url=$(grep -oE 'https?://[^ )]*/install\.sh' README.md | head -1); echo "$url"; test "$(curl -fsSL -o /dev/null -w '%{http_code}' "$url")" = 200`
- A4: review
- A5: `python -m pytest`
- A6: `bash -lc git diff --name-only | grep -vE '^(README\.md|tests/test_readme_install\.py)$' | wc -l | grep -qx 0`
- Command: `python -m pytest`

## Acceptance Criteria

- **AC-1**: A1: A grep for `v0.1.0/install.sh` in README.md returns nothing.
- **AC-2**: A2: All install-script URLs found in README.md are identical, and there are at least two of them (one in the install command, one in the uninstall command).
- **AC-3**: A3: The version selector in the README install-script URL equals the version documented as the current release, and the URL is fetchable (HTTP 200) from the public repository.
- **AC-4**: A4: The README diff contains only URL changes, reviewable as a small, self-contained change.
- **AC-5**: A5: `python -m pytest` passes for the whole repository, including tests/test_readme_install.py.
- **AC-6**: A6: `git diff --name-only` lists only README.md and, optionally, tests/test_readme_install.py.

## Scope Boundaries

- README.md: the install command that pipes `install.sh`.
- README.md: the uninstall command that pipes `install.sh`.
- tests/test_readme_install.py: only if the existing assertion pins the stale URL or does not yet assert that install and uninstall reference the same, current script URL.
- Changing install.sh behavior, the guarded block, login-shell detection, fresh-shell verification, cross-profile uninstall or FORGEL_CODE_PROFILE handling.
- Assigning, promising, creating or moving a release tag or a release version.
- Rewriting the published v0.1.0 release notes or release directory.
- Adding installation methods, badges, new documentation sections or new install options.
- Changing the package code (forgel_code/*) or packaging metadata (pyproject.toml, _build_backend.py).

## Risks

- If the intended release tag (v0.1.1) is not yet published when this task is committed, a README pointing at it advertises a 404 URL; the coder must fall back to the newest published tag and record it (R5).
- The README may reference the install script in more places than the two commands (e.g. troubleshooting prose); a partial fix leaves users on the old script.
- tests/test_readme_install.py may hard-code the expected URL; updating it could look like weakening a test, so the report must show that the assertion was tightened, not loosened.
- A repository-rename or raw-URL convention mismatch (organization `forgel-dev`, repository name) could make the new URL unreachable while still passing a local grep check; the HTTP 200 check is what catches this.
- README-only change cannot by itself prove the PATH bug is fixed for a new user; that proof came from install.sh behavior and earlier tests, and this task only aligns documentation with it.

## Open Questions

- None.

## Affected Files

- README.md
- tests/test_readme_install.py

## Assumptions

- The README install and uninstall commands share one install-script URL; if they genuinely differ, R2 is applied per documented purpose and the report says so.
- The release that fixes the PATH bug is the one the release report names as current (v0.1.1 in the audit finding); the exact tag is read from the release report and CHANGELOG.md rather than invented.
- `tests/test_readme_install.py` is the authoritative existing guard for README install instructions; extending it is preferable to adding a new test file.
- Keeping the URL pinned to a tag (rather than a moving branch) is intended, because the documented script must match the documented behavior; this is treated as stable existing README style.

## Related Documents

- CHANGELOG.md
- releases/0.1.0/release.md
- releases/0.1.0/plan.md
- install.sh
- AGENTS.md

## Revision History

- v1: Initial specification for the README release-audit fix (stale v0.1.0 install-script URL).

## External Dependencies

- **GitHub release asset / raw file URL for install.sh** — mode `stub`; interface: Tests intercept the documented `curl -fsSL https://raw.githubusercontent.com/forgel-dev/<repo>/<tag>/install.sh` fetch with a deterministic `curl` shim. The shim returns the repository's current `install.sh` for v0.1.1 and `git show v0.1.0:install.sh` for the immutable v0.1.0 tag. The production interface remains an HTTPS GET of the tag-pinned raw URL returning HTTP 200.; docs: README.md install/uninstall command blocks; AGENTS.md Release Rules; releases/0.1.0/release.md; evidence: README.md documents `.../v0.1.0/install.sh` for both install and uninstall, and the release audit finding says the described behavior is v0.1.1. AGENTS.md Release Rules state that a published tag is immutable and the release report is the source of truth, so the raw URL is tag-pinned. The repository has the current `install.sh` and the v0.1.0 tag content is available through git.
  ```
  #!/bin/sh
  # tests/stubs/curl - deterministic fixture for the tag-pinned install.sh URL.
  set -eu
  
  url=
  for arg in "$@"; do
      case "$arg" in
          -*) ;;
          *) url=$arg ;;
      esac
  done
  
  root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
  case "$url" in
      https://raw.githubusercontent.com/forgel-dev/*/v0.1.0/install.sh)
          exec git -C "$root" show v0.1.0:install.sh
          ;;
      https://raw.githubusercontent.com/forgel-dev/*/v0.1.1/install.sh)
          exec cat "$root/install.sh"
          ;;
      *)
          printf '%s\n' "stub curl: no fixture for $url" >&2
          exit 22
          ;;
  esac
  ```
- **curl** — mode `direct`; interface: The documented install and uninstall commands use `curl -fsSL https://raw.githubusercontent.com/forgel-dev/<repo>/<tag>/install.sh | bash`; tests run the same command shape against the URL fixture.; docs: README.md install/uninstall command blocks; evidence: README.md uses `curl -fsSL .../install.sh | bash` for install and uninstall. The dependency contract also states that checks exercise the same URL fetches, so curl is the local executable invoked by the command.
- **pytest** — mode `direct`; interface: `pytest` runs the repository test suite under `tests/`; `make test` is the project's required verification entry point.; docs: pyproject.toml; AGENTS.md Change Workflow and Layout; evidence: The dependency contract identifies pytest as the repository test runner and `pyproject.toml` as its configuration source. AGENTS.md requires `make test`/`make lint` and identifies `tests/` as the test suite.
