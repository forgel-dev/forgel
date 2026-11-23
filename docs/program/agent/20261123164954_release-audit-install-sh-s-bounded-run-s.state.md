# Session State: Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out

- Task: `20261123164954_release-audit-install-sh-s-bounded-run-s`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- When a verification command does not finish within its time limit, the installer must fail the installation and its failure must state that the time limit was exceeded.
- That failure must occur regardless of whether the command ends just before, at, or just after the moment the limit elapses.
- A verification command that finishes within its limit and reports success must let the installation continue.
- A verification command that finishes within its limit and reports failure must be reported as that failure and must not be presented as a time-limit failure.
- No situation may exist in which the installation is reported as successful for a verification run that exceeded its limit.
- The installer's additional waiting for the outcome of a verification run after the limit has passed must be finite and short.
- The verification step must leave no residual processes and no temporary working artifacts behind, including when the limit is exceeded.
- The project's test suite must contain a regression test whose verification command ends just after the limit and which asserts that the installation fails with a message naming the limit.
- The behavior of the installer for verification commands that finish well within their limit must remain unchanged.
- All project artifacts are in English.

## Acceptance Criteria

- A verification command that ends just after the time limit makes the installation fail with a message naming the time limit.
- A verification command that succeeds well within the time limit lets the installation complete.
- A verification command that fails with its own error within the time limit produces that error and not a time-limit message.
- No run in which the time limit elapsed is reported as a successful installation.
- The regression test for the just-after-limit case exists and passes, and the full test suite passes.
- The pre-existing tests for within-limit verification pass without being weakened, showing that behavior for those cases is unchanged.
- After an exceeded-limit run, no verification processes remain and no temporary working artifacts are left behind.
- Every artifact produced is in English.

## Constraints

- One change that a single agent can finish and verify on its own.
- The time limit and its default value stay as they are.
- No existing test may be weakened to make the new behavior pass.
- Project and repository instructions and recorded user decisions are binding.
- A verification command running past its limit must continue to fail the installation; only the correctness of that verdict changes.

## Assumptions

- none

## Files Changed

- install.sh
- tests/test_install_timeout_verdict.py

## Actions

- run: ['git', 'status', '--porcelain', '--untracked-files=all']
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- read_file: tests/test_install_timeout_verdict.py
- run: ['python', '-m', 'pytest', '-q']
- read_file: tests/test_install_timeout_verdict.py
- read_file: install.sh
- recall

## Commands

- `['git', 'status', '--porcelain', '--untracked-files=all']` -> exit 0
- `['python', '-m', 'pytest', '-q']` -> exit 124

## Recent Observations

- read_file tests/test_install_timeout_verdict.py: tests/test_install_timeout_verdict.py: lines 30-149 of 178
- read_file install.sh: install.sh: lines 1-20 of 1024
- recall: step 1 [read_file]

## Next Step

Continue from the current repository state and the changed files.
