# Session State: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- R1: README.md contains no reference to the `v0.1.0` install script URL (`.../v0.1.0/install.sh`), in the install command or anywhere else.
- R2: The README install command and the README uninstall command reference exactly the same install-script URL, and that URL is the only install-script URL in README.md.
- R3: The install-script URL in README.md points at the release whose behavior the documentation describes (the current release, i.e. the v0.1.1 release referenced by the audit finding), not at an earlier tag. The version selector appears exactly once in the URL and both commands inherit it.
- R4: No other README content changes: the surrounding prose, command shape (`curl -fsSL <url> | bash`), options and section structure stay as they are, except for the URL itself.
- R5: If the chosen URL names a release tag that is not yet published at commit time, the README names the newest published tag instead and the discrepancy is recorded in the task report; README must never advertise a tag that does not resolve.
- R6: The existing test suite passes, and tests/test_readme_install.py either already fails on the stale URL (and therefore now passes) or is extended to assert R1 and R2 without weakening any existing assertion.
- R7: No change to install.sh, forge_code/*, pyproject.toml or the release directories is introduced by this task.

## Acceptance Criteria

- A1: A grep for `v0.1.0/install.sh` in README.md returns nothing.
- A2: All install-script URLs found in README.md are identical, and there are at least two of them (one in the install command, one in the uninstall command).
- A3: The version selector in the README install-script URL equals the version documented as the current release, and the URL is fetchable (HTTP 200) from the public repository.
- A4: The README diff contains only URL changes, reviewable as a small, self-contained change.
- A5: `python -m pytest` passes for the whole repository, including tests/test_readme_install.py.
- A6: `git diff --name-only` lists only README.md and, optionally, tests/test_readme_install.py.

## Constraints

- none

## Assumptions

- none

## Files Changed

- CHANGELOG.md
- README.md
- install.sh
- tests/test_check_cleanup.py
- tests/test_cli.py
- tests/test_install.py
- tests/test_readme_install.py

## Actions

- run: ['git', 'status', '--short']
- run: ['git', 'diff', '--name-only']
- run: ['git', 'diff', '-U0', '--', 'README.md']
- run: ['git', 'diff', '-U1', '--', 'tests/test_cli.py', 'CHANGELOG.md']
- read_file: tests/test_cli.py
- read_file: tests/test_readme_install.py
- read_file: README.md
- read_file: CHANGELOG.md
- run: ['git', 'diff', '--stat']
- run: ['git', 'diff', '-U0', '--', 'tests/test_cli.py', 'CHANGELOG.md', 'install.sh', 'tests/test_install.py']
- run: ['git', 'diff', '-U0', '--', 'install.sh', 'tests/test_install.py']
- run: ['git', 'diff', '-U0', '--', 'CHANGELOG.md']
- run: ['git', 'diff', '-U0', '--', 'tests/test_cli.py']
- run: ['git', 'diff', '-U2', '--', 'tests/test_cli.py']
- run: ['git', 'diff', '-U3', '--', 'tests/test_cli.py']
- run: ['git', 'diff', '-U3', '--', 'tests/test_cli.py', 'CHANGELOG.md']
- run: ['git', 'diff', '--', 'tests/test_cli.py']
- run: ['git', 'diff']
- run: ['git', 'status']
- recall

## Commands

- `['git', 'diff', '-U0', '--', 'tests/test_cli.py', 'CHANGELOG.md', 'install.sh', 'tests/test_install.py']` -> exit 0
- `['git', 'diff', '-U0', '--', 'install.sh', 'tests/test_install.py']` -> exit 0
- `['git', 'diff', '-U0', '--', 'CHANGELOG.md']` -> exit 0
- `['git', 'diff', '-U0', '--', 'tests/test_cli.py']` -> exit 0
- `['git', 'diff', '-U2', '--', 'tests/test_cli.py']` -> exit 0
- `['git', 'diff', '-U3', '--', 'tests/test_cli.py']` -> exit 0
- `['git', 'diff', '-U3', '--', 'tests/test_cli.py', 'CHANGELOG.md']` -> exit 0
- `['git', 'diff', '--', 'tests/test_cli.py']` -> exit 0
- `['git', 'diff']` -> exit 0
- `['git', 'status']` -> exit 0

## Recent Observations

- run git diff -> exit 0
- run git status -> exit 0
- recall: step 1 [read_file]

## Next Step

Continue from the current repository state and the changed files.
