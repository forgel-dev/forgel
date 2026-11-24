# Task Review: Release audit: `forgel_code/cli.py` changes the argparse description to include `Run it without

- Task: `20261124131129_release-audit-forgel-code-cli-py-changes`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T13:34:45+00:00

## Summary

The attributed change does exactly what the release audit finding requires: `forgel_code/cli.py` drops the appended sentence "Run it without a command to open the interactive session." from the argparse `description`, leaving "Thin console client for Forgel over the engine's machine-readable commands." — the sentence the audit identified as the sole addition, so removing it restores the previously released wording with no other line in the file (usage text, option help, subcommand help, version output, or one-shot handling) touched. The no-argument path still routes to `run_interactive()`, so the interactive session remains reachable as required, and every other command path is byte-identical because no other code changed. The newly added `tests/test_cli_help_description.py` does not assert the removed sentence (it asserts its absence and pins the restored text, both in-process and through a real `--help` subprocess run), so FR-4 is satisfied and no existing test was deleted or weakened. The change set contains only the description restoration and the accompanying help-assertion test; no temporary, debug or generated artifact was committed. QA reports the environment gate and the full suite as passing, and the two review-only criteria (identical previous-release wording, scoped change set) hold when the diff is read. The only observation, non-blocking, is that the new test also rejects the bare word "interactive" anywhere in the help output, which is slightly stronger than the requirement but consistent with it and does not constrain current product behavior.

## Requirements

- FR-1 / AC-1: the help output's description contains no sentence advertising the interactive session and matches the previous release text.: pass — The description now reads "Thin console client for Forgel over the engine's machine-readable commands."; the appended interactive-session sentence is gone.
- AC-2: the description text is identical to the previous release with no other wording change.: pass — The diff removes only the added sentence from the concatenated description string; no other line of cli.py is modified, so no other help-visible wording (usage, options, subcommands, version) changed.
- FR-2 / AC-3: running the program with no command still opens the interactive session.: pass — `main()` keeps the empty-argv branch returning `run_interactive()`; that path was not touched, and the environment/acceptance checks for it passed.
- FR-3: every existing one-shot usage produces the same output as before, including failures and exit statuses.: pass — Only the parser `description` string changed; argument parsing, engine invocation, error reporting and exit codes are untouched.
- FR-4: no automated test asserts the presence of the removed interactive-session sentence in the help output.: pass — The added test asserts the released sentence is present and that 'interactive' is absent from help; no test asserts the removed sentence, and no test was deleted or weakened.
- FR-5 / AC-5: the change set contains only the description restoration and any test adjustment needed by it, with no unrelated, temporary or generated files.: pass — Two files: the description fix in forgel_code/cli.py and one help-description test that pins the restored wording and the absence of interactive advertising; nothing else, no artifacts.
- AC-4: all tests in the project's test suite pass.: pass — QA verdict pass, with the environment test, both e2e checks and the acceptance commands exiting 0.
- Quality of the added test: not a weakening, not documentation-reading, and consistent with the corrected output.: pass — The new test exercises parser state, formatted help and a real `--help` process run; it verifies rather than weakens behavior. Its blanket 'no interactive in help' assertion is marginally stronger than FR-4 but does not conflict with any requirement.

## Blocking

- none

## Test Removals

- none


