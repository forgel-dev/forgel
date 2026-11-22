# Task Spec: Release audit: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block |
| Project | — |
| Task | `20261122034544_release-audit-uninstall-no-longer-honors` |
| Plan | `` |
| Repository | `code` |
| Depends on | none |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-22T03:46:57+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

Release audit finding against install.sh: `--uninstall` no longer honors `FORGEL_CODE_PROFILE`. The current `--uninstall` loop visits only the fixed `PROFILE_NAMES` list (' .zshrc .zprofile .zshenv .bash_profile .bash_login .profile'), so a PATH block written into the profile named by `FORGEL_CODE_PROFILE` — by a completed install or by an install whose fresh-shell verification failed and exited non-zero after writing the block — survives uninstall. The result is a stale, unowned `forgel-code` PATH entry that keeps shadowing or resurrecting the removed launcher, a behavior regression against the earlier code that removed the block from the overridden profile.

**Outcome:** `sh install.sh --uninstall` removes the byte-exact marked block from the profile named by `FORGEL_CODE_PROFILE`, in addition to the six standard profile files under `$HOME`, leaving every other line of each edited file untouched; with the variable unset the behavior is exactly as before; a missing or marker-free override file is tolerated with exit code 0 and no file created; the new scenarios are covered by the repository test suite and the whole suite passes.

## Product Intent

—

## User Experience

—

## Goals

- Make `--uninstall` remove the marked PATH block from the profile named by `FORGEL_CODE_PROFILE`, restoring the pre-regression behavior.
- Prove the behavior with tests that run the real `install.sh` against a temporary `$HOME`, including the failed-install leftover case.
- Keep the documented uninstall contract truthful and the whole suite green.

## Non-Goals

- Changing how the installer chooses or writes a profile, the detection order, or the opt-out variables.
- Changing the install path, the launcher, the prefix layout, the verification logic or the exit codes of `--uninstall` beyond what the marker removal already does.
- Removing `forgel-code` blocks from arbitrary dotfiles a user never pointed the installer at (no scanning of `$HOME`, no `.bashrc`, `.kshrc`, `.bash_logout` additions to `PROFILE_NAMES`).
- Changing the block markers, the `export PATH=...` line or the file-rewrite mechanism.
- Assigning, promising or rewriting any release version or tag.
- Touching the client code, the engine protocol, packaging or the build backend.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client's working name is Forgel Code; it is a Python client installed as `forgel-code` with a Pareto 20/80 scope and imports nothing from the engine. | D-004, user accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: R1: When `FORGEL_CODE_PROFILE` is set and non-empty, `--uninstall` removes the marked block from that exact path in addition to the files in `PROFILE_NAMES`.
- **FR-2**: R2: Removal from the override file is byte-exact between `MARKER_START='# >>> forgel-code >>>'` and `MARKER_END='# <<< forgel-code <<<'`; every line outside the block is preserved in order and no new line is appended by an uninstall.
- **FR-3**: R3: When `FORGEL_CODE_PROFILE` is unset or empty, `--uninstall` behaves exactly as before: the six standard profile files under `$HOME` are cleaned and the exit status and output are unchanged.
- **FR-4**: R4: When the override path does not exist, or exists without the start marker, `--uninstall` still exits 0, prints no error for it and creates no file at that path.
- **FR-5**: R5: When the override path is the same file as one of the standard profile names under `$HOME` (for example `$HOME/.profile`), the file is cleaned exactly once, loses no non-block content, and the run still exits 0.
- **FR-6**: R6: A block written into the override profile by a completed install is removed by `--uninstall`; a block left behind by an install that wrote the profile but failed its fresh-shell verification and exited non-zero is removed by the same `--uninstall` invocation.
- **FR-7**: R7: `tests/test_install.py` gains tests, using the real script and a temporary `$HOME`, that cover: override block removed after a successful install, override block removed after a failed install, override-free run unchanged, and missing override file tolerated.
- **FR-8**: R8: `README.md` states that the uninstall also removes the marked block from the profile named by `FORGEL_CODE_PROFILE`; the documentation stays valid under the existing README guard tests (exactly one install command, one update line, one uninstall line, no extra installation path).
- **FR-9**: R9: `CHANGELOG.md` carries the fix under an `## [Unreleased]` heading with a `### Fixed` entry, keeping the existing `[0.1.0]` section intact.
- **FR-10**: R10: The whole repository suite passes: `python -m unittest discover -s tests`.

## Technical Requirements

