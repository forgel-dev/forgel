# Task Spec: Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo |
| Project | — |
| Task | `20261122192217_release-audit-remove-profile-block-and-u` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T19:22:50+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

install.sh removes the forgel-code profile block with an AWK program driven by the `# >>> forgel-code >>>` and `# <<< forgel-code <<<` markers. When the start marker exists without a matching end marker, the AWK never clears its `inside` flag and drops every line from the marker to end of file. Re-running install or running uninstall on such a profile destroys unrelated user content, contradicting the install contract that only the delimited block is removed and every other line is preserved. The release audit reports this as a defect to resolve.

**Outcome:** `remove_profile_block` (and therefore `uninstall_profile`, which uses it) removes a profile block only when both markers are present and well formed. A start marker without a matching end marker leaves the file byte-for-byte unchanged apart from an optional diagnostic on stderr, and unrelated profile lines are never deleted. New regression tests in tests/test_install.py cover the unbalanced-marker case and the install-rerun-then-uninstall case, and the whole suite still passes.

## Product Intent

The client installs as `forgel-code` into the user's shell profile; installation and removal must be safe and reversible on any profile the user already has, so a new terminal finds `forgel-code` on PATH without the installer ever damaging unrelated profile content. Removing the client must restore the profile to its pre-install state.

## User Experience

A user installs `forgel-code`, re-runs `install.sh`, and later uninstalls. Their `.bashrc`/`.zshrc` keeps every unrelated line and every other tool's block exactly as before; only the forgel-code block appears and disappears. If the profile somehow contains a stray start marker without an end marker, the installer warns instead of silently wiping the rest of the file.

## Roadmap

—

## Goals

- Resolve the release audit finding that an unmatched start marker deletes the rest of the profile.
- Guarantee that install re-runs and uninstall preserve all non-forgel-code profile content.
- Add regression tests that fail on the current AWK and pass after the fix.

## Non-Goals

- Changing the PATH installation strategy, install location, or the markers themselves
- Changing `install.sh` behaviour for a well-formed block (already correct)
- Modifying the client Python code, packaging, or the CLI
- Reworking unrelated parts of `install.sh` (dependency checks, virtualenv creation, wrapper creation)
- Cross-platform rewrites of profile editing beyond what the current script already targets

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code; it is a Python client installed as `forgel-code`. | D-004, User decision log |

## Functional Requirements

- **FR-1**: `remove_profile_block` must delete lines only between a `# >>> forgel-code >>>` line and its matching `# <<< forgel-code <<<` line, inclusive, when the start marker precedes the end marker.
- **FR-2**: If a `# >>> forgel-code >>>` line has no matching `# <<< forgel-code <<<` line after it, `remove_profile_block` must leave the profile file content unchanged and must not truncate the file from the marker to end of file.
- **FR-3**: In the unbalanced case, `remove_profile_block` must emit a diagnostic on stderr naming the file and the missing end marker so the user can repair the file.
- **FR-4**: A `# <<< forgel-code <<<` line with no preceding `# >>> forgel-code >>>` line must be treated as ordinary user content and preserved.
- **FR-5**: Every line of the profile that is not part of a well-formed block must appear in the output, in the original order, byte-identical, including blank lines and trailing content.
- **FR-6**: `uninstall_profile` must inherit the corrected removal behaviour, because it removes the block through `remove_profile_block`.
- **FR-7**: Running `install.sh` twice and then uninstalling must leave the profile with exactly the same non-forgel-code lines it had before the first install, and with no forgel-code markers left.
- **FR-8**: `remove_profile_block` must be idempotent and safe on a profile that contains no forgel-code markers: the file is unchanged.
- **FR-9**: `tests/test_install.py` must gain regression tests that construct a profile with a start marker and no end marker plus unrelated content, run the removal path used by `install.sh`, and assert the unrelated content survives.
- **FR-10**: All existing tests must continue to pass without weakening any test.

## Technical Requirements

- All committed artifacts are English (project language rule).
- Stay inside POSIX shell plus the AWK and text tools `install.sh` already uses; do not introduce a new runtime dependency such as Python or perl into the shell script.
- Do not weaken or delete existing tests to make the change pass (repository AGENTS.md rule).
- Keep the marker strings `# >>> forgel-code >>>` and `# <<< forgel-code <<<` exactly as they are.
- Commit in English, imperative mood, with `git commit -s`, without tool attribution lines.
- One logical change: fix the removal logic and add its regression tests.

