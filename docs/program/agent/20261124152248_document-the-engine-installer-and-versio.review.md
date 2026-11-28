# Task Review: Document the engine installer and version contract

- Task: `20261124152248_document-the-engine-installer-and-versio`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-28T08:48:12+00:00

## Summary

The attributed change is exactly three documentation files: a new CHANGELOG.md with an Unreleased entry covering the single install step, entry point and shell reachability, removal, the directly consumable version report and pre-install version determination; a rewritten README Install section; and an expanded docs/install.md. Every documented name, default, flag and output contract can be checked against the shipped code and matches: install.sh defines FORGEL_INSTALL_ROOT (~/.local/share/forgel), FORGEL_BIN_DIR (~/.local/bin), FORGEL_SOURCE (pypi), FORGEL_REF (latest), FORGEL_PYTHON, the 3.11 minimum, the --resolve/--uninstall modes, the one-value stdout contract and the delimited start-up block; engine_version declares that the report needs no project, credential or particular working directory, writes nothing, and emits one JSON object whose top-level `version` field is the answer, exiting non-zero with a reason on stderr when no comparable version exists; envelope/write in client_cli confirm the flat envelope and single JSON object. The strictly-newer comparison rule is stated and explicitly attributed to the caller that drives the installer (with `sh install.sh` installing the target it resolved), so it does not claim installer behaviour that does not exist. The change is documentation text only: no test, guard or assertion reads documentation, no test was removed or weakened, no release version or tag is assigned, and no unrelated, temporary or generated file is included. One sentence in docs/install.md refers to `$FORGEL_BIN_DIR/forgel version --json`, which is only meaningful when the variable is exported; because the correct default path is given immediately before it in the same section, this is loose wording rather than a contradicted shipped behaviour, and I do not treat it as blocking.

## Requirements

- FR-1 / AC-1: One install step presented as the complete way to obtain a working engine, with prerequisites named and no second required step.: pass — README and docs/install.md present `sh install.sh` from the checkout root as the complete step and name Linux/macOS, a checkout and Python 3.11+ on PATH; no second step is required. The installer header confirms the mode and the 3.11 minimum.
- FR-2 / AC-2: Where the entry point is placed, how the engine is run afterwards, and what to do when the location is not reachable from the shell.: pass — Entry point at `~/.local/bin/forgel` (FORGEL_BIN_DIR), matching install.sh defaults; run `forgel` in a new session; fallback to running the entry point by full path and checking the start-up file. The one sentence using `$FORGEL_BIN_DIR/forgel` assumes the variable is exported but is preceded by the correct default path.
- FR-3 / AC-3: How the user confirms a successful install by reading the reported version.: pass — `forgel version --json` shown, with the `version` field described as the same value the install reported; confirmed by engine_version.version_command and tests/test_install.py's assertion that the two agree.
- FR-4 / AC-4: Version report consumable directly by another program, the supported compatibility judgement, needing no project, no model credential and no particular working directory.: pass — Stated in README and docs/install.md; engine_version documents the same contract and client_cli.write emits exactly one JSON object; a failure exits non-zero with the reason on stderr and an empty version.
- FR-5 / AC-5: How the version a configured source or release ref would provide is determined before anything is installed, and that this is what an installed engine is compared against.: pass — `sh install.sh --resolve` described as answering without installing or changing anything; install.sh documents --resolve as producing the version on stdout, and the existing Inputs table explains FORGEL_SOURCE/FORGEL_REF.
- FR-6 / AC-6: Strictly-newer comparison rule; equal or older available version leaves the installed engine untouched.: pass — Both files state the rule and scope it correctly: `sh install.sh` installs the target it resolved, so the comparison belongs to the caller that keeps the engine current. This is consistent with the shipped installer rather than a false claim about it.
- FR-7 / AC-7: How to remove the engine and its entry point and which configuration and project material are kept.: pass — `sh install.sh --uninstall` removes the install root, the entry point and the start-up block; `~/.forgel` configuration and project material are kept, consistent with the README's documented engine home.
- FR-8 / AC-8: Every name, option, location and example matches the shipped engine and installer; no documented behaviour they do not perform.: pass — Checked against install.sh (inputs, defaults, modes, stdout contract, start-up markers), engine_version.py (--json/--home handling, failure behaviour) and client_cli.py (flat envelope). The only imprecision is the `$FORGEL_BIN_DIR` wording, which is contextualised by the correct default path in the same section.
- FR-9 / AC-9: User-visible release notes carry an entry covering the install step, entry point and reachability, removal, the directly consumable version inquiry and pre-install version determination.: pass — The new CHANGELOG.md 'Added' entries cover each of the five required capabilities; the header matches the format the release train generates.
- FR-10 / AC-10: Behaviour and stable contracts only; no internal structure, timing, runtime bound, test duration or local environment detail.: pass — The new text names only user-facing inputs and observable outcomes; no timings, bounds, internal module structure or test details appear.
- FR-11 / AC-11: No statement in the user-facing introduction contradicts the shipped installer or version behaviour, and no previously accurate section is weakened.: pass — README's Install section was corrected and its removed equivalence claim (installer output equals `forgel version --json`) is restated in the new 'Confirming the installation' section; the rest of the introduction (client, scripted client, skeleton, gates) is untouched.
- Constraints: documentation-only change, no automated check on documentation, no release version or tag assignment, no unrelated files.: pass — Only CHANGELOG.md, README.md and docs/install.md changed; no test or guard reads documentation, no test was removed or weakened, and no version or tag is assigned or promised.

## Blocking

- none

## Test Removals

- none


