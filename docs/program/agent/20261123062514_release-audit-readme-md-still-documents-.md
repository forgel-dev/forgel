# Agent Run: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Status: `done`
- Repository: `code`
- Steps: 23
- Finished: 2026-11-23T12:40:28+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The README keeps naming the pinned tag v0.1.1 rather than the only currently published tag v0.1.0, because the specification's FR-1 to FR-3 state the v0.1.1 commands character for character and the acceptance criteria forbid any `/v0.1.0/` install-script path in README.md.
- The guard's second install-script URL check is proven with a divergent tag (v0.1.2) on the uninstall line, since a divergent URL that keeps the current tag cannot exist under the single-tag rule the guard enforces.
- Only the README URL lines, the one `tests/test_cli.py` pin, the one existing CHANGELOG bullet and the guard module are in scope; install.sh, its `FORGEL_CODE_TAG` default and its header comment stay untouched.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 23
- Estimated input tokens (all calls): 656559
- Provider input/output tokens: 697116 / 34653
- Provider cache hit/miss tokens: 661376 / 35740
- Estimated prompt at the end: 36936 tokens
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
| Created | 2026-11-23T12:30:20+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The release audit found README.md still documenting the previous release's installer URL (`.../v0.1.0/install.sh`), and the repository's README pins disagree: `tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command` still expects the v0.1.0 URL while `tests/test_readme_install.py` guards for v0.1.1. The documentation and both test pins must name one current release installer, and the guard must be verified by its observable rejection behaviour rather than by the wording of its error messages or by a token grep that forbids the word `curl` the documented commands must contain.

**Outcome:** README.md's install, update and uninstall commands all fetch `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh`; no install-script path under `/v0.1.0/` remains in README.md; `tests/test_readme_install.py` holds a text-only guard that fails on a stale tag, a stale install-script path or a divergent install-script URL and proves that failure with two negative tests; `tests/test_cli.py`'s README pin expects the v0.1.1 URL and fails on the v0.1.0 path; and the whole suite passes.

## Product Intent

A new user must be able to copy one command out of the README and install the current release of Forgel Code; documentation that points at a superseded installer is a release defect (D-004: the client is installed as `forgel-code` from its own public repository).

## User Experience

A reader of README.md copies the install, update or uninstall command as printed and gets the current release installer instead of the old one; a contributor who edits those commands to another tag sees the test suite fail instead of shipping stale install instructions.

## Roadmap

—

## Goals

- README.md documents the current release installer for install, update and uninstall and no stale install-script path.
- The README guard fails when a documented command drifts to another tag or to a divergent install-script URL, and that failure is proven by tests.
- The two README pins in the repository agree on one release tag.
- The changelog records the fix once.
- The whole suite passes.

## Non-Goals

- Changing install.sh behaviour, its `FORGEL_CODE_TAG` default or its header comment
- Assigning, promising or rewriting a release version or tag
- Publishing a release or editing files under `releases/`
- Changing the client (`forgel_code/`), packaging, or any test other than the README pins and the README guard
- Rewriting the README's prose sections (profile selection, options, commands)
- Requiring the guard's error messages to contain any particular wording

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-001: the interactive client lives in a separate public repository in the same organization as the engine. | User, 2026-11-16 21:14 |
| — | D-004: the client's working name is Forgel Code, installed as `forgel-code`, a Python client that imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-005: the second repository is public and lives in the `forgel-dev` organization, which is why the documented installer URL is `raw.githubusercontent.com/forgel-dev/code/...`. | User, 2026-11-16 21:14 |

## Functional Requirements

