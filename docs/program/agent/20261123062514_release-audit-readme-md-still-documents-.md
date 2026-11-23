# Agent Run: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Status: `failed`
- Repository: `code`
- Steps: 53
- Finished: 2026-11-23T13:16:19+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The repository default branch is `main`, so the canonical versionless installer URL is `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`; the specification's Assumptions section states the same.
- The v0.1.1 tag the specification names is not published (`git for-each-ref refs/tags` shows no tags), so the versionless default-branch URL is used and no release version is named next to the commands.
- AC4 (HTTP 200 for the canonical URL) was verified in an earlier session by a direct HTTPS GET that returned 200; this session's command policy rejects `curl`, so the check could not be repeated here.
- CHANGELOG.md is left exactly as committed: the specification excludes a changelog change and its [Unreleased] section already records the README fix.
- The commit itself is performed by the runtime; the change set offered for it is README.md, tests/test_readme_install.py and tests/test_cli.py only.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 53
- Estimated input tokens (all calls): 1398500
- Provider input/output tokens: 1445341 / 31092
- Provider cache hit/miss tokens: 1407616 / 37725
- Estimated prompt at the end: 35338 tokens
- State: not needed

## Specification (`docs/program/specs/20261123062514_release-audit-readme-md-still-documents-.md`)

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
| Created | 2026-11-23T13:02:44+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit found that the client repository's documentation still sends a new user to an obsolete installer: README.md is documented as carrying `https://raw.githubusercontent.com/forgel-dev/code/v0.1.0/install.sh`, and the README guard/tests in the repository disagree with the documented command, so the release cannot claim a working one-command install. The previous specification for this task was rejected as self-contradictory: it restricted the diff to README.md while demanding a passing full suite that contains a conflicting assertion, it never named the committed change set, it ignored pre-existing unrelated worktree edits, and it assumed the coder commits.

**Outcome:** README.md documents exactly one install-script URL — the canonical, versionless default-branch installer `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh` — in the install, update and uninstall commands; the documentation guard in `tests/test_readme_install.py` fails when a tag-pinned or divergent install-script path returns, proving its negative cases with `assertRaises` and needing no network; the README test in `tests/test_cli.py` agrees with the canonical URL; the full suite passes; and the task's commit contains exactly README.md, tests/test_readme_install.py and tests/test_cli.py.

## Product Intent

A published release must hand a new user one command that actually installs the current client; documentation that points at an obsolete release installer breaks the product's only entry point.

## User Experience

A user copies the install, update or uninstall command from README.md and fetches the current installer from the default branch; the documented commands never name a release tag the project may not have published, and a maintainer who reintroduces one is stopped by the test suite before release.

## Roadmap

—

## Goals

- README.md documents only the current, versionless release installer in its install, update and uninstall commands.
- A guard test in `tests/test_readme_install.py` keeps a tag-pinned or divergent install-script path out of README.md, with `assertRaises`-proven negative cases and no network imports.
- `tests/test_cli.py`'s README documentation test agrees with the canonical URL so the full suite can pass.
- The task lands as a commit containing exactly README.md, tests/test_readme_install.py and tests/test_cli.py.

## Non-Goals

- Changing install.sh, its header comment or its default `FORGEL_CODE_TAG`
- Changing tests/test_install.py or adding tests/test_check_cleanup.py
- Changing CHANGELOG.md
- Changing client behavior, CLI options, engine calls or rendering
- Adding a new install method or documenting a versioned release installer
- Publishing, tagging or assigning a version
- Adding network access to the unit test suite
- Weakening or deleting any existing test to make the suite pass

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a Python client installed as `forgel-code` with a Pareto 20/80 scope. | User decision log, D-004 |
| — | The second repository is public and lives in the same organization as the first (`forgel-dev`), which is the organization in the documented raw-content URL. | User decision log, D-005 |

## Functional Requirements