- `install.sh` stays POSIX `sh` (`set -eu`), keeps never reading stdin, and must still pass `sh -n`.
- The uninstall keeps working when the prefix and launcher are already gone or were never installed.
- No test may be weakened to make the suite pass; fix the script or the test premise.
- Committed artifacts and the CHANGELOG entry are in English, imperative mood, with `git commit -s` and no tool attribution lines.
- No release version or tag is assigned, promised or rewritten by this task.

## User Stories

- As a user who installed Forgel Code with `FORGEL_CODE_PROFILE` set to my own profile file, I want `--uninstall` to remove the PATH block from that file so that no stale `forgel-code` PATH entry is left behind.
- As a user whose install failed its shell check, I want the same `--uninstall` command to clean the block the failed install wrote so that I can back out cleanly.
- As a maintainer closing a release audit finding, I want a test that fails before the fix and passes after it so that the regression cannot return.

## Tests

- AC1: `sh -c set -e; d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; mkdir -p "$d/home"; p="$d/home/custom_profile"; printf '# keep-before\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n# keep-after\n' "$d" > "$p"; HOME="$d/home" FORGEL_CODE_PROFILE="$p" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$p")" = "$(printf '# keep-before\n# keep-after')"; ! grep -q 'forgel-code >>>' "$p"`
- AC2: `sh -c set -e; d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; mkdir -p "$d/home"; printf '# keep\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n' "$d" > "$d/home/.profile"; HOME="$d/home" SHELL=/bin/sh FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$d/home/.profile")" = "# keep"`
- AC3: `sh -c set -e; d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; mkdir -p "$d/home"; printf 'no markers here\n' > "$d/home/plain_profile"; HOME="$d/home" FORGEL_CODE_PROFILE="$d/home/absent_profile" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test ! -e "$d/home/absent_profile"; test "$(cat "$d/home/plain_profile")" = "no markers here"`
- AC4: `sh -c set -e; d=$(mktemp -d); trap 'rm -rf "$d"' EXIT; mkdir -p "$d/home"; printf '# keep\n# >>> forgel-code >>>\nexport PATH="%s/bin:$PATH"\n# <<< forgel-code <<<\n# tail\n' "$d" > "$d/home/.profile"; HOME="$d/home" SHELL=/bin/sh FORGEL_CODE_PROFILE="$d/home/.profile" FORGEL_CODE_HOME="$d/prefix" FORGEL_CODE_BIN="$d/bin" sh install.sh --uninstall; test "$(cat "$d/home/.profile")" = "$(printf '# keep\n# tail')"`
- AC5: `python -m unittest discover -s tests`
- AC6: review
- AC7: review
- AC8: `python -m unittest discover -s tests`
- Shell syntax of the edited script: `sh -n install.sh`
- Command: `python -m unittest discover -s tests`

## Acceptance Criteria

- **AC-1**: AC1: With `FORGEL_CODE_PROFILE` pointing at a file in the temporary `$HOME` that holds the exact marked block plus surrounding lines, `sh install.sh --uninstall` exits 0, the block is gone and the other lines are unchanged (R1, R2).
- **AC-2**: AC2: With `FORGEL_CODE_PROFILE` unset, a marked block in `$HOME/.profile` is still removed and `--uninstall` exits 0 (R3).
- **AC-3**: AC3: With `FORGEL_CODE_PROFILE` pointing at a nonexistent file, `--uninstall` exits 0 and that file is still absent afterwards; a marker-free existing file keeps its content (R4).
- **AC-4**: AC4: With `FORGEL_CODE_PROFILE` set to `$HOME/.profile`, the uninstall leaves `.profile` free of the block and of any other change, exit 0 (R5).
- **AC-5**: AC5: The new suite tests show the override profile cleaned after both a successful and a failed install (R6, R7).
- **AC-6**: AC6: `README.md` documents the override-profile cleanup and the README guard tests still pass (R8).
- **AC-7**: AC7: `CHANGELOG.md` records the fix under `## [Unreleased]` / `### Fixed` (R9).
- **AC-8**: AC8: The full suite `python -m unittest discover -s tests` passes (R10).

## Scope Boundaries

