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
| Created | 2026-11-23T12:16:52+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

README.md documents the install and uninstall commands with the release installer path, but the release reference it carries and the assertions in the test suite disagree: the README's `## Install`, `### Update` and `### Uninstall` blocks must name the current release installer, and the suite contains a pinned-URL expectation in `tests/test_cli.py` (`ReadmeTest::test_readme_has_a_pinned_install_command`) that was written against the old tag. A stale or split release reference in the documented one-command install path is a documentation defect: the reader is sent to an installer for a release that no longer carries the described behaviour, and the suite cannot be green while the two files pin different tags.

**Outcome:** README.md names exactly one install-script URL — the release installer of the current release — and the install, update and uninstall commands all use it character for character. The test suite fails whenever any of those three documented commands names a different tag or a different repository path, and `python -m pytest -q` passes on the whole suite because the pinned-URL assertion in `tests/test_cli.py` now expects the same release as the README guard in `tests/test_readme_install.py`.

## Product Intent

Forgel Code installs with one command copied from README.md (D-004: the client is installed as `forgel-code` from the public `forgel-dev/code` repository, D-005). The documented command must be the installer of the release that actually ships the login-shell PATH handling the README promises, so a reader who copies the line gets the product the text describes.

## User Experience

A reader copies the install line from README.md, pipes it into `sh`, and gets the release installer that writes the marked PATH block and verifies it in a fresh login shell. The same line, with `-s -- --uninstall`, removes it again. Nobody who follows the README lands on an installer from the previous release.

## Roadmap

—

## Goals

- The one-command install path a reader copies from README.md is the release installer of the current release.
- The install, update and uninstall commands in README.md name one and the same release installer URL.
- A stale release tag in any of those three documented commands fails the suite instead of shipping.
- The whole suite is green again, with no test weakened to get there.

## Non-Goals

- Changing `install.sh` behaviour, its PATH handling, its fresh-shell check or its options.
- Changing `install.sh`'s own header comment or its `FORGEL_CODE_TAG` default.
- Assigning, promising, creating or moving a release tag; the release train owns the version (FORGEL.md `## Releases`).
- Adding a versionless `latest` installer URL or teaching `install.sh` to serve one.
- Changing any other README section, the client code, the packaging backend or the other installer tests.
- Weakening any test: the pinned URL is moved to the current tag, not relaxed to a looser substring check.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-004: The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | User decisions log, D-004 (accepted proposal, 2026-11-16 18:34) |
| — | D-005: The second repository is public and lives in the same organization as the first (`forgel-dev`). | User decisions log, D-005 (user, 2026-11-16 21:14) |

## Functional Requirements

- **FR-1**: R1: README.md contains no install-script URL whose ref is `v0.1.0`; the string `/v0.1.0/install.sh` does not appear anywhere in the file.
- **FR-2**: R2: The first command in the first code block of the `## Install` section is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh`.
- **FR-3**: R3: The install command in the `### Update` section is byte-identical to the command in R2.
- **FR-4**: R4: The command in the `### Uninstall` section is exactly `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh | sh -s -- --uninstall`.
- **FR-5**: R5: Every install-script URL anywhere in README.md is the same URL as R2 — one owner/repository path, one ref, one script path.
- **FR-6**: R6: The test suite contains a guard, in `tests/test_readme_install.py`, that reads README.md from the repository root and fails when any of the commands in R2, R3 and R4 names a different tag or a different install-script URL; it is part of the default suite invocation and needs no environment variable or marker.
- **FR-7**: R7: The pinned install-URL assertion in `tests/test_cli.py` (`ReadmeTest::test_readme_has_a_pinned_install_command`) expects the same release tag as R2 instead of `v0.1.0`, and still asserts a pinned install command rather than a weaker substring presence check.
- **FR-8**: R8: `python -m pytest -q` exits 0 on the whole suite.
- **FR-9**: R9: CHANGELOG.md gains one English entry inside the `## [Unreleased]` section describing the documentation fix and the guard.
- **FR-10**: R10: `tests/test_readme_install.py` builds all three expected commands from a single release-tag constant, so the next release moves one constant instead of three literals.

## Technical Requirements