- **FR-1**: FR-1: The first command of the first code block under `## Install` in README.md is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh`.
- **FR-2**: FR-2: The command shown under `### Update` is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh`.
- **FR-3**: FR-3: The command shown under `### Uninstall` is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh -s -- --uninstall`.
- **FR-4**: FR-4: README.md contains no install-script path under `/v0.1.0/`, and every line of README.md that names an `install.sh` URL names the single URL `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh`.
- **FR-5**: FR-5: `tests/test_readme_install.py` keeps a guard that reads README.md as text and fails when the first install command is not the one-command installer, when any documented install-script URL is not the v0.1.1 URL, or when the `/v0.1.0/install.sh` path appears; the guard is not deleted, disabled or narrowed to fewer of these cases.
- **FR-6**: FR-6: The guard module contains a test named `test_stale_install_script_url_is_rejected` that feeds the guard's install-script-URL assertion a document carrying `/v0.1.0/install.sh` and requires the assertion to raise.
- **FR-7**: FR-7: The guard module contains a test named `test_divergent_install_script_url_is_rejected` that feeds the same assertion a document whose second install-script URL differs in tag or URL from the first and requires the assertion to raise.
- **FR-8**: FR-8: `tests/test_readme_install.py` imports none of `urllib`, `http.client`, `requests`, `socket`, `subprocess` and calls none of `os.system`, `os.popen`, `urlopen`, `urlretrieve`; it verifies the documentation as text only and fetches nothing.
- **FR-9**: FR-9: The README pin in `tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command` expects `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh` and fails when README.md carries the `/v0.1.0/install.sh` path.
- **FR-10**: FR-10: CHANGELOG.md keeps exactly one English bullet under `## [Unreleased]` recording this fix — that the README install, update and uninstall commands now name the v0.1.1 release installer and that the README guard fails on a stale tag or a divergent install-script URL. The delivered tree already carries this bullet (under `### Fixed`), so the change keeps it and does not add a second bullet for the same fix.
- **FR-11**: FR-11: `python -m unittest discover -s tests` passes from a checkout with unchanged runtime behaviour of the client, the installer and the packaging.
- **FR-12**: FR-12: No file outside the affected files changes in this task.

## Technical Requirements

- Artifacts are English (project rule, D-025 in AGENTS.md).
- Standard library only; the tests run under `python -m unittest discover -s tests` with no network access and no extra environment.
- A published tag is immutable and the runtime release train computes versions (FORGEL.md, AGENTS.md Release Rules): this task references v0.1.1, it does not choose or publish it.
- Never weaken a test to make it pass; fix the product or the test's premise (repository AGENTS.md).
- No tool attribution lines or session references in commits or pull requests.
- The README guard must not depend on the wording of its own failure messages.

## User Stories

- As a new user, I want the README install command to fetch the current release installer so that I install the version the documentation describes.
- As a contributor, I want the test suite to fail when I change a documented install command to an older tag so that stale install instructions never ship.
- As a release auditor, I want the README pin in the client tests and the documentation guard to agree on one tag so that the audit does not report a contradiction.

## Tests

- A1: `python -m unittest -v tests.test_readme_install`
- A2: `python -c import sys;t=open('README.md',encoding='utf-8').read();c=t.count('/v0.1.1/install.sh');s=t.count('/v0.1.0/');print('v0.1.1 installer URLs:',c,'stale paths:',s);sys.exit(0 if c==3 and s==0 else 1)`
- A3: `python -m unittest -k test_stale_install_script_url_is_rejected -v tests.test_readme_install`
- A4: `python -m unittest -k test_divergent_install_script_url_is_rejected -v tests.test_readme_install`
- A5: `python -c import sys;t=open('tests/test_readme_install.py',encoding='utf-8').read();bad=[s for s in ('import urllib','import http.client','import requests','import socket','import subprocess','from subprocess','os.system','os.popen','urlopen','urlretrieve') if s in t];print(bad);sys.exit(1 if bad else 0)`
- A6: `python -m unittest -v tests.test_cli.ReadmeTest`
- A7: review
- A8: `python -m unittest discover -s tests`
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: A1: The guard over README.md passes: the install, update and uninstall commands are the three v0.1.1 commands of FR-1 to FR-3 and no install-script URL diverges.
- **AC-2**: A2: README.md contains exactly three occurrences of `/v0.1.1/install.sh` and zero occurrences of the install-script path `/v0.1.0/`.
- **AC-3**: A3: `test_stale_install_script_url_is_rejected` passes, proving the guard's rejection of the stale tag by behaviour rather than by message wording.
- **AC-4**: A4: `test_divergent_install_script_url_is_rejected` passes, proving the guard rejects a divergent install-script URL.
- **AC-5**: A5: A scan of `tests/test_readme_install.py` finds no network or process capability as listed in FR-8, so the guard's claim about documentation is made from text alone.
- **AC-6**: A6: `tests.test_cli.ReadmeTest` passes with the v0.1.1 URL pinned.
- **AC-7**: A7: CHANGELOG.md's `## [Unreleased]` section carries exactly one English bullet that records this fix and no duplicate of it.
- **AC-8**: A8: The full `unittest` suite passes.