- Restore override-profile handling in the `--uninstall` path of `install.sh`: also remove the marked block from the profile named by `FORGEL_CODE_PROFILE` when the variable is set and non-empty.
- Keep removing the block from the six standard profile names under `$HOME`; the override is an addition, not a replacement.
- Keep marker-based, byte-exact removal semantics and preserve the remaining lines of every edited profile.
- Tolerate a missing, empty or marker-free override file, and an override path that duplicates a standard name, without failing and without creating files.
- Add tests to `tests/test_install.py` that exercise the real `install.sh` under a temporary `$HOME` with a non-standard `FORGEL_CODE_PROFILE`.
- Update the README Uninstall paragraph (and, if needed, the Options table wording) so the documented cleanup covers the profile named by `FORGEL_CODE_PROFILE`.
- Record the fix in `CHANGELOG.md` under an `## [Unreleased]` / `### Fixed` entry.
- Changing how the installer chooses or writes a profile, the detection order, or the opt-out variables.
- Changing the install path, the launcher, the prefix layout, the verification logic or the exit codes of `--uninstall` beyond what the marker removal already does.
- Removing `forgel-code` blocks from arbitrary dotfiles a user never pointed the installer at (no scanning of `$HOME`, no `.bashrc`, `.kshrc`, `.bash_logout` additions to `PROFILE_NAMES`).
- Changing the block markers, the `export PATH=...` line or the file-rewrite mechanism.
- Assigning, promising or rewriting any release version or tag.
- Touching the client code, the engine protocol, packaging or the build backend.

## Risks

- If the uninstall path in `install.sh` was only partially visible during planning (the function body beyond the `PROFILE_NAMES` loop), an existing override handling may already exist; the coder must verify before adding a second removal, so the change is not a no-op or a double edit.
- Editing an arbitrary path named by `FORGEL_CODE_PROFILE` means uninstall can write outside `$HOME`; a wrong value in the environment touches a file the user did not intend. The behavior matches install, but it must be documented and limited to exactly the named path.
- A block that was written before a crash may span a truncated marker pair; byte-exact removal leaves such a fragment behind. Out of scope here, but it must not be reported as fixed.
- New end-to-end tests that install through pip lengthen the suite; a flaky or slow install could make CI unreliable. Prefer a seeded-profile test as the primary check and one real install scenario.
- The README guard tests are positional and token-based; rewording the Uninstall paragraph can trip them if `pip install`, `--user`, `pipx`, `venv` or a second uninstall line appears in the Install section.
- A CHANGELOG heading that does not follow the existing structure can confuse the release train that computes the next version from tags and `CHANGELOG.md`.

## Open Questions

- None.

## Affected Files

- install.sh
- tests/test_install.py
- README.md
- CHANGELOG.md

## Assumptions

- The fix is additive: `PROFILE_NAMES` cleanup stays, and the override profile is cleaned in addition, because the override may be edited while `$HOME/.profile` still holds an older block from an earlier install.
- Cleaning the override path is only attempted when `FORGEL_CODE_PROFILE` is set and non-empty; the installer does not guess a further profile (for example a newly detected login shell profile) beyond the six standard names.
- Removing the block from an existing override file that carries no marker is a silent no-op, matching `remove_profile_block` today.
- The failed-install scenario is modelled by an install that writes the override profile and then fails its fresh-shell verification; the block is intentionally left in place by the installer, so uninstall is the cleanup path.
- `python` on the developer PATH can run the `unittest` suite; the installer tests already locate a Python 3.9+ with `pip` themselves.

## Related Documents

- README.md
- releases/0.1.0/release.md
- CHANGELOG.md
- AGENTS.md
- FORGEL.md

## Revision History

- 1 — initial specification for the release audit finding on `--uninstall` and `FORGEL_CODE_PROFILE`.

## External Dependencies

- **POSIX shell (`sh`, `dash`, `bash`)** — mode `direct`; interface: `install.sh` is run as `sh install.sh [--uninstall]`, syntax-checked with `sh -n`, and the fresh-shell check invokes the detected login shell as `-l -i -c`.; docs: POSIX.1-2017 Shell Command Language, https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html; evidence: The repository dependency contract for `code` declares the concrete shell interface above, and `AGENTS.md` identifies `tests/` as the unittest suite covering the install/uninstall path. The shell is a locally installed executable, so no stub is needed.
- **pip / Python 3.9+** — mode `direct`; interface: The uninstall test path installs the client from the local checkout with pip's `--target`/offline mode; the tests select the Python interpreter from the environment.; docs: pip install documentation, https://pip.pypa.io/en/stable/cli/pip_install/; evidence: The repository dependency contract for `code` specifies the local-checkout, offline `--target` install path and test-selected Python 3.9+ interpreter; `AGENTS.md` lists `tests/` as the unittest suite. This is a locally installed toolchain, so no stub is needed.
- **Keep a Changelog format** — mode `direct`; interface: Edit the repository `CHANGELOG.md` as a local fixture: add or maintain an `## [Unreleased]` heading with a `### Fixed` entry above the existing `[0.1.0]` section.; docs: Keep a Changelog 1.1.0, https://keepachangelog.com/en/1.1.0/; evidence: The dependency contract for `code` states the exact `CHANGELOG.md` structure, and the release rules in `AGENTS.md`/`FORGEL.md` make `CHANGELOG.md` the release input. The file is local, so no stub is needed.
