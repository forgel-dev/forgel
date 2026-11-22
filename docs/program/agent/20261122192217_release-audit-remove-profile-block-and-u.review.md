# Task Review: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

- Task: `20261122192217_release-audit-remove-profile-block-and-u`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-22T21:20:38+00:00

## Summary

The functional core of the task is implemented and covered: `has_unclosed_block` guards `remove_profile_block`, an unterminated start marker now leaves the profile untouched with a diagnostic on stderr that names the file and the missing end marker, `uninstall_profile` inherits the behaviour, and the attributed tests cover the unbalanced case, the orphan end marker, the well-formed block, idempotency and the install-rerun-then-uninstall round trip; QA reports the acceptance checks green. However the attributed diff bundles substantial unrequested work into the same change: two new installer knobs (`FORGEL_CODE_VERIFY_GRACE`, `FORGEL_CODE_POLL_MS`) with `verify_grace`/`verify_poll` and a rewritten millisecond watchdog loop in `bounded_run`, a rewritten pip-module detection in `install_client`, and a suite-wide rewrite of `tests/test_install.py` (thread-pool scenario batching, shared source/install singletons, `lru_cache`) that goes far beyond adding the regression tests. The specification explicitly puts such work out of bounds: Non-Goals exclude reworking unrelated parts of `install.sh` (dependency checks, and by extension the verification timing), and the Technical Requirements fix the change to 'One logical change: fix the removal logic and add its regression tests'. These are product changes with their own failure modes (new public environment variables, a partial-second `sleep` fallback, shared test state under threads), not present in the contract, so the change does not meet the written requirement even though the targeted behaviour works.

## Requirements

- FR-1: `remove_profile_block` deletes only the lines between a start marker and its matching end marker, inclusive, when the start precedes the end.: pass — The guard only short-circuits unbalanced files; a well-formed block still goes through the existing removal, and `test_remove_profile_block_removes_only_wellformed_block` passes.
- FR-2: A start marker with no matching end marker leaves the profile content unchanged and does not truncate to EOF.: pass — `has_unclosed_block` detects the open marker before any temporary file is written and returns 1, so the profile is never rewritten; the acceptance check proves the file is byte-identical.
- FR-3: In the unbalanced case a diagnostic on stderr names the file and the missing end marker.: pass — The message prints the profile path, the start marker and the expected end marker before returning non-zero.
- FR-4: An end marker with no preceding start marker is ordinary content and is preserved.: pass — `has_unclosed_block` only flags an open start marker; a lone end marker falls through to the unchanged removal program, and `test_remove_profile_block_preserves_orphan_end_marker` passes.
- FR-5: Every line outside a well-formed block appears in the output, in order, byte-identical, including blank and trailing lines.: pass — The removal path is not altered for the well-formed case, and the byte-for-byte comparisons in the unbalanced and orphan cases hold.
- FR-6: `uninstall_profile` inherits the corrected behaviour through `remove_profile_block`.: pass — Uninstall goes through the same function, and the rerun-then-uninstall test exercises that path.
- FR-7: Installing twice and then uninstalling restores the original non-forgel-code lines with no markers left.: pass — `test_install_rerun_then_uninstall_preserves_profile` passes, and it starts from a profile that already carries another tool's block.
- FR-8: `remove_profile_block` is idempotent and leaves a marker-free profile unchanged.: pass — A marker-free file returns early at the `grep`, and the second run on a well-formed block finds no markers; `test_remove_profile_block_is_idempotent` passes.
- FR-9: `tests/test_install.py` gains a regression test that builds a start-marker-without-end profile plus unrelated content and asserts the unrelated content survives.: pass — `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged` constructs the fixture and asserts the exact bytes plus the stderr diagnostic.
- FR-10: All existing tests continue to pass without weakening any test.: pass — QA reports the full suite green and no test removals were detected. The extensive restructuring of the file is reported separately under the one-logical-change requirement, not as a weakened assertion.
- Technical Requirements: one logical change, the removal fix plus its regression tests.: fail — The diff also adds `FORGEL_CODE_VERIFY_GRACE`/`FORGEL_CODE_POLL_MS` with `verify_grace`/`verify_poll` and a rewritten millisecond `bounded_run` watchdog, rewrites the pip-module detection in `install_client`, and rewrites the whole test harness (thread pool, shared source/install, `lru_cache`). None of this is the removal fix.
- Non-Goals: do not rework unrelated parts of `install.sh` (dependency checks, virtualenv creation, wrapper creation) and do not change anything beyond the block-removal logic.: fail — The pip dependency check is rewritten from `import pip` to `importlib.util.find_spec('pip')` with a fallback import, and the fresh-shell check timing is reworked; both are explicitly outside the declared scope.
- Technical Requirements: stay inside the tools `install.sh` already uses, harden only the removal logic; no new installer interface.: fail — Two new public environment variables (`FORGEL_CODE_VERIFY_GRACE`, `FORGEL_CODE_POLL_MS`) and the sub-second `sleep` probing they need extend the installer's external interface, which the specification does not ask for.
- Technical Requirements: keep the marker strings exactly as they are.: pass — `MARKER_START` and `MARKER_END` are unchanged.
- Technical Requirements: committed artifacts in English, signed commit, no tool attribution lines.: pass — Both commits carry `Signed-off-by` and English messages; the subject is a task title rather than imperative mood, which is not treated as blocking here.
- Acceptance criteria AC-1 through AC-6 pass as run by QA.: pass — All listed scenario checks and the full suite report exit 0; the deterministic gate is QA's responsibility and is accepted.
- No deleted or weakened tests without justification.: pass — No test removals were detected in the attributed commits, and the new assertions are byte-exact.

## Blocking

- The attributed change bundles unrequested work into a task whose specification is limited to the block-removal fix: new `FORGEL_CODE_VERIFY_GRACE`/`FORGEL_CODE_POLL_MS` knobs with `verify_grace`/`verify_poll` and a rewritten millisecond `bounded_run` watchdog, plus a rewritten pip-module detection in `install_client` — violating the Non-Goals ('Reworking unrelated parts of install.sh (dependency checks, ...)') and the 'One logical change' technical requirement.
- The attributed change rewrites the whole `tests/test_install.py` harness (thread-pool scenario batching, shared source and shared install singletons, `lru_cache`) instead of only adding the regression tests, which the specification does not request and which changes the isolation and determinism of existing tests.

## Test Removals

- none


