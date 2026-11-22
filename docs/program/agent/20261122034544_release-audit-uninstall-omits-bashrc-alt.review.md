# Task Review: Release audit: --uninstall omits ~/.bashrc, although the previous installer wrote the marked bl

- Task: `20261122034544_release-audit-uninstall-omits-bashrc-alt`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-22T04:04:24+00:00

## Summary

The change is minimal and targeted: `PROFILE_NAMES` in install.sh gains `.bashrc`, and since that variable is consumed only by `uninstall`, the uninstall path now strips the marked block from `~/.bashrc` while the install path, marker text and CLI surface are untouched. `remove_profile_block` already tolerates missing, unreadable and block-free files and is idempotent, so FR-3/FR-4/FR-5 hold for the new candidate without extra logic. tests/test_install.py adds a `bashrc` regression test with an exact byte-for-byte expectation, adds an `idempotent` double-uninstall test over every candidate profile, extends `CANDIDATE_PROFILES`, and factors the block text into a `_marked_block` helper whose output matches the installer's block byte for byte; the pre-existing string-concatenation refactors keep the same content. All tests use a temporary HOME and no test was deleted or weakened. One cosmetic nit: `assertNotIn("Removed the PATH block", second.stdout)` is vacuous because the script never prints that phrase, but it does not affect the requirement. Minor note: the bashrc test writes the block in the exact install format rather than invoking the installer (whose bash branch cannot select `~/.bashrc`, since a fresh bash install verifies through `-l -i`), which is the only feasible way to reproduce the audited state and matches the spec's fixture allowance.

## Requirements

- FR-1: uninstall treats ~/.bashrc as a file that can contain the marked block: pass — `.bashrc` added to `PROFILE_NAMES`, which `uninstall` iterates.
- FR-2: uninstall file set is a superset of the bash install targets (`.bash_profile` branch and `.bashrc`): pass — List covers .bash_profile, .bash_login, .profile plus .bashrc; a custom FORGEL_CODE_PROFILE is still cleaned as before.
- FR-3: block between existing markers removed, all other lines unchanged in content and order: pass — Unchanged awk-based `remove_profile_block`; the bashrc test compares the full file against `# keep-before\nexport EDITOR=vi\n# keep-after\n`.
- FR-4: missing/unreadable/block-free candidate does not fail or modify the file: pass — `remove_profile_block` returns 0 for non-files and for files without MARKER_START; idempotence test exercises block-free reruns.
- FR-5: second uninstall produces the same result as the first: pass — `test_repeated_uninstall_of_bashrc_is_idempotent` snapshots all candidate files after run one and compares after run two.
- FR-6: install path behaviour unchanged (one block in the same selected file): pass — Only the uninstall-only `PROFILE_NAMES` list changed; `profile_path`, markers and block-writing code are untouched.
- FR-7: regression test with `bashrc` in its name, temp HOME, block in ~/.bashrc, no ~/.bash_profile, asserts block gone and unrelated lines survive: pass — `test_uninstall_removes_the_marked_block_from_bashrc` does all of this; it writes the block in the installer's exact byte format via `_marked_block` rather than running the installer, which matches the spec's fixture allowance and is the only reproducible state since the install path's bash branch never selects ~/.bashrc.
- FR-8: idempotence test with `idempotent` in its name, two uninstall runs, unchanged file, no markers: pass — `test_repeated_uninstall_of_bashrc_is_idempotent` verifies both runs and marker counts; the `assertNotIn("Removed the PATH block", ...)` line is vacuous but harmless.
- FR-9: tests use a temporary HOME and never touch the real startup files: pass — `InstallerCase` uses `tempfile.mkdtemp` and `HOME`/`FORGEL_CODE_*` overrides; no real home path is read or written.
- FR-10: install.sh remains valid POSIX sh: pass — Change is a string literal only; QA ran `sh -n install.sh` (pass).
- Scope: only install.sh and tests/test_install.py change; no README/CHANGELOG/pyproject/releases/forgel_code edits: pass — Attributed diff touches exactly the two files.
- No weakened or deleted tests; refactors preserve semantics: pass — Refactors replace inline block text with `_marked_block`, which yields identical content; no test was removed.

## Blocking

- none

## Test Removals

- none