## Scope Boundaries

- README.md: the `## Install`, `### Update` and `### Uninstall` commands and every other install-script URL the document names
- tests/test_readme_install.py: the README guard, its stale-tag and divergent-URL rejection tests, and its absence of network or process capability
- tests/test_cli.py: the README pin in `ReadmeTest` that still expects the v0.1.0 URL
- CHANGELOG.md: the single `## [Unreleased]` bullet that records this fix
- Changing install.sh behaviour, its `FORGEL_CODE_TAG` default or its header comment
- Assigning, promising or rewriting a release version or tag
- Publishing a release or editing files under `releases/`
- Changing the client (`forgel_code/`), packaging, or any test other than the README pins and the README guard
- Rewriting the README's prose sections (profile selection, options, commands)
- Requiring the guard's error messages to contain any particular wording

## Risks

- The full suite runs the real installer through `pip` into a temporary home and has a two-minute bound; a slow machine can exceed it and fail A8 for reasons unrelated to this change.
- The reported pin is `tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command`; if the class or method name differs in the tree, FR-9 must be applied to the real test rather than duplicated as a new one, otherwise A6 fails.
- The guard's negative tests must call the same assertion the positive path uses; a negative test that reimplements the check would pass while the real guard stays unproven.
- install.sh still defaults to `FORGEL_CODE_TAG=v0.1.0` and its header shows the v0.1.0 URL; the README guard is scoped to README.md, so those mentions stay and must not be pulled into this change or into the guard.
- Requiring exactly three `/v0.1.1/install.sh` occurrences in README.md is strict; a legitimate fourth documented command would fail A2 and must be handled by a deliberate spec change, not by loosening the guard silently.
- Editing the README command strings without updating the guard's expected constants would make the guard fail for the wrong reason; the constants and the document move together.

## Open Questions

- None.

## Affected Files

- README.md
- tests/test_readme_install.py
- tests/test_cli.py
- CHANGELOG.md

## Assumptions

- The task intent offers `v0.1.1` or a versionless latest URL; v0.1.1 is chosen because the immutable-tag rule makes a pinned release tag the safe target and README.md, the guard and CHANGELOG.md already name v0.1.1.
- The three documented commands are the only install-script URLs README.md should carry; the Windows fallback line stays as it is and is not an install-script command.
- `tests/test_cli.py`'s README pin asserts one command string; converting it to the v0.1.1 URL is the whole change there.
- The CHANGELOG bullet for this fix already exists; it is required, not out of scope, and is kept rather than rewritten.
- install.sh's own v0.1.0 default tag and header comment are outside this task's scope.

## Related Documents

- FORGEL.md
- AGENTS.md
- install.sh
- releases/0.1.0/release.md

## Revision History

- v1: initial specification for the README install-command release audit.
- v2: scoped the guard's no-network check to imports and process invocation instead of the token `curl`, which the required command strings must contain.
- v3: added `tests/test_cli.py`'s README pin to scope so FR-11 (now FR-9) can hold.
- v4: stated that the single English `## [Unreleased]` CHANGELOG bullet is required and already present, and pinned the guard's rejection by its negative tests instead of its message wording (current).