## User Stories

- As a user with an existing shell profile, I want install and uninstall to touch only the forgel-code block, so that my other settings and tools' blocks survive.
- As a user whose profile has a damaged or partial forgel-code marker, I want the installer to warn instead of deleting the rest of my file, so that I can repair it myself.

## Tests

- A profile file containing `# >>> forgel-code >>>` with no matching `# <<< forgel-code <<<`, followed by unrelated lines, is left byte-for-byte identical after `remove_profile_block` runs, and a diagnostic is written to stderr. Test: `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged`.: `python -m pytest -q tests/test_install.py -k unmatched_start_marker`
- A profile containing one well-formed block surrounded by unrelated lines loses exactly the block and its two markers; all other lines remain in their original order. Test: `test_remove_profile_block_removes_only_wellformed_block`.: `python -m pytest -q tests/test_install.py -k removes_only_wellformed_block`
- A lone `# <<< forgel-code <<<` line with no start marker is preserved. Test: `test_remove_profile_block_preserves_orphan_end_marker`.: `python -m pytest -q tests/test_install.py -k orphan_end_marker`
- Installing twice and then running the uninstall path restores the original profile content with no forgel-code markers. Test: `test_install_rerun_then_uninstall_preserves_profile`.: `python -m pytest -q tests/test_install.py -k install_rerun_then_uninstall`
- Running `remove_profile_block` twice on a well-formed block succeeds and the second run leaves the file unchanged. Test: `test_remove_profile_block_is_idempotent`.: `python -m pytest -q tests/test_install.py -k is_idempotent`
- The full test suite passes with no skipped or weakened tests.: `python -m pytest -q tests`
- Command: `python -m pytest -q tests`

## Acceptance Criteria

- **AC-1**: A profile file containing `# >>> forgel-code >>>` with no matching `# <<< forgel-code <<<`, followed by unrelated lines, is left byte-for-byte identical after `remove_profile_block` runs, and a diagnostic is written to stderr. Test: `test_remove_profile_block_unmatched_start_marker_leaves_file_unchanged`.
- **AC-2**: A profile containing one well-formed block surrounded by unrelated lines loses exactly the block and its two markers; all other lines remain in their original order. Test: `test_remove_profile_block_removes_only_wellformed_block`.
- **AC-3**: A lone `# <<< forgel-code <<<` line with no start marker is preserved. Test: `test_remove_profile_block_preserves_orphan_end_marker`.
- **AC-4**: Installing twice and then running the uninstall path restores the original profile content with no forgel-code markers. Test: `test_install_rerun_then_uninstall_preserves_profile`.
- **AC-5**: Running `remove_profile_block` twice on a well-formed block succeeds and the second run leaves the file unchanged. Test: `test_remove_profile_block_is_idempotent`.
- **AC-6**: The full test suite passes with no skipped or weakened tests.

## Scope Boundaries

- The block-removal logic in install.sh used by `remove_profile_block` and `uninstall_profile`
- Handling of a start marker with no matching end marker
- Handling of an end marker with no preceding start marker
- Preservation of all lines outside a well-formed block, in order
- Idempotency: re-running install and then uninstall restores the original profile content
- Regression tests for the above in tests/test_install.py
- Changing the PATH installation strategy, install location, or the markers themselves
- Changing `install.sh` behaviour for a well-formed block (already correct)
- Modifying the client Python code, packaging, or the CLI
- Reworking unrelated parts of `install.sh` (dependency checks, virtualenv creation, wrapper creation)
- Cross-platform rewrites of profile editing beyond what the current script already targets

## Risks

- An unbalanced start marker is ambiguous; if review expects the trailing content to be removed anyway, the chosen fail-safe behaviour (leave file unchanged, warn) would be rejected. The intent only forbids destroying unrelated content, so fail-safe is chosen.
- The AWK rewrite could change behaviour for edge cases not covered by tests (markers indented, repeated well-formed blocks, no trailing newline on the last line).
- If `install.sh` uses platform-specific in-place edit flags, the test harness may not reproduce the real path; the tests must call the same functions the script uses rather than re-implement the filter.
- Existing tests may assert the current truncating behaviour; correcting them is part of the change but must not be done by weakening assertions.

## Open Questions

- None.

## Affected Files

- install.sh
- tests/test_install.py

## Assumptions

