# Task Review: Add the combined engine and client install mode

- Task: `20261124152248_add-the-combined-engine-and-client-insta`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-25T01:02:04+00:00

## Summary

The attributed change implements the combined install: install.sh gains an engine phase that learns the offered version from the configured source without changing anything, reads the present engine version, then keeps, replaces or obtains the engine, enforces the client's declared minimum (`MIN_ENGINE_VERSION` in `forgel_code/__init__.py`), and reports `Engine: forgel <version> <installed|kept|replaced>` or fails with the minimum, the found/offered version and an action. A deterministic stand-in (`tests/stub_engine_install.py`) mirrors the recorded engine-installer contract and the new `tests/test_install_engine.py` exercises obtain/keep/replace/failure/client-only/uninstall/repeat cases through the real installer. The documentation check (`tests/test_readme_install.py` and the `ReadmeTest` in `tests/test_cli.py`) is deleted together with its supporting data and replaced by nothing, and the README/CHANGELOG are updated to describe the combined installation, the engine source, the client-only route, the no-profile-edit option and the leave-engine-on-uninstall behaviour. QA reports all repository and environment checks passing, the worktree is clean, and the removed tests carry justified `removed` reasons consistent with the mandated removal of documentation-reading checks. No unrelated, temporary or generated file is part of the attributed change, and I found no logical or security defect in the reviewed parts.

## Requirements

- Default installation also ensures a supported engine in the same run (FR-1, AC-1): pass — install.sh performs the engine phase by default; `EngineObtainedTest.test_absent_engine_is_installed_and_reported` shows the client plus an installed engine reported as `Engine: forgel 0.2.0 installed`.
- The offered version is learned without changing the machine (FR-2): pass — The engine installer is queried with `--available-version` through the stub contract, which installs nothing; `install_calls()` remains empty in the keep cases.
- Absent engine is obtained; a present engine at or above the offered version is kept unchanged (FR-3, FR-4, AC-2, AC-4): pass — `EngineObtainedTest` and `EngineKeptTest` assert an unchanged engine version and no install call for equal and higher present versions.
- A strictly newer offered engine replaces the present one; an engine older than or equal to the present one is never installed (FR-5, FR-6, AC-3): pass — `EngineReplacedTest` covers replacement; keep cases assert `install_calls() == []`, so no equal or older version is installed.
- The finished state satisfies the declared minimum or the run fails (FR-7, AC-5, AC-6): pass — Minimum is declared once in `forgel_code/__init__.py`, and the tests use `_declared_minimum()`; failure message contents are asserted by the failure scenarios covered by the passing repository checks.
- A failed engine outcome reports the minimum, the found or offered version and an action, and is distinguishable from success (FR-8): pass — The installer tracks ENGINE_MINIMUM/ENGINE_PRESENT/ENGINE_AVAILABLE for the failure report and exits non-zero; the README documents that the failure names the minimum, version and next action.
- A successful installation states the engine version in place and how it was obtained (FR-9, AC-11): pass — Asserted by the `Engine: forgel <version> installed|kept|replaced` lines in the engine tests and described in the README.
- Version ordering tolerates one leading prefix and trailing zeros; an unorderable version never satisfies the minimum (FR-10, AC-9): pass — `test_a_prefix_or_trailing_zeros_do_not_make_a_newer_version` keeps `v0.1.0.0` against offered `0.1`; the installer's comparison is component-wise and the README states the ordering rule.
- The client-only installation installs the client and neither queries nor changes any engine (FR-11, AC-7): pass — `--client-only` short-circuits the engine phase before any query; the README documents that route and the installer advertises the flag.
- Removing the client installs nothing and leaves any engine in place (FR-12, AC-10): pass — The uninstall path removes the prefix, launcher and PATH block only; the README states it leaves any engine in place.
- The startup-configuration opt-out does not disable the engine part (FR-13): pass — `FORGEL_CODE_NO_MODIFY_PATH` only skips profile editing and the fresh-shell check; the README states the engine part still happens.
- The engine source is documented configuration with a stated default and a way to point it elsewhere (FR-14, AC-13): pass — README documents `FORGEL_ENGINE_SOURCE` (default `https://github.com/forgel-dev/forgel`) and `FORGEL_ENGINE_INSTALLER`, with an example overriding the source; both are read by install.sh.
- Repeating the default installation changes nothing that needs no change and leaves one client installation and one startup entry (FR-15, AC-8): pass — The existing re-run guarantees (one marked block, replaced prefix) are unchanged and the engine keep case issues no install call on the second run.
- README/CHANGELOG present the default installation as the way to obtain a working pair, document client-only and the engine source, and no longer instruct a separate engine for the default (FR-16, AC-11, AC-12, AC-13): pass — The README adds 'The engine', 'Engine source' and 'Client only' sections describing the decision table, the failure report, the success report, the variables and the defaults; the prerequisites line no longer asks for the engine on PATH, and the CHANGELOG records the change.
- No automated check reads documentation text and none replaces it (FR-17, AC-14): pass — `tests/test_readme_install.py` is deleted in full with its data, `tests/test_cli.py` `ReadmeTest` is removed; no new documentation-reading check is added and no file reads README.md text.
- Installation instructions are accepted or returned solely by reading their text (FR-18, AC-16): pass — With the documentation checks gone, no automated verdict over README wording exists; this review judged the wording directly.
- All other automated checks stay in place and unchanged; installer and client behaviour outside the combined installation is unchanged (FR-19, AC-15): pass — Remaining tests (packaging, CLI, redaction, interactive, installer) are untouched by the diff; the attributed changes to install.sh only add the engine phase and its reporting.
- No unrelated, temporary or generated file committed: pass — The attributed files are the installer, the version module, the README, the CHANGELOG, the engine stub and the engine/install/CLI tests; no debug or generated artifacts appear.
- No weakened or unjustifiably deleted test: pass — The only deletions are the documentation-reading check and its CLI counterpart, both justified as `removed` by the mandated elimination of checks over documentation text (D-106), with no replacement check over documentation.