## External Dependencies

- **GitHub raw content URL for the release installer** — mode `unknown`; interface: `https://raw.githubusercontent.com/forgel-dev/code/<tag>/install.sh` returns the raw POSIX `sh` installer for tag `<tag>`; the documentation quotes this URL as the install, update and uninstall command and the tests assert its text, never fetching it.; docs: README.md `## Install`; install.sh header comment; evidence: —


## Summary

README.md now documents one install-script URL, https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh, in the `## Install` command, the `### Update` command and the `### Uninstall` command (`| sh -s -- --uninstall`); the only README change is the URL in those lines, so no `.../v0.1.0/install.sh` reference remains. tests/test_cli.py's `ReadmeTest::test_readme_has_a_pinned_install_command` now pins the full v0.1.1 command instead of the v0.1.0 URL. CHANGELOG.md keeps exactly one English `## [Unreleased]` bullet recording the fix. tests/test_readme_install.py keeps the text-only guard built from the single `INSTALL_TAG = "v0.1.1"` constant and gains the two named rejection tests required by the spec: `test_stale_install_script_url_is_rejected` feeds the guard's own `assert_single_install_script_url` a document carrying `/v0.1.0/install.sh`, and `test_divergent_install_script_url_is_rejected` feeds it a document whose second install-script URL names another tag; both require the same assertion the positive path uses to raise, so the guard is proven by behaviour rather than message wording. The module imports only `re`, `unittest` and `pathlib` and fetches nothing. Verified with `python -m unittest -v tests.test_readme_install tests.test_cli.ReadmeTest` (37 tests OK) and the full `python -m unittest discover -s tests` (211 tests OK, ~141 s). Note: the documented installer URL currently answers HTTP 404 because the v0.1.1 tag is not published yet; that is recorded under spec_issues.; uncommitted files outside the contract: install.sh, tests/test_check_cleanup.py, tests/test_install.py

## Files Changed

- `CHANGELOG.md`
- `README.md`
- `tests/test_cli.py`
- `tests/test_readme_install.py`

## Commands

- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python", "-m", "unittest", "-v", "tests.test_readme_install", "tests.test_cli.ReadmeTest"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["python", "-m", "unittest", "-v", "tests.test_readme_install", "tests.test_cli.ReadmeTest"]` → exit 0
- `["git", "diff", "--name-only"]` → exit 0
- `["git", "status", "--short"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["git", "diff", "--stat", "--", "tests/test_readme_install.py"]` → exit 0
- `["python", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
...................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 211 tests in 141.855s

OK

```

## Actions

- read_file: README.md
- read_file: tests/test_readme_install.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: CHANGELOG.md
- read_file: tests/test_cli.py
- run: ['python', '-c', "import sys;t=open('README.md',encoding='utf-8').read();c=t.count('/v0.1.1/install.sh');s=t.count('/v0.1.0/');print('v0.1.1 installer URLs:',c,'stale paths:',s);sys.exit(0 if c==3 and s==0 else 1)"]
- run: ['python', '-m', 'unittest', '-v', 'tests.test_readme_install', 'tests.test_cli.ReadmeTest']
- run: ['git', 'status', '--short']
- run: ['git', 'diff', '--stat']
- write_file: tests/test_readme_install.py
- run: ['python', '-m', 'unittest', '-v', 'tests.test_readme_install', 'tests.test_cli.ReadmeTest']
- run: ['git', 'diff', '--name-only']
- run: ['git', 'status', '--short']
- recall
- read_file: tests/test_cli.py
- run: ['python', '-m', 'unittest', 'discover', '-s', 'tests']
- recall
- recall
- run: ['git', 'diff', '--stat', '--', 'tests/test_readme_install.py']
