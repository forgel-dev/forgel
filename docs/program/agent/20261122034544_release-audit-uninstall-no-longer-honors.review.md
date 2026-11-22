# Task Review: Release audit: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block

- Task: `20261122034544_release-audit-uninstall-no-longer-honors`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-22T03:55:56+00:00

## Summary

The attributed commit restores override-profile cleanup in `install.sh --uninstall`: a new `uninstall_profile` helper (missing/non-regular file and marker-free file are silent no-ops, removal failure sets status=1) is reused for the six `PROFILE_NAMES` and, when `FORGEL_CODE_PROFILE` is set and non-empty, for that exact path as an additive second step. The refactor preserves the previous standard-name behavior byte for byte, tolerates duplicates (second call sees no marker), does not create files, and keeps the POSIX `sh` contract. `tests/test_install.py` gains an `InstallerProfileOverrideUninstallTest` class exercising the real script under a temporary `$HOME`: override cleanup, a successful install through an override, a failed-install leftover, override-free run, missing override, marker-free override, and an override naming `$HOME/.profile` cleaned exactly once. README documents the override cleanup in both the Options table and the Uninstall paragraph, and CHANGELOG records the fix under `## [Unreleased]` / `### Fixed` above the intact `[0.1.0]` section. No tests were removed or weakened; QA reports all deterministic checks (AC1-AC5, `sh -n`, full suite) green. Only minor, non-blocking observation: the commit subject is the runtime-generated task title rather than an imperative sentence; this is pipeline bookkeeping, not a product defect.

## Requirements

- R1: With `FORGEL_CODE_PROFILE` set and non-empty, `--uninstall` removes the marked block from that exact path in addition to `PROFILE_NAMES`.: pass — The `PROFILE_NAMES` loop is kept and an additive block calls `uninstall_profile "$FORGEL_CODE_PROFILE"` when the variable is non-empty.
- R2: Byte-exact marker removal preserving all other lines and appending no new line.: pass — `remove_profile_block` (awk exact-match markers) is unchanged; the new helper only gates on presence and reports.
- R3: With the variable unset or empty, behavior, output and exit status are as before.: pass — The override step is guarded by `[ -n "${FORGEL_CODE_PROFILE:-}" ]`; the standard loop is behaviorally identical (silent `return 0` replaces `continue`).
- R4: Missing override file or marker-free file exits 0, prints no error and creates no file.: pass — `uninstall_profile` returns 0 on `[ ! -f ]` or absent start marker before any write; covered by two tests.
- R5: Override equal to a standard profile name is cleaned exactly once without content loss and exits 0.: pass — Second call finds no marker and returns silently; test asserts exactly one 'Removed the PATH block' line and preserved tail.
- R6: Block from a completed install and from a failed-verification install is removed by the same uninstall.: pass — Successful-install and failed-fresh-shell tests both drive the real script and assert marker count 1 before and 0 after uninstall.
- R7: `tests/test_install.py` covers override removal after successful and failed install, override-free run, and missing override.: pass — New test class adds exactly these scenarios plus marker-free and duplicate-path cases; QA AC5 passes.
- R8: `README.md` states the override profile is cleaned and README guard tests stay valid.: pass — Options row and Uninstall paragraph updated; install/update/uninstall command lines untouched, and the suite (including guard tests) passes.
- R9: `CHANGELOG.md` records the fix under `## [Unreleased]` / `### Fixed` with `[0.1.0]` intact.: pass — Verified in the current file: Unreleased/Fixed entry precedes the unchanged 0.1.0 section.
- R10: Full suite `python -m unittest discover -s tests` passes.: pass — QA reports AC5/AC8 pass; environment tests also pass.
- Technical: POSIX `sh` (`set -eu`), never reads stdin, passes `sh -n`.: pass — New helper uses only POSIX constructs and no stdin; `sh -n` acceptance check passes.
- Technical: uninstall still works when prefix/launcher are already gone.: pass — Existing `[ -d "$PREFIX" ]` / `[ -e "$LAUNCHER" ]` guards are untouched; profile cleanup is independent of them.
- Technical: no test weakened or removed; no tool attribution lines.: pass — No removals detected in the attributed commit; added tests only. Commit carries Signed-off-by; the `Agent:` subject prefix is runtime bookkeeping, not a product change.
- AC6 (review): README documents override-profile cleanup and remains truthful.: pass — Text states the exact-named file is cleaned, missing/marker-free files are left alone, and builds no file; matches the script.
- AC7 (review): CHANGELOG entry present under Unreleased/Fixed.: pass — Present and English; describes the restored behavior without assigning any version.
- Scope: no changes to profile selection, markers, PATH line, prefix layout, verification, exit codes, or release versioning.: pass — Diff is limited to uninstall cleanup, tests, README and CHANGELOG; no tags or versions touched.

## Blocking

- none

## Test Removals

- none


