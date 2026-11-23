# Session State: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Session: 2
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

- README.md
- install.sh
- tests/test_check_cleanup.py
- tests/test_install.py
- tests/test_probe_release_url.py
- tests/test_probe_tags.py
- tests/test_readme_install.py

## Actions

- run: ['git', 'log', '--oneline', '--decorate', '-10']
- run: ['git', 'for-each-ref', 'refs/tags']
- recall
- read_file: README.md
- recall
- run: ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code} v0.1.1\n', 'https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh']
- recall
- read_file: tests/test_readme_install.py
- run: ['git', 'diff', '-U0', '--', 'README.md']
- run: ['git', 'diff', '-U0', '--', 'tests/test_cli.py']
- read_file: tests/test_cli.py
- read_file: CHANGELOG.md
- run: ['git', 'status', '--short']
- read_file: README.md
- run: ['git', 'diff', '-U2', '--', 'README.md', 'tests/test_readme_install.py']
- read_file: tests/test_cli.py
- run: ['git', 'log', '--oneline', '--decorate', '-10']
- recall
- run: ['git', 'restore', '--source=HEAD^', '--worktree', '--', 'tests/test_cli.py']
- run: ['git', 'for-each-ref', 'refs/tags']

## Commands

- `['git', 'status', '--short']` -> exit 0
- `['git', 'log', '--oneline', '--decorate', '-10']` -> exit 0
- `['git', 'diff', '-U0', '--', 'README.md']` -> exit 0
- `['git', 'diff', '-U0', '--', 'tests/test_cli.py']` -> exit 0
- `['git', 'status', '--short']` -> exit 0
- `['git', 'diff', '-U2', '--', 'README.md', 'tests/test_readme_install.py']` -> exit 0
- `['git', 'log', '--oneline', '--decorate', '-10']` -> exit 0

## Recent Observations

- recall: step 1 [read_file]
- run git restore '--source=HEAD^' --worktree -- tests/test_cli.py -> exit ?
- run git for-each-ref refs/tags -> exit ?

## Next Step

Continue from the current repository state and the changed files.