## Blocking

- none

## Test Removals

- file:tests/test_readme_install.py
- line:def test_readme_documents_the_engine_commands_the_client_calls(self) -> None:
- line:def test_readme_documents_the_missing_engine_command_report(self) -> None:
- line:def test_readme_has_a_pinned_install_command(self) -> None:
- line:def test_readme_has_no_default_branch_install(self) -> None:
- line:def test_readme_has_no_editable_install_recommendation(self) -> None:
- line:def test_readme_documents_the_update_path(self) -> None:
- line:def test_first_install_command_is_the_installer_line(self) -> None:
- line:def test_no_alternative_main_path(self) -> None:
- line:def test_no_editable_install(self) -> None:
- line:def test_tests_section_shows_the_extra_install(self) -> None:
- line:def test_installer_line_is_inside_a_code_block(self) -> None:
- line:def test_prerequisites_are_kept(self) -> None:
- line:def test_one_update_line_and_one_uninstall_line(self) -> None:
- line:def test_one_windows_line_outside_the_main_path(self) -> None:
- line:def test_no_stale_install_script_url(self) -> None:
- line:def test_install_script_url_names_the_current_release(self) -> None:
- line:def test_install_and_uninstall_share_the_install_script_url(self) -> None:
- line:def test_accepts_the_good_shape(self) -> None:
- line:def test_accepts_the_extra_install_inside_the_tests_section(self) -> None:
- line:def test_rejects_a_tests_section_without_the_runner(self) -> None:
- line:def test_rejects_a_tests_section_without_the_no_install_path(self) -> None:
- line:def test_rejects_a_pip_install_outside_the_tests_section(self) -> None:
- line:def test_rejects_a_pip_install_in_the_tests_section_without_the_extra(
- line:def test_rejects_an_editable_install(self) -> None:
- line:def test_rejects_the_editable_long_flag(self) -> None:
- line:def test_rejects_pip_before_the_installer(self) -> None:
- line:def test_rejects_a_pip_install_first_command(self) -> None:
- line:def test_rejects_a_virtual_environment_block(self) -> None:
- line:def test_rejects_pipx_as_an_alternative(self) -> None:
- line:def test_rejects_two_update_lines(self) -> None:
- line:def test_rejects_a_missing_uninstall_line(self) -> None:
- line:def test_stale_install_script_url_is_rejected(self) -> None:
- line:def test_divergent_install_script_url_is_rejected(self) -> None:
- line:def test_default_branch_install_script_url_is_rejected(self) -> None:
- line:def test_a_missing_install_script_url_is_rejected(self) -> None:
- line:def test_rejects_a_stale_url_anywhere_in_the_document(self) -> None:
- line:def test_rejects_a_second_windows_line(self) -> None:
- line:def test_rejects_a_windows_line_above_the_installer(self) -> None:
- line:def test_rejects_windows_offered_as_the_main_path(self) -> None:
- line:def test_rejects_a_missing_engine_prerequisite(self) -> None:

- tests/test_readme_install.py: removed
- tests/test_cli.py::ReadmeTest: removed
