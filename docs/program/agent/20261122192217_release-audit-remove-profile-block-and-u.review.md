# Task Review: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

- Task: `20261122192217_release-audit-remove-profile-block-and-u`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-22T21:07:50+00:00

## Summary

The requested defect is fixed: `has_unclosed_block` detects an unterminated `# >>> forgel-code >>>` marker before any rewrite, `remove_profile_block` then leaves the profile untouched and prints a diagnostic naming the file and the missing end marker, an orphan end marker is preserved, well-formed blocks are still removed around unrelated content, and the new regression tests are present and green. The change is nevertheless not acceptable as delivered: the single commit bundles a large amount of work the specification explicitly excludes, altering the installer's timeout/watchdog behaviour with two new environment knobs (`FORGEL_CODE_VERIFY_GRACE`, `FORGEL_CODE_POLL_MS`), rewriting the millisecond polling loop of `bounded_run`, and changing the pip detection path — a Technical Requirement in the spec is 'One logical change: fix the removal logic and add its regression tests', and 'Reworking unrelated parts of install.sh' is a Non-Goal. Alongside it, `tests/test_install.py` is not merely extended but largely re-architected (a thread-pool scenario runner, a shared checkout copy, a shared already-installed client), which is outside the affected-files scope and introduces shared mutable state between tests, and two probe files attributed to the task were part of the change.

## Requirements

- FR-1: a well-formed block between start and end markers is removed inclusive.: pass — Existing awk removal runs only after `has_unclosed_block` reports a closed or marker-free file, so well-formed blocks are still dropped with both markers.
- FR-2: an unmatched start marker leaves the profile content unchanged and never truncates to EOF.: pass — `has_unclosed_block` exits 0 on an open marker and `remove_profile_block` returns before the temp-copy rewrite, so the file is not modified.
- FR-3: the unbalanced case emits a stderr diagnostic naming the file and the missing end marker.: pass — The message interpolates `$profile`, `$MARKER_START` and `$MARKER_END` and goes to stderr.
- FR-4: an orphan end marker with no preceding start marker is preserved as user content.: pass — The early `grep -Fq "$MARKER_START"` guard returns 0, so the file is untouched.
- FR-5: every non-block line survives byte-identical and in order.: pass — The removal program is unchanged apart from the pre-check; it only suppresses matched ranges and prints everything else.
- FR-6: `uninstall_profile` inherits the corrected behaviour.: pass — It removes the block through `remove_profile_block`, which now refuses an unclosed block.
- FR-7: install twice and then uninstall restores the original non-forgel-code lines with no markers left.: pass — Covered by `test_install_rerun_then_uninstall_preserves_profile` over a profile holding a foreign block and blank lines; acceptance check passed.
- FR-8: removal is idempotent and a marker-free profile is unchanged.: pass — No start marker returns 0 before any rewrite; the second run is a no-op, covered by `test_remove_profile_block_is_idempotent`.
- FR-9: `tests/test_install.py` gains regression tests for the unbalanced-marker and install-rerun-then-uninstall cases.: pass — `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged`, `test_remove_profile_block_removes_only_wellformed_block`, `test_remove_profile_block_preserves_orphan_end_marker`, `test_install_rerun_then_uninstall_preserves_profile` and `test_remove_profile_block_is_idempotent` are present and pass.
- FR-10 / AC-6: all existing tests continue to pass with no test weakened or deleted.: pass — QA environment gates and the full suite pass; no test removals were detected. The broad test rewrite is flagged separately as out of scope, not as a proven weakening.
- Stay inside POSIX shell plus the already-used awk/text tools; no new runtime dependency.: pass — awk, sleep and the existing utilities are used; no Python or perl is introduced into the installer.
- Keep the marker strings exactly as they are.: pass — `MARKER_START` and `MARKER_END` are unchanged.
- Commit in English, imperative mood, signed off, without tool attribution lines.: pass — Commit 445b877 is English and carries `Signed-off-by: Forgel`; no attribution line found.
- One logical change: fix the removal logic and add its regression tests.: fail — The same commit adds `FORGEL_CODE_VERIFY_GRACE` and `FORGEL_CODE_POLL_MS`, rewrites the watchdog in `bounded_run` to millisecond polling, changes pip detection to `importlib.util.find_spec`, and re-architects the test module with a thread pool, a shared checkout copy and a shared installed client — far beyond the removal fix.
- Non-Goal: do not rework unrelated parts of `install.sh` (dependency checks, watchdog, virtualenv, wrapper).: fail — The dependency check for pip and the fresh-shell watchdog are both rewritten, and two new user-facing environment variables are introduced, which the spec does not request.

## Blocking

- The attributed commit bundles unrequested functionality into `install.sh`: new `FORGEL_CODE_VERIFY_GRACE`/`FORGEL_CODE_POLL_MS` knobs, a millisecond-polling rewrite of the `bounded_run` watchdog and a changed pip detection path. This violates the Technical Requirement 'One logical change: fix the removal logic and add its regression tests' and the Non-Goal against reworking unrelated parts of `install.sh`.
- `tests/test_install.py` is not just extended with regression tests: it is re-architected around a `ThreadPoolExecutor` scenario runner, a `lru_cache`d shared source checkout and a shared already-installed client. That is outside the change and makes previously independent tests share mutable temp state and install concurrently from one symlinked source, an unnecessary race risk.
- Probe files `tests/test_zz_probe2.py` and `tests/test_zz_timing_probe.py` were part of this task's change; temporary timing probes are not part of the requested fix.

## Test Removals

- none


