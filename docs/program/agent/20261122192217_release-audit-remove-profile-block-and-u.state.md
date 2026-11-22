# Session State: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

- Task: `20261122192217_release-audit-remove-profile-block-and-u`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- `remove_profile_block` must delete lines only between a `# >>> forgel-code >>>` line and its matching `# <<< forgel-code <<<` line, inclusive, when the start marker precedes the end marker.
- If a `# >>> forgel-code >>>` line has no matching `# <<< forgel-code <<<` line after it, `remove_profile_block` must leave the profile file content unchanged and must not truncate the file from the marker to end of file.
- In the unbalanced case, `remove_profile_block` must emit a diagnostic on stderr naming the file and the missing end marker so the user can repair the file.
- A `# <<< forgel-code <<<` line with no preceding `# >>> forgel-code >>>` line must be treated as ordinary user content and preserved.
- Every line of the profile that is not part of a well-formed block must appear in the output, in the original order, byte-identical, including blank lines and trailing content.
- `uninstall_profile` must inherit the corrected removal behaviour, because it removes the block through `remove_profile_block`.
- Running `install.sh` twice and then uninstalling must leave the profile with exactly the same non-forgel-code lines it had before the first install, and with no forgel-code markers left.
- `remove_profile_block` must be idempotent and safe on a profile that contains no forgel-code markers: the file is unchanged.
- `tests/test_install.py` must gain regression tests that construct a profile with a start marker and no end marker plus unrelated content, run the removal path used by `install.sh`, and assert the unrelated content survives.
- All existing tests must continue to pass without weakening any test.

## Acceptance Criteria

- A profile file containing `# >>> forgel-code >>>` with no matching `# <<< forgel-code <<<`, followed by unrelated lines, is left byte-for-byte identical after `remove_profile_block` runs, and a diagnostic is written to stderr. Test: `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged`.
- A profile containing one well-formed block surrounded by unrelated lines loses exactly the block and its two markers; all other lines remain in their original order. Test: `test_remove_profile_block_removes_only_wellformed_block`.
- A lone `# <<< forgel-code <<<` line with no start marker is preserved. Test: `test_remove_profile_block_preserves_orphan_end_marker`.
- Installing twice and then running the uninstall path restores the original profile content with no forgel-code markers. Test: `test_install_rerun_then_uninstall_preserves_profile`.
- Running `remove_profile_block` twice on a well-formed block succeeds and the second run leaves the file unchanged. Test: `test_remove_profile_block_is_idempotent`.
- The full test suite passes with no skipped or weakened tests.

## Constraints

- none

## Assumptions

- none

## Files Changed

- install.sh

## Actions

- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- recall
- list_files
- write_file: install.sh

## Commands

- none

## Recent Observations

- recall: step 1 [read_file]
- list_files: .gitignore
- write_file install.sh

## Next Step

Continue from the current repository state and the changed files.