- All committed artifacts are English (AGENTS.md project rule).
- Never weaken a test to make it pass (repository code AGENTS.md): the `tests/test_cli.py` assertion is moved to the current tag, not deleted or broadened.
- A published tag is immutable and agents do not assign or rewrite release versions or tags (FORGEL.md `## Releases`, `## Release Rules`); this task only changes which existing release the documentation names.
- The suite must stay within the 120-second bound the README `## Tests` section states, and must keep running without network access: the installer scenarios install from a local checkout with `PIP_NO_INDEX=1`.
- The change is one logical commit, English and imperative, with `git commit -s` (project Change Workflow).
- No tool attribution lines and no session references in the commit.

## User Stories

- As someone installing Forgel Code, I want the README's install line to fetch the current release installer so that I get the login-shell PATH handling the surrounding text describes.
- As someone removing Forgel Code, I want the README's uninstall line to run the same release installer with `--uninstall` so that the block and the launcher it wrote are both removed.
- As a maintainer, I want the suite to fail when a documented install command names an older release so that a stale line cannot ship.

## Tests

- A1: `python -c import pathlib,sys
text=pathlib.Path('README.md').read_text(encoding='utf-8')
stale='/v0.1.0/install.sh'
print('stale occurrences:', text.count(stale))
sys.exit(1 if stale in text else 0)`
- A2: `python -m pytest -q tests/test_readme_install.py`
- A3: `python -c import pathlib,subprocess,sys
p=pathlib.Path('README.md')
orig=p.read_text(encoding='utf-8')
files=['tests/test_readme_install.py','tests/test_cli.py']
run=lambda: subprocess.run([sys.executable,'-m','pytest','-q',*files],capture_output=True).returncode
base=run()
lines=orig.splitlines(True)
hits=[i for i,l in enumerate(lines) if 'forgel-dev/code/v0.1.1/install.sh' in l]
caught=[]
try:
    for i in hits:
        mutated=list(lines)
        mutated[i]=mutated[i].replace('/v0.1.1/','/v0.1.0/')
        p.write_text(''.join(mutated),encoding='utf-8')
        caught.append(run()!=0)
finally:
    p.write_text(orig,encoding='utf-8')
print('baseline=%d documented_lines=%d caught=%s' % (base,len(hits),caught))
sys.exit(0 if base==0 and len(hits)>=3 and all(caught) else 1)`
- A4: `python -c import pathlib,sys
text=pathlib.Path('tests/test_cli.py').read_text(encoding='utf-8')
stale='v0.1.0/install.sh'
print('stale pin occurrences:', text.count(stale))
sys.exit(1 if stale in text else 0)`
- A5: `python -m pytest -q`
- A6: `python -c import pathlib,sys
text=pathlib.Path('CHANGELOG.md').read_text(encoding='utf-8')
start=text.find('## [Unreleased]')
end=text.find('## [0.1.0]')
ok=start!=-1 and end!=-1 and start<end
section=text[start:end] if ok else ''
found='README' in section and ('install' in section.lower())
print('unreleased entry mentions README install docs:', found)
sys.exit(0 if found else 1)`
- A7: `python -c import sys,urllib.error,urllib.request
url='https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh'
try:
    with urllib.request.urlopen(url,timeout=15) as response:
        print('resolved', response.status)
        sys.exit(0 if response.status==200 else 1)
except urllib.error.HTTPError as error:
    print('http error', error.code)
    sys.exit(1)
except OSError as error:
    print('network unavailable, url not verified:', error)
    sys.exit(0)`
- Command: `python -m pytest -q`

## Acceptance Criteria

- **AC-1**: A1: `grep`-style inspection of README.md finds no `/v0.1.0/install.sh`.
- **AC-2**: A2: The `## Install` install command, the `### Update` command and the `### Uninstall` command are the release installer of the tag `v0.1.1`, and the uninstall command is the install command plus ` | sh -s -- --uninstall`.
- **AC-3**: A3: `tests/test_readme_install.py` exits 1 when the tag in the `## Install` command is changed to another tag, when the tag in the `### Update` command is changed, and when the tag in the `### Uninstall` command is changed.
- **AC-4**: A4: `tests/test_cli.py` contains no install-script expectation naming `v0.1.0`.
- **AC-5**: A5: `python -m pytest -q` exits 0 on the whole suite.
- **AC-6**: A6: The `## [Unreleased]` section of CHANGELOG.md carries an entry that names the README install/uninstall documentation and its guard.
- **AC-7**: A7: When the network is reachable, `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh` answers HTTP 200.

