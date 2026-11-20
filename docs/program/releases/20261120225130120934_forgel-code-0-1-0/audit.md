# Release audit 20261120225130120934_forgel-code-0-1-0

- Round: 1
- Verdict: fail
- At: 2026-11-20T22:52:55+00:00

## Summary

The release is not auditable as shipped: the base..head diff for code changes only tests/test_extras.py. The task claims and requires changes to pyproject.toml, _build_backend.py, README.md, and tests/test_readme_install.py, but those files are absent from the diff. The required test-extra implementation and README evidence is therefore missing, and R13's new no-editable-install assertion is unverified.

## Findings

- [critical] code: The actual change set modifies only tests/test_extras.py. It does not include the pyproject.toml, _build_backend.py, or README.md changes that the task lists and R1/R3/R8 require, so the release does not evidence the declared test extra, the emitted Provides-Extra/Requires-Dist metadata, or the README [test] install instructions. The review's claim that those files changed is contradicted by the repository diff. — Include the missing implementation and README changes in the release diff, or provide head-state evidence that they already exist and correct the task/release records; then rerun the packaging tests.
- [major] code: R13 requires tests/test_readme_install.py to gain an assertion that no editable-install instruction appears anywhere in README.md. That file is not in the change set and no test output identifies the new assertion, leaving the required guard unverified. — Add the no-editable-install assertion to tests/test_readme_install.py, include it in the release diff, and run the README install tests.
