# Task Review: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

- Task: `20261122192217_release-audit-remove-profile-block-and-u`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-23T05:17:42+00:00

## Summary

The product fix itself is sound: `has_unclosed_block` guards `remove_profile_block`, so an unterminated `# >>> forgel-code >>>` now leaves the profile byte-identical and writes a diagnostic naming the file and the missing end marker, while a well-formed block, an orphan end marker, and a marker-free file keep their previous correct behaviour; `uninstall_profile` inherits the fix because it delegates to `remove_profile_block`. The regression tests named in the acceptance criteria are present and the QA gate is green. However, the attributed change breaks two explicit task rules: it commits scratch probe test files (`tests/test_zz_probe2.py`, `tests/test_zz_timing_probe.py`) that the specification does not list and that the rules forbid, and it carries unrelated refactors of the shell-detection test harness and of the watchdog test (new `_INSTALL_SCRIPT`/`_STDIN_TAIL` module globals, removed `detection_environment` helper, `FORGEL_CODE_TIMEOUT=1` plus a new stderr assertion in the watchdog case, `test_unknown_shell_writes_profile_and_warns` switched to `self.install()`), which the contract explicitly excludes from this one-logical-change task.

## Requirements

- FR-1: `remove_profile_block` deletes only lines from a start marker through its matching end marker, inclusive.: pass — The existing AWK program is unchanged and still suppresses only the delimited range; the new guard does not alter the well-formed path, and `test_remove_profile_block_removes_only_wellformed_block` passes.
- FR-2: an unterminated start marker leaves the file content unchanged and does not truncate to EOF.: pass — `has_unclosed_block` returns 0 on an open marker and the function returns 1 before any copy/rewrite; `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged` asserts the bytes are identical.
- FR-3: the unbalanced case emits a stderr diagnostic naming the file and the missing end marker.: pass — The message interpolates `$profile` and `$MARKER_END`; the test asserts both appear in stderr.
- FR-4: an orphan end marker with no preceding start marker is preserved as user content.: pass — The `grep -Fq "$MARKER_START"` early return plus the AWK's marker handling leave such a line intact; `test_remove_profile_block_preserves_orphan_end_marker` passes.
- FR-5: every non-block line appears in the output in order and byte-identical, including blank lines and trailing content.: pass — Covered by the byte-stability tests and by `test_remove_profile_block_removes_only_wellformed_block`, which keeps surrounding lines and order.
- FR-6: `uninstall_profile` inherits the corrected removal behaviour.: pass — `uninstall_profile` removes the block through `remove_profile_block`, so the guard applies to the uninstall path exercised by the tests.
- FR-7: two installs then an uninstall leave exactly the pre-install non-forgel-code lines and no markers.: pass — `test_install_rerun_then_uninstall_preserves_profile` builds `RERUN_PROFILE` with a foreign marked block and asserts byte equality plus `_marker_count == 0`.
- FR-8: `remove_profile_block` is idempotent and safe on a marker-free profile.: pass — The marker-free case returns 0 early unchanged and the second well-formed run finds no start marker; `test_remove_profile_block_is_idempotent` passes.
- FR-9: `tests/test_install.py` gains a start-marker-without-end regression that runs the removal path and asserts unrelated content survives.: pass — `InstallerBlockRemovalTest.test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged` runs the real uninstall path and asserts survival of the lines below the marker.
- FR-10 / AC-6: all existing tests still pass, with no weakened or deleted test.: pass — No test removals were detected, the edited assertions are equal or stricter (marker count, stderr content), and the full-suite acceptance check passes.
- Constraint: change only the files the specification lists (`install.sh`, `tests/test_install.py`) and commit no probe, debug or scratch files.: fail — The attributed change also commits `tests/test_zz_probe2.py` and `tests/test_zz_timing_probe.py`, which are probe/scratch files outside the affected-files list, later removed again in a follow-up commit.
- Constraint: one logical change; do not refactor unrelated code or the test harness.: fail — `tests/test_install.py` is refactored well beyond the block-removal scope: module-level `_INSTALL_SCRIPT`/`_STDIN_TAIL`, removal of the `detection_environment` helper, reworked `InstallerShellDetectionTest` cases, the watchdog test given `FORGEL_CODE_TIMEOUT=1` plus a new stderr assertion, and `test_unknown_shell_writes_profile_and_warns` switched to `self.install()`.

## Blocking

- Committed scratch/probe test files `tests/test_zz_probe2.py` and `tests/test_zz_timing_probe.py` in the attributed commits: they are outside the specification's affected files and violate the rule never to commit temporary, probe, debug or generated scratch files.
- Unrelated test-harness refactors in `tests/test_install.py` (shell-detection helper removal and rewrites, watchdog test premise change with `FORGEL_CODE_TIMEOUT=1`, module-level script globals), which the contract excludes from this single logical change and the rules forbid refactoring of the test harness.

## Test Removals

- none


