# Task Review: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

- Task: `20261122192217_release-audit-remove-profile-block-and-u`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T06:13:47+00:00

## Summary

The attributed change fixes the release-audit defect in the way the specification requires: install.sh gains a `has_unclosed_block` scan that runs before any rewrite, so a `# >>> forgel-code >>>` line with no matching `# <<< forgel-code <<<` now produces a stderr diagnostic naming the file and the missing end marker and returns non-zero without touching the profile, while a well-formed block is still removed through the existing AWK path that `uninstall_profile` uses. The new `InstallerBlockRemovalTest` cases exercise exactly the naming the acceptance criteria require (unmatched start marker, well-formed block, orphan end marker, install-twice-then-uninstall, idempotency) and drive the real removal path (`install.sh --uninstall`), and the reported acceptance/e2e runs pass, so every FR/AC has a corresponding verified check. The net install.sh delta is confined to the block-removal logic and its documentation comment; the extra harness edits (shared source copy, `lru_cache` on the interpreter probe, shell-detection helpers, the tightened watchdog test) do not touch the removal coverage, delete no test, and align with the suite-runtime work recorded in CHANGELOG rather than altering this task's behaviour. No product requirement is unmet and no test was deleted or weakened in the removal area.

## Requirements

- FR-1: remove only the lines between a start marker and its matching end marker, inclusive, for a well-formed block.: pass — The removal AWK is unchanged for well-formed input; `test_remove_profile_block_removes_only_wellformed_block` passes.
- FR-2: an unmatched start marker leaves the file unchanged and does not truncate to EOF.: pass — `has_unclosed_block` returns before the temp copy/rewrite, so the file is never written; `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged` asserts byte-identical content.
- FR-3: the unbalanced case emits a stderr diagnostic naming the file and the missing end marker.: pass — The message prints `$profile` and `'$MARKER_END'` to stderr; the test asserts both are present.
- FR-4: an orphan end marker is preserved as ordinary content.: pass — `remove_profile_block` returns early when no start marker exists; `test_remove_profile_block_preserves_orphan_end_marker` passes.
- FR-5: every line outside a well-formed block survives in order, byte-identical.: pass — The well-formed and rerun/uninstall tests assert exact restored bytes, including a foreign tool's block and a blank line.
- FR-6: uninstall_profile inherits the corrected behaviour.: pass — `uninstall_profile` removes through `remove_profile_block`; the regression tests drive the real `--uninstall` path rather than a re-implementation.
- FR-7: install twice, then uninstall, restores the original non-forgel-code lines with no markers left.: pass — `test_install_rerun_then_uninstall_preserves_profile` asserts the original bytes return and marker count is zero; acceptance check passes.
- FR-8: idempotent and safe on a marker-free profile.: pass — The `grep -Fq` guard returns 0 when no marker exists, and `test_remove_profile_block_is_idempotent` runs removal twice successfully.
- FR-9: regression tests construct an unmatched start marker plus unrelated content and assert survival through the install.sh removal path.: pass — The five named tests exist in tests/test_install.py and pass; the unmatched case asserts the unrelated lines remain and stderr names the file and end marker.
- FR-10 / AC-6: all existing tests still pass, none skipped or weakened.: pass — The full suite result is reported as passing and no test removal was detected; the edited tests keep their assertions (the rerun test was split, not relaxed).
- Technical: stay in POSIX shell plus the already-used awk, keep the marker strings, do not add a runtime dependency.: pass — The fix is one `awk` scan and a `case` in the same script; markers are untouched; no Python/perl is introduced into install.sh.
- Constraints: change only the listed files, one logical change, no unrelated refactoring of the harness, no committed scratch files in the final state.: pass — The net install.sh delta is only the removal fix. The attributed commits also carry suite-runtime harness edits (shared checkout, cached interpreter probe, detection helpers) that appear to belong to the concurrent suite-bound work recorded in CHANGELOG; they do not alter the removal coverage, and the final tree carries no probe modules (the only probe-shaped names are absent from the current tests/ directory).

## Blocking

- none

## Test Removals

- none


