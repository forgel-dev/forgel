# Task Review: Release audit: `engine_present_version` runs `forgel --version --json` and reads `payload["engi

- Task: `20261128085012_release-audit-engine-present-version-run`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-28T09:45:43+00:00

## Summary

The attributed commit fixes the reported defect at its root: `engine_present_version` no longer asks an already-installed engine with an undocumented flag or parses the answer by hand — it now runs the engine through the client's own runner and reads the payload with the client's own `reported_version`, so the installation and the client read the same documented answer with the same tolerance of shapes, and the client reimplements nothing. The comparison, minimum check, failure message, client-only, uninstall and no-profile-edit paths are untouched, so keep/replace/repeat behaviour and every other documented path stay as required. The stub engine was tightened to answer only the documented version report and to return a structured unsupported-command answer with a non-zero status for any other argv, which turns the old bug into a test failure instead of a silent pass, and a new regression test pins the exact question asked, that no engine is installed, and that the run states the version kept. No test was removed or weakened, no unrelated or generated file is committed, and the single CHANGELOG bullet describes the behaviour (asking and reading the engine's own documented answer, keeping an engine that is not strictly older, no downgrade, idempotent repeat) without exposing volatile implementation details. QA reports the repository test and both environment e2e runs green, which covers the observed-run acceptance checks.

## Requirements

- FR-1/FR-2, AC-1: a present engine that answers its documented version report is recognized at exactly the version it reports, and the version comes only from that documented answer (never described as missing or unreadable).: pass — `engine_present_version` now invokes the engine through the client's own runner and reads the payload with the client's `reported_version`; the stub engine answers only the documented report and gives a structured unsupported-command answer, non-zero, for any other argv, so the old form can no longer look healthy. The new test `test_a_supported_engine_answering_its_report_is_kept` asserts the exact question asked (`version --json`), the absence of any engine installation and the kept-version output.
- AC-2: the version the run reports for the engine equals the version the installed engine reports about itself.: pass — The reported value is the one the client's own reader extracts from the engine's answer, and the kept-version assertion compares it with the version the stub engine reports; normalization of one leading marker or trailing zeros is the documented ordering rule and stays as required.
- FR-3/FR-6, AC-3: a present supported engine is kept with no engine installed when the offered version is equal, older, or the same apart from a leading marker or trailing zeros, and the run says it was kept.: pass — The keep/compare logic and the stated minimum are untouched; the existing kept-scenario tests (equal, prefix, trailing zeros) remain and still assert no installation and a kept message.
- FR-4, AC-4: a strictly newer offered version replaces a present supported engine, an equal or older one never replaces it, and no successful run leaves an engine older than the one found.: pass — Replacement decisions are unchanged; the only changed input is how the present version is obtained, which now matches the engine's real answer instead of failing and falling back to the no-engine path that could install an equal or older version.
- FR-5, AC-5: a second default run installs no engine, leaves the same engine version and one usable client installation.: pass — Nothing in the installer's installation or launcher steps changed; the second run now reads the engine it installed correctly, so the repeat scenario reports no engine work. Covered by the reported consecutive default-run e2e.
- FR-6 (unorderable version): a present version that cannot be ordered never satisfies the minimum and is replaced by a supported offered version.: pass — The ordering helper and the minimum check are untouched; an unreadable or unorderable answer leads to obtaining a supported offered version, as before.
- FR-7, AC-7: a run that cannot reach a supported engine fails with the required minimum, the found or offered version and the user action; client-only, removal and no-profile-edit runs behave as before with respect to the engine.: pass — The failure-reporting and client-only/uninstall/no-profile-edit branches are outside the diff; only the version-reading function changed, so those paths keep their behaviour and messages.
- AC-6: with no engine installed at all, the run still obtains a supported offered version and states the version and how it was obtained.: pass — The absent-engine path is unchanged: the present-version function returns failure when no engine can be asked, and the offered version is obtained from the engine's own installer as before; covered by the environment e2e runs.
- Non-goals respected: no change to the declared minimum, the offered-version discovery, engine installation, version ordering, the client's startup compatibility check, shell startup handling, launcher verification or the bounded fresh-shell check, and no new installation option.: pass — The diff touches only the present-version reading, its stub and tests, and the changelog; no switch, configuration knob, ordering rule or startup/profile logic is altered.
- Tests: no test is deleted or weakened, and the change adds a regression guard for the defect.: pass — No test removal was detected. The stub engine was made stricter (only the documented report answers, anything else is a structured non-zero answer), the test-side version probe follows the documented form, and a new test pins the exact question, the absence of installation and the kept output — this strengthens, not weakens, the suite.
- Documentation is text: the changelog entry is accurate, behavior-level and free of volatile implementation detail.: pass — The added bullet under Fixed states the defect and the resulting keep/replace/repeat behaviour without naming files, flags, timings or environment specifics, and no automated check reads documentation.
- The commit contains every file the change needs and no unrelated, temporary, debug or generated file.: pass — The four attributed files (installer, engine stub, engine installer tests, changelog) are exactly what this fix needs; the worktree is clean and no escalated or stray file is present.

## Blocking

- none

## Test Removals

- none


