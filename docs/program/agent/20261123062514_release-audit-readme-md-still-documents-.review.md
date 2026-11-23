# Task Review: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-23T15:32:28+00:00

## Summary

The README install, update and uninstall commands now all name one and the same install-script URL, the `v0.1.0/install.sh` string is gone, the README diff touches only the URL lines, and QA reports the suite green. But the chosen URL is the default-branch script `https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`, which carries no version selector at all. The contract's R3 is explicit: the URL must point at the release whose behaviour the documentation describes (the v0.1.1 release named by the audit finding), not at an earlier tag, and the version selector must appear exactly once. The delivered change instead pins the documentation to `main` forever, and the guard test goes further: it rejects every tag-pinned install URL and inverts the pre-existing `test_readme_has_no_default_branch_install` protection into `test_readme_has_no_tag_pinned_install`, so the suite now enforces the opposite of R3 and would block the correct fix on the next release. Two extra artefacts also land outside the declared change set: a CHANGELOG entry that states the commands point at the `v0.1.1` installer while the README in fact points at `main` (a factually wrong record), and a `tests/test_probe_canonical_url.py` attributed to the task that does not exist in the tree. R1, R2, R4, R5 (vacuously, since no tag is named), R7 and A1, A4, A6, A5, A7 hold; R3, R6 (weakened/inverted assertions), R9/A8 (change-set scope) and A2/A3 do not.

## Requirements

- R1: README.md contains no reference to the `.../v0.1.0/install.sh` URL anywhere.: pass — README.md now names only `.../main/install.sh`; neither the install, update nor uninstall section mentions v0.1.0. A1 passes.
- R2: The README install command and uninstall command reference exactly the same install-script URL, and that URL is the only install-script URL in README.md.: pass — Install, update and uninstall all carry `curl -fsSL https://raw.githubusercontent.com/forgel-dev/code/main/install.sh`; no second install-script URL appears (the v0.1.1 source tarball line in `## Tests` is not an install.sh URL).
- R3: The install-script URL points at the release whose behaviour the documentation describes (the current v0.1.1 release), not an earlier tag; the version selector appears exactly once in the URL.: fail — The delivered URL is `.../code/main/install.sh` — a default-branch path with zero version selectors, not the v0.1.1 release path. Commit 81668fd moved the README from `v0.1.1` (2e55f34-era state) to `main`, i.e. away from the release the contract names. This is the central requirement and it is not met.
- R4: No other README content changes; only the URL itself.: pass — The README hunk set changes exactly the three `curl -fsSL <url> | sh` lines; prose, options, section structure and command shape are untouched.
- R5: If the chosen URL names an unpublished release tag, the README names the newest published tag and the discrepancy is recorded.: pass — Vacuous in the delivered state: the URL names no tag at all. That is exactly why R3 fails, but the R5 branch itself is not triggered.
- R6: The suite passes and tests/test_readme_install.py is extended to assert R1 and R2 without weakening any existing assertion.: fail — The guard is extended (test_no_stale_install_script_url, test_install_and_uninstall_share_the_install_script_url) and QA shows it green, but the change also deletes `tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install` and replaces it with `test_readme_has_no_tag_pinned_install`, which asserts the inverse (the README must contain NO tag-pinned URL and must contain `main`). The suite no longer protects against a default-branch install and now would fail a correct release-pinned README, so existing assertions are weakened rather than preserved.
- R7: No change to install.sh, forgel_code/*, pyproject.toml or the release directories.: pass — The committed diff touches only README.md, CHANGELOG.md, tests/test_cli.py and tests/test_readme_install.py; install.sh and tests/test_install.py edit the worktree but stay uncommitted as escalated.
- A2 (review-only): The documented install command references the release installer and any version matches the newest CHANGELOG release.: fail — The install line references the default-branch script, not a release installer, and carries no version that could match CHANGELOG.md's `[0.1.0] - 2026-11-20` / v0.1.1 release.
- A3 (review-only): The documented uninstall command references the release installer on the same terms as A2.: fail — Same `main/install.sh` URL, so the uninstall command also documents a branch script rather than a release installer.
- A5 (review-only): The guard test fails against a README documenting a superseded install path.: pass — `test_stale_install_script_url_is_rejected` and `assert_single_install_script_url`'s STALE_INSTALL_PATH check do reject a v0.1.0 README, and the negative tests run. The rejection is only a side effect of forbidding every tag, which is the R3 defect noted above.
- A7 (review-only): The guard test makes no network call, spawns no external binary and calls no git.: pass — tests/test_readme_install.py imports only `re`, `unittest` and `pathlib`, reads README.md from disk and does pure text parsing.
- A8 / R9 (review-only): The change set is exactly README.md, tests/test_readme_install.py and tests/test_cli.py, with unrelated worktree changes left uncommitted.: fail — Unrelated worktree changes were correctly left uncommitted (install.sh, tests/test_install.py, tests/test_check_cleanup.py), but the committed set is not the declared three: CHANGELOG.md was committed (aff039d) beyond the declared paths, and tests/test_probe_canonical_url.py was also attributed/committed yet does not exist in the tree.
- A1: A grep for `v0.1.0/install.sh` in README.md returns nothing (QA check).: pass — QA reports exit 0 and the file confirms no such string.
- A4: The README diff contains only URL changes (QA check).: pass — Only the three URL literals differ; command shape, options and sections are unchanged.
- A6: `python -m pytest` passes for the whole repository (QA check).: pass — QA reports the full suite green; the verdict here rests on requirement compliance, not on rerunning it.
- Change-set quality: committed artefacts are internally consistent.: fail — The CHANGELOG entry says the README now points at the current `v0.1.1` release installer, while the README points at `main`; the record contradicts the product state, and a `main`-pinned install means a future release's docs silently ship unreleased code.

## Blocking

- R3/A3 not met: README documents `.../code/main/install.sh` — a default-branch URL with no version selector — instead of the v0.1.1 release installer the contract requires.
- R6 weakened/inverted protection: `tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install` is replaced by `test_readme_has_no_tag_pinned_install`, and tests/test_readme_install.py adds `TAG_PATH_RE`, so the suite now forbids exactly the release-pinned URL R3 demands and would fail a correct README.
- A8/R9 scope violation: CHANGELOG.md is committed although the declared change set is README.md, tests/test_readme_install.py and tests/test_cli.py only.
- Internally inconsistent artefact: the committed CHANGELOG entry claims the README commands point at the `v0.1.1` release installer, which the committed README does not do.
- Attributed file tests/test_probe_canonical_url.py does not exist in the repository, so the attributed change set and the tree disagree.

## Test Removals

- line:def test_rejects_the_stale_install_script_url(self) -> None:
- line:def test_rejects_install_and_uninstall_on_different_tags(self) -> None:
- line:def test_readme_has_no_default_branch_install(self) -> None:

- tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_a_pinned_install_command
- tests/test_readme_install.py::ReadmeInstallTest::test_one_update_line_and_one_uninstall_line: replaced -> tests/test_readme_install.py::ReadmeInstallTest::test_one_update_line_and_one_uninstall_line
- tests/test_cli.py::ReadmeTest::test_readme_has_no_default_branch_install: replaced -> tests/test_cli.py::ReadmeTest::test_readme_has_no_tag_pinned_install