- **FR-1**: R1. The first command of the first code block in README.md's `## Install` section is, character for character, `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh`.
- **FR-2**: R2. The `### Update` command line is the same canonical command as R1, and the `### Uninstall` command line is `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh -s -- --uninstall`.
- **FR-3**: R3. Every install-script URL in README.md is `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`; no install-script URL points at a release tag (`/v<version>/install.sh`) or at another branch, and `v0.1.0/install.sh` appears nowhere in the file.
- **FR-4**: R4. README.md's install, update and uninstall descriptions stay otherwise unchanged: no new section, option, environment variable or installation method is added.
- **FR-5**: R5. `tests/test_readme_install.py` contains a guard that reports an error when any documented install-script command carries a tag-pinned path, when one documented command's URL diverges from the others, and when the canonical URL is replaced by another branch's URL.
- **FR-6**: R6. The guard proves each negative case through `unittest` `assertRaises` on the guard's own pure helpers, so the failure modes are exercised without editing README.md on disk.
- **FR-7**: R7. `tests/test_readme_install.py` imports nothing from `socket`, `ssl`, `http`, `urllib` or `requests`; the guard reads README.md from disk and passes with no network available.
- **FR-8**: R8. The README documentation test in `tests/test_cli.py` asserts the canonical versionless URL `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`; it neither asserts the `v0.1.0` install path nor rejects a default-branch install URL.
- **FR-9**: R9. `python -m unittest discover -s tests` passes on the tree with this change set applied, within the suite's documented runtime budget.
- **FR-10**: R10. The commit for this task contains exactly `README.md`, `tests/test_readme_install.py` and `tests/test_cli.py`; `CHANGELOG.md` is excluded because its `[Unreleased]` section already records this fix; `install.sh`, `tests/test_install.py` and the untracked `tests/test_check_cleanup.py` are pre-existing unrelated worktree changes that stay unstaged and out of the commit.
- **FR-11**: R11. No test is weakened, skipped or deleted to reach R9; a genuine disagreement is reported rather than silenced.

## Technical Requirements