## Scope Boundaries

- README.md: the `## Install` install command, the `### Update` install command and the `### Uninstall` command are brought to the current release installer, with no other release tag left anywhere in the file's install-script URLs.
- tests/test_readme_install.py: the README guard keeps (or gains) an assertion that the install, update and uninstall commands are the release installer, built from one release-tag constant.
- tests/test_cli.py: the pinned install-URL assertion that still names the old tag is updated to the same release tag.
- CHANGELOG.md: one English entry under `## [Unreleased]` for the documentation fix and its guard.
- Changing `install.sh` behaviour, its PATH handling, its fresh-shell check or its options.
- Changing `install.sh`'s own header comment or its `FORGEL_CODE_TAG` default.
- Assigning, promising, creating or moving a release tag; the release train owns the version (FORGEL.md `## Releases`).
- Adding a versionless `latest` installer URL or teaching `install.sh` to serve one.
- Changing any other README section, the client code, the packaging backend or the other installer tests.
- Weakening any test: the pinned URL is moved to the current tag, not relaxed to a looser substring check.

## Risks

- If tag `v0.1.1` is not yet published, the documented URL answers 404 until the release train publishes it; this task must not create or move the tag (FORGEL.md `## Releases`), so the pin can only be corrected by a later change or by the release itself.
- If the release train selects a different next version, the pin in README.md and in both test files moves with that release; a hardcoded literal kept in three places would drift — hence R10.
- The previous specification was rejected because it forbade touching `tests/test_cli.py` while requiring the `v0.1.0` string to leave README.md; that contradiction is resolved here by putting `tests/test_cli.py` in scope (R7). Any implementation that leaves the signed expectation in place cannot reach A5.
- `install.sh`'s own header comment and its `FORGEL_CODE_TAG` default still name `v0.1.0`; the README fix does not address them, and they are a separate follow-up rather than a hidden part of this task.
- Requiring the guard to fail for each of the three documented commands (A3) can surface an over-broad or under-broad guard: a guard that only reads the `## Install` section passes A2 but fails A3.
- A7 needs outbound network access; on an offline machine the check reports the URL as unresolved and passes, so A7 never turns an offline build red, but it also proves nothing there.

## Open Questions

- None.

## Affected Files

- README.md
- tests/test_cli.py
- tests/test_readme_install.py
- CHANGELOG.md

## Assumptions

- The current release installer tag is `v0.1.1`, as already encoded by `tests/test_readme_install.py` (`INSTALL_TAG = "v0.1.1"`); keeping it is the minimal change that makes README and suite agree, and the suite itself rejects a versionless URL (`TAG_RE` requires exactly one tag per URL).
- `tests/test_cli.py` holds the stale expectation in `ReadmeTest::test_readme_has_a_pinned_install_command`; the exact line number is not asserted here, only that no `v0.1.0` install-script expectation survives in that file.
- A CHANGELOG entry is repo convention for a user-visible documentation change; `## [Unreleased]` already exists and is where it belongs.
- The network reachability of the documented URL is not a suite dependency: the suite is offline by design, so A7 is verified as a separate, network-optional check.

## Related Documents

- README.md
- tests/test_readme_install.py
- tests/test_cli.py
- install.sh
- CHANGELOG.md
- releases/0.1.0/release.md
- FORGEL.md
- AGENTS.md

## Revision History

- v1 — initial specification; it forbade changes to tests/test_cli.py while requiring the v0.1.0 install-script string to leave README.md, which made R1 and the green-suite acceptance criterion unsatisfiable.
- v2 — concrete defect fixed: tests/test_cli.py is now in scope (R7), the pinned-URL assertion there is required to move to the same release tag as the README guard, an acceptance criterion (A4) and a command check cover the absence of the old pin, and a risk records the resolved contradiction. The guard-tightening requirement survives unchanged (R6, A3).

## External Dependencies

- **GitHub raw content URL** — mode `unknown`; interface: `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>` serves the file at `<path>` from the commit or tag `<ref>` of the public repository `<owner>/<repo>`; the README pipes such a URL into `sh`. The task uses `https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh`.; docs: GitHub Docs: raw.githubusercontent.com raw content URL form (no local copy in the repository); the repository itself is `forgel-dev/code` per D-005.; evidence: —
