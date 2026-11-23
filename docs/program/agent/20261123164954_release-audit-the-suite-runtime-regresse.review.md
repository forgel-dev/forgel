# Task Review: Release audit: The suite runtime regressed past the bound the release established. Task 2026112

- Task: `20261123164954_release-audit-the-suite-runtime-regresse`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T18:45:27+00:00

## Summary

The attributed change is a documentation-only edit: README's `## Tests` section loses the 'under 120 seconds (about two minutes)' completion-time/budget sentence while keeping every coverage statement the requirements demand (one command runs the whole suite with no environment variable, marker or default option leaving a test out; the installer scenarios run the real `install.sh` with a real install through `pip` into a temporary home directory and a real detected login shell), and it adds the missing 'and no network access' clause next to the standard-library-only statement, so the guidance now matches FR-3. The CHANGELOG entry that previously recorded the two-minute release-audit bound and the concrete one-second limit was rewritten to describe the speed-up without any figure, and a new entry records the removal of the runtime claim; the removal is done by deleting the detail rather than by tuning code or a limit, exactly as the rule requires. Client commands, options, output form, session behaviour and the installer's install/update/uninstall text are untouched, all text is English, no test was added, weakened or deleted, and no timing, duration or runtime bound remains in the reviewed documentation (README.md, CHANGELOG.md). Verification is review-only and QA was skipped, which is the correct handling for a documentation task.

## Requirements

- No project documentation states a suite completion time, duration or runtime bound (FR-1, AC-1).: pass — The README sentence 'it completes in under 120 seconds (about two minutes) on a development machine. That budget covers ...' is gone; the surviving text states coverage only. The CHANGELOG entry citing 'the release audit's two-minute bound' and 'a one-second limit' was rewritten without any figure, and the new entry promises no time. No other statement of a suite time, duration or bound remains in the reviewed documentation.
- The guidance still says one documented command runs the whole suite with nothing configured or selected that leaves a part out (FR-2, AC-2).: pass — README keeps `python -m unittest discover -s tests` and the sentence 'That command runs the whole suite — no environment variable, marker or default option leaves a test out'; only the timing clause after the dash was removed, so the claim now stands alone and is still complete.
- The guidance still says the installer situations are covered, that they perform a real installation into a throwaway home location with a real detected login shell, and that a source-checkout run needs only the Python standard library and no network access (FR-3, AC-2).: pass — 'it covers the installer scenarios too, which run the real `install.sh` with a real install through `pip` into a temporary home directory and a real detected login shell' is retained, and the lead sentence now reads 'needs nothing but the Python standard library and no network access', which the previous text lacked. Both halves of FR-3 are present.
- Every statement about how to run the suite and about what such a run covers is true of the project as it stands (FR-4, AC-3).: pass — The remaining statements describe behaviour (the discovery command, the absence of skips, the installer scenarios, stdlib-only and offline) and no longer assert a figure the measured run contradicts; the removed claim was the only statement that did not hold. The neighbouring pytest paragraph is unchanged and refers to the same suite via the declared `test` extra.
- Documented client commands, options, output form, session behaviour and the installer's install, update and uninstall behaviour are unchanged (FR-5, AC-4).: pass — The README diff touches only the `## Tests` section; the Install, Options, Update, Uninstall, Commands, Output, Active project and Timeout sections are byte-identical, and CHANGELOG edits are descriptions of previously shipped behaviour, not documentation of it.
- All project documentation is written in English (FR-6, AC-5).: pass — Both changed documents are entirely English.
- The fix is documentation-only: no product, test, limit or timing change, no automated check that reads a documentation file, no release action (constraints and non-goals).: pass — Only CHANGELOG.md and README.md changed; no code, test, harness or limit was touched, no test was added or removed (none reported by the harness), the release audit's external two-minute budget is left alone, and nothing is published or tagged.

## Blocking

- none

## Test Removals

- none