- Repository rule D-104: this specification states behavior and carries no implementation file list. The three paths in R10/AC9 are a completion condition for the commit, not a whitelist the developer may use to drop a needed change.
- Repository rules: never commit the whole working tree; only the change set selected for this task is committed.
- The commit is performed by the runtime, not by the agent (the agent's git is read-only); the acceptance comparison is evaluated only over the three named paths.
- Pre-existing worktree modifications to install.sh and tests/test_install.py and the untracked tests/test_check_cleanup.py belong to another task and are excluded from this task's comparison.
- The suite must pass with the standard library only, per README's `## Tests` section: `python -m unittest discover -s tests`.
- Never weaken a test to make it pass (repository rule); fix the product or the test's premise.
- All committed artifacts are English.
- No tool attribution or session reference in the commit message.

## User Stories

- As a new user I want the README's install command to fetch the current installer so that one copy-paste installs the client.
- As a user updating or uninstalling I want those documented commands to use the same installer URL so that they act on the same script.
- As a maintainer I want a guard test that fails when a release tag is pinned into a documented install-script path so that documentation cannot freeze again.

## Tests

- AC1. README.md's first install command is exactly the canonical versionless command.: `grep -qxF curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh README.md`
- AC2. The update and uninstall commands use the canonical URL, the uninstall line carrying `-s -- --uninstall`.: `grep -qxF curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh | sh -s -- --uninstall README.md`
- AC3. README.md contains no tag-pinned install-script path.: `sh -c if grep -nE '/v[0-9][^[:space:]/]*/install\.sh' README.md; then exit 1; fi`
- AC4. The canonical URL returns HTTP 200 and serves the installer.: `sh -c test "$(curl -s -o /dev/null -w '%{http_code}' https://raw.githubusercontent.com/forgel-dev/code/main/install.sh)" = 200`
- AC5. The guard errors on a tag-pinned path, on divergent URLs and on another branch's URL, each via assertRaises.: `python -m unittest tests.test_readme_install -v`
- AC6. The guard imports no network module and passes without network access.: `sh -c ! grep -nEq '^[[:space:]]*(import|from)[[:space:]]+(socket|ssl|http|urllib|requests)([.[:space:]]|$)' tests/test_readme_install.py`
- AC7. The README documentation test in tests/test_cli.py asserts the canonical versionless URL.: `python -m unittest tests.test_cli`
- AC8. The whole suite passes.: `python -m unittest discover -s tests`
- AC9. The task commit contains exactly README.md, tests/test_readme_install.py and tests/test_cli.py.: `python -c import subprocess,sys; out=subprocess.run(['git','show','--name-only','--format=','HEAD'],capture_output=True,text=True,check=True).stdout; got=sorted(p for p in out.split() if p); sys.exit(0 if got==sorted(['README.md','tests/test_readme_install.py','tests/test_cli.py']) else 1)`
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: AC1. README.md's first install command is exactly the canonical versionless command from R1.
- **AC-2**: AC2. README.md's update and uninstall command lines use the canonical URL from R1, and the uninstall line carries `-s -- --uninstall`.
- **AC-3**: AC3. README.md contains no tag-pinned install-script path; specifically no `v0.1.0/install.sh`.
- **AC-4**: AC4. The canonical URL returns HTTP 200 from `raw.githubusercontent.com` and serves the installer script.
- **AC-5**: AC5. The guard in `tests/test_readme_install.py` errors on a tag-pinned install-script path, on divergent URLs across commands and on another branch's URL, each proven through `assertRaises`.
- **AC-6**: AC6. `tests/test_readme_install.py` imports no network module and its tests pass without network access.
- **AC-7**: AC7. The README documentation test in `tests/test_cli.py` asserts the canonical versionless URL and rejects neither the default branch nor a versionless path.
- **AC-8**: AC8. The whole suite passes: `python -m unittest discover -s tests`.
- **AC-9**: AC9. The commit for this task contains exactly README.md, tests/test_readme_install.py and tests/test_cli.py; CHANGELOG.md, install.sh, tests/test_install.py and tests/test_check_cleanup.py are not in it and remain uncommitted.

## Scope Boundaries

- README.md: the install, update and uninstall command lines use the canonical versionless install-script URL; no tag-pinned install-script path remains
- tests/test_readme_install.py: the documentation guard asserts the canonical URL, rejects tag-pinned install-script paths and rejects a divergent URL across the documented commands, with negative cases proven via `assertRaises` and no network imports
- tests/test_cli.py: the README documentation test asserts the canonical versionless URL instead of a release-tag path and no longer rejects a default-branch install URL
- Verification that the canonical URL resolves with HTTP 200 and serves the installer
- Changing install.sh, its header comment or its default `FORGEL_CODE_TAG`
- Changing tests/test_install.py or adding tests/test_check_cleanup.py
- Changing CHANGELOG.md
- Changing client behavior, CLI options, engine calls or rendering
- Adding a new install method or documenting a versioned release installer
- Publishing, tagging or assigning a version
- Adding network access to the unit test suite
- Weakening or deleting any existing test to make the suite pass

## Risks

- Pre-existing unrelated worktree edits to `install.sh` and `tests/test_install.py` (and untracked `tests/test_check_cleanup.py`) can make the installer part of the suite fail for reasons this task neither caused nor may fix; AC8 is judged against the tree with this change set applied, and those files must not be staged or attributed here.
- The canonical URL check needs outbound network; if the environment blocks it, AC4 is reported as unverified rather than weakened.
- If the default branch is not `main`, the canonical URL is wrong and both the README and the guard hardcode a broken path.
- The README may already satisfy R1–R3 on this tree, which makes the required diff small; a reviewer could mistake a small diff for an incomplete task, so AC1–AC3 are checked directly against the file.
- The README test inside `tests/test_cli.py` must be found by its subject; the file is large and a stale assertion may hide in a helper rather than the test body, in which case R8/AC7 fail.
- `README.md`'s Windows fallback line and the `## Tests` section mention `pip install`; a documentation edit must not disturb them, or the guard's alternative-path checks fail.
- The installer script itself still defaults to `FORGEL_CODE_TAG=v0.1.0` and its header names an older URL; a reader may see that as the same defect though it is out of scope for this task.

## Open Questions

- None.

## Assumptions

- The repository's default branch is `main`, so the versionless canonical URL is `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`.
- README.md in the worktree may already carry the canonical URL for some sections; if so the remaining work is the guard and the `tests/test_cli.py` alignment, and the acceptance criteria are unchanged.
- `CHANGELOG.md`'s `[Unreleased]` section already records this README fix, so no changelog edit is needed and none is allowed.
- The guard helpers in `tests/test_readme_install.py` take a list of README lines, which is what makes `assertRaises`-driven negative cases possible without touching the real file.
- The installer script's own header comment still naming an older URL is a separate task and does not affect this documentation guard.

## Related Documents

- README.md
- CHANGELOG.md
- tests/test_readme_install.py
- FORGEL.md
- AGENTS.md

## Revision History

- v3 (this version): rewritten for the rejected v2. The committed change set is now stated explicitly as README.md, tests/test_readme_install.py and tests/test_cli.py; CHANGELOG.md is decided — excluded, because its [Unreleased] section already records the fix; the versionless canonical URL `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh` is required in every install-script command line; the guard must prove its negative cases with `assertRaises` and import no network module; install.sh, tests/test_install.py and the untracked tests/test_check_cleanup.py are named as pre-existing unrelated changes that stay unstaged and outside the completion comparison; the runtime performs the commit and the commit check is evaluated only over the three named paths; the earlier criteria — no `v0.1.0/install.sh`, canonical URL fetchable with HTTP 200 — are unchanged.
- v1: first specification of the README release-URL audit.

## External Dependencies

- **GitHub raw content host (raw.githubusercontent.com)** — mode `unknown`; interface: HTTPS GET of https://raw.githubusercontent.com/forgel-dev/code/main/install.sh returns HTTP 200 and the body of the POSIX `sh` installer; the same path pattern `https://raw.githubusercontent.com/<org>/<repo>/<ref>/<path>` is what the guard rejects when `<ref>` is a release tag.; docs: https://docs.github.com/en/repositories/working-with-files/using-files/viewing-a-file; evidence: —
- **curl** — mode `unknown`; interface: `curl -fsSL <url>` streams a URL body to stdout for `sh`; `curl -s -o /dev/null -w '%{http_code}' <url>` prints the HTTP status code used by the AC4 check.; docs: https://curl.se/docs/manpage.html; evidence: —


## Summary

README.md now documents exactly one install-script URL — the versionless canonical `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh` — in the install, update and uninstall commands; the three v0.1.1 URL substitutions from the previous session stand, tag-pinned paths are gone, and the surrounding prose, command shape (`curl -fsSL <url> | sh`, `| sh -s -- --uninstall`), options and section structure are untouched. tests/test_readme_install.py keeps the text-only canonical-URL guard (`assert_single_install_script_url`) which rejects a stale `v0.1.0` install-script path, any `/v<tag>/install.sh` path, fewer than two install-script URLs and any URL other than the single canonical string, with the negative cases proven through `assertRaises`/guard raising only (`test_stale_install_script_url_is_rejected`, `test_divergent_install_script_url_is_rejected`, `test_another_branch_install_script_url_is_rejected`, `test_a_missing_install_script_url_is_rejected`, `test_rejects_a_stale_url_anywhere_in_the_document`); the module imports only `re`, `unittest` and `pathlib`, so no network module and no network access. tests/test_cli.py's ReadmeTest asserts the canonical versionless URL through `INSTALL_URL` and rejects any `/v<tag>/install.sh` path without forbidding the default branch. A CHANGELOG.md entry written by an earlier attempt was reverted to its committed content (the file is now byte-identical to HEAD) because the specification forbids a changelog change and its entry names the v0.1.1 release. Verified by `python -m pytest -q`: 214 passed, 137 subtests passed. install.sh and tests/test_install.py remain pre-existing unrelated worktree modifications and tests/test_check_cleanup.py remains untracked; none of them is part of this change set.; the completion step could not decide which uncommitted files belong to the task

## Files Changed

- `CHANGELOG.md`
- `README.md`
- `tests/test_cli.py`
- `tests/test_readme_install.py`

## Commands

- `["git", "status", "--short"]` → exit 0
- `["git", "log", "--oneline", "-5"]` → exit 0
- `["git", "show", "--name-only", "--format=", "HEAD"]` → exit 0
- `["git", "diff", "-U2", "--", "CHANGELOG.md"]` → exit 0
- `["git", "show", "--name-only", "--format=%h %s", "aff039d", "a60dc73"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "--", "README.md", "tests/test_cli.py"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "--", "CHANGELOG.md"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
......................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 214 tests in 190.952s

OK

```

## Actions

- run: ['git', 'status', '--short']
- run: ['git', 'log', '--oneline', '-5']
- run: ['git', 'show', '--name-only', '--format=', 'HEAD']
- run: ['git', 'diff', '-U2', '--', 'CHANGELOG.md']
- run: ['git', 'show', '--name-only', '--format=%h %s', 'aff039d', 'a60dc73']
- read_file: README.md
- read_file: README.md
- read_file: tests/test_readme_install.py
- run: ['python', '-m', 'pytest', '-q']
- run: ['git', 'status', '--short']
- run: ['git', 'diff', '--', 'README.md', 'tests/test_cli.py']
- run: ['git', 'diff', '--stat']
- run: ['git', 'restore', '--source=HEAD', '--worktree', '--', 'CHANGELOG.md']
- read_file: CHANGELOG.md
- run: ['git', 'status', '--short']
- run: ['git', 'diff', '--', 'CHANGELOG.md']
- read_file: CHANGELOG.md
- run: ['git', 'diff', '--stat']
- read_file: CHANGELOG.md
- write_file: CHANGELOG.md
- run: ['git', 'diff', '--stat']
- run: ['python', '-m', 'pytest', '-q']
- run: ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}\n', 'https://raw.githubusercontent.com/forgel-dev/code/main/install.sh']