- `remove_profile_block` is a shell function inside `install.sh`, and `uninstall_profile` calls it; the fix therefore belongs in that single function.
- The safest behaviour for an unbalanced start marker is to leave the file untouched and warn, rather than guess which lines the block would have covered; the intent states only that a block is removed, so an ill-formed block is not removed.
- Tests exercise the shell functions through a subprocess (sourcing `install.sh` or invoking the install/uninstall entry points) with a temporary profile file, matching how `tests/test_install.py` already tests the script.
- The test suite is runnable with pytest in this repository (`.pytest_cache` present, `tests/` package present); `make test` does not exist in this repository.
- The corrected function may return a non-zero status in the unbalanced case; whether the caller aborts is decided in the shell script and must not result in the profile being modified.

## Related Documents

- AGENTS.md
- FORGEL.md
- README.md
- CHANGELOG.md
- releases/0.1.0/release.md

## Revision History

- v1: initial specification for the release-audit finding on unbalanced forgel-code block markers in install.sh

## External Dependencies

- **awk** — mode `direct`; interface: Line-oriented filter invoked from the profile-editing shell functions (`remove_profile_block`, and `uninstall_profile` which delegates to it). The profile text is piped to `awk '<program>'`, and the program writes only the lines that must survive to stdout, then the caller replaces the profile with that output. The contract the fix relies on: `BEGIN`/`END`, `next`, and `print` are available; a line matched by a marker rule can be suppressed with `next`, and every non-matching line is re-emitted unchanged with `print`. The corrected program must track `inside` only after a start marker and reset it on the matching end marker, so an unterminated start marker cannot leave `inside = 1` through EOF and swallow trailing user content. No locale-, gawk-extension- or version-dependent constructs are used, so output is deterministic for identical input bytes. Exit status 0 on success; the caller treats a non-zero status as a failure and does not rewrite the profile.; docs: POSIX awk specification, https://pubs.opengroup.org/onlinepubs/9699919799/utilities/awk.html; evidence: AGENTS.md `Layout` table declares `environment.yaml` ("Environment contract for Forgel itself: build, commands, env") and `environment/` ("Dockerfile for Forgel's own sandbox environment"), i.e. the tool set of this project's own runtime image is defined in-repo rather than assumed. AGENTS.md also declares `tests/` ("`unittest` suite") as the place where the behaviour is exercised, and the repository rules require `make test`/`make lint` on every change, so the filter is covered by an in-environment test run. awk is a POSIX utility shipped by the environment's base image, so it is reachable as a locally installed executable without any stub. The exact invocation contract (pattern-action rules, `BEGIN`/`END`, `next`, variables, `print`) is the one documented in the POSIX awk specification cited in `docs`.
- **bash / POSIX shell profile files (.bashrc, .zshrc, .profile)** — mode `direct`; interface: Plain-text, newline-separated startup files that install mutates and uninstall restores. Install appends a marked block delimited by the start marker line `# >>> forgel-code >>>` and the end marker line `# <<< forgel-code <<<`; the file may already contain arbitrary user content and other tools' delimiter blocks. Uninstall reads the same path and removes only the lines from a start marker through its matching end marker, leaving every other line (before, between, and after the block) byte-for-byte unchanged; an unterminated start marker is not a complete block and must not cause deletion through EOF. The file is never parsed as shell here — only as lines — so no shell evaluation, sourcing or syntax checking of user content is required. Tests operate on temporary fixture files (copies and hand-written profile texts, including the unterminated-marker case and a profile with foreign blocks) instead of the user's real dotfiles.; docs: Repository docs: AGENTS.md `Layout` (`environment.yaml` environment contract, `tests/` unittest suite) and the repository rule `Never weaken a test to make it pass; fix the product or the test's premise.`; evidence: The dependency is a text file format handled entirely by this repository's own code, not an external service or third-party API: the marker strings, the append-on-install and remove-on-uninstall logic live in the repository under audit, so the contract is fully determined by that source. The repository instructions define an in-repo environment contract (`environment.yaml` — "build, commands, env") and a `tests/` unittest suite where fixtures can be created deterministically in a temp directory, and the code repository rule "Never weaken a test to make it pass; fix the product or the test's premise" requires the fixture set (complete block, unterminated start marker, foreign blocks, no markers) to encode the premise directly. No real `$HOME` dotfile is required for a deterministic test, so no stub is needed.
