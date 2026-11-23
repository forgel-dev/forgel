# Task Review: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T16:46:01+00:00

## Summary

The attributed change does what R1-R7 ask. README.md now points the install, update and uninstall commands at the single version-pinned installer URL https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh, with the version selector appearing once per URL and the surrounding prose, command shape and section structure untouched. The guard in tests/test_readme_install.py was rewritten to require exactly the current release URL, to fail for the stale v0.1.0 script anywhere in the page, for a divergent tag and for a versionless default-branch URL, and it now checks that install, update and uninstall all use one and the same URL; the fixture was updated consistently. tests/test_cli.py's ReadmeTest was moved from the old v0.1.0 assertion to the same v0.1.1 URL, which is required for the suite to stay green, and CHANGELOG.md records the fix as the release-record reconciliation. No pre-existing test was lost: the removals flagged in the commit series are intra-range churn whose replacements (test_stale_install_script_url_is_rejected, test_divergent_install_script_url_is_rejected, test_default_branch_install_script_url_is_rejected, test_a_missing_install_script_url_is_rejected) are present in the final state, and test_readme_has_no_default_branch_install still exists. No install.sh, forgel_code/*, pyproject.toml or release-directory change is committed; the install.sh, tests/test_install.py and tests/test_check_cleanup.py worktree items are escalated and unattributed. QA passed, and the review-only criteria hold.

## Requirements

- R1: README.md contains no reference to the v0.1.0 install script URL.: pass — The final README.md has only v0.1.1 install-script URLs; no v0.1.0/install.sh reference remains.
- R2: The install and uninstall commands reference exactly the same install-script URL, and that URL is the only install-script URL in README.md.: pass — Install, update and uninstall all use https://raw.githubusercontent.com/forgel-dev/code/v0.1.1/install.sh; the tarball URL in the Tests section is not an install-script URL. The guard asserts set(urls) == {INSTALL_URL} with at least two occurrences.
- R3: The install-script URL points at the current release (v0.1.1) and the version selector appears once per URL.: pass — The URL uses the v0.1.1 selector once; both commands inherit it from the same URL. QA's environment checks passed and the README references v0.1.1 consistently.
- R4: No other README content changes; prose, command shape and section structure stay as they are.: pass — The README diff is exactly two lines, each changing only the URL inside the unchanged `curl -fsSL <url> | sh` / `| sh -s -- --uninstall` commands.
- R5: README must never advertise a tag that does not resolve; if v0.1.1 is not published, the newest published tag is used and the discrepancy is recorded.: pass — The task contract names v0.1.1 as the current release referenced by the audit, and QA's environment checks passed on the shipped URL; no unpublished tag is advertised.
- R6: The existing test suite passes, and tests/test_readme_install.py is extended to assert R1 and R2 without weakening any existing assertion.: pass — The guard was strengthened (single URL, current-release tag, stale/divergent/mutable rejection); tests/test_cli.py's ReadmeTest was moved to the same URL so the suite stays green; QA's pytest/unittest and environment checks passed. No existing assertion was weakened.
- R7: No change to install.sh, forgel_code/*, pyproject.toml or the release directories.: pass — The committed diff touches only README.md, CHANGELOG.md, tests/test_cli.py and tests/test_readme_install.py. The install.sh, tests/test_install.py and tests/test_check_cleanup.py worktree items are escalated and not committed.
- Review-only: The guard fails against a documentation variant naming a superseded release and against a variant naming no release.: pass — test_stale_install_script_url_is_rejected and test_rejects_a_stale_url_anywhere_in_the_document cover the superseded case; test_default_branch_install_script_url_is_rejected and test_a_missing_install_script_url_is_rejected cover the versionless/no-URL case.
- Review-only: The documented install instruction identifies the current published release rather than an in-development location.: pass — README.md's install command uses the v0.1.1 installer URL, not main/ or another mutable location.
- Review-only: The documented uninstall and update instructions carry the same release identifier as the install instruction.: pass — Both the update and uninstall commands use the same v0.1.1 install-script URL; the guard's UPDATE_COMMAND/UNINSTALL_COMMAND enforce this.
- Review-only: The release record and the documentation agree on the release identifier and instruction form.: pass — The CHANGELOG.md entry added under Unreleased states that the README install, update and uninstall commands point at the current v0.1.1 installer and share one install-script URL, matching the README's v0.1.1 form; the committed release directories are untouched per R7.
- A6/AC-7: The delivered result is confined to the documentation page, the guard and the release record; unrelated pending changes remain undelivered and unattributed.: pass — The committed set is README.md (documentation page), tests/test_readme_install.py plus tests/test_cli.py (the README guard) and CHANGELOG.md (the release record). The install.sh/test_install.py/test_check_cleanup.py worktree items are escalated, not committed. QA's delivery-scope acceptance check passed.

## Blocking

- none

## Test Removals

- line:def test_rejects_the_stale_install_script_url(self) -> None:
- line:def test_rejects_install_and_uninstall_on_different_tags(self) -> None:
- line:def test_readme_has_no_tag_pinned_install(self) -> None:
- line:def test_no_tag_pinned_install_script_url(self) -> None:
- line:def test_another_branch_install_script_url_is_rejected(self) -> None:

- tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command
- tests/test_readme_install.py::ReadmeInstallTest::test_one_update_line_and_one_uninstall_line: replaced -> tests/test_readme_install.py::ReadmeInstallTest::test_one_update_line_and_one_uninstall_line
- tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_no_tag_pinned_install
- tests/test_cli.py::ReadmeTest::test_readme_has_no_tag_pinned_install: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install
