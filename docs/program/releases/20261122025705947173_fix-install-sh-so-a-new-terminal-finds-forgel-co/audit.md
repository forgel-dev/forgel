# Release audit 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Round: 1
- Verdict: fail
- At: 2026-11-22T19:21:49+00:00

## Summary

The change set largely implements the requested shell detection, profile selection, fresh-shell verification, uninstall cleanup, documentation and tests, but it cannot be published as-is. The recorded full-suite run for the final task timed out after 120 seconds and never completed, so the required full-suite acceptance is unverified. The block-removal logic also treats an unmatched start marker as an open block and deletes every following line, risking loss of unrelated profile content.

## Findings

- [major] code: The final task's recorded test run shows only `timed out after 120s` and partial progress, with no completed passing suite. The acceptance criterion that the full repository test suite passes is therefore not evidenced, so a required check is left unverified. — Run the complete suite with an adequate timeout, fix or shorten any slow/hanging bounded-check tests (for example by setting a short `FORGEL_CODE_TIMEOUT` in those tests), and record the completed passing output.
- [critical] code: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> forgel-code >>>` is present. If that start marker has no matching `# <<< forgel-code <<<`, the AWK keeps `inside = 1` to EOF and deletes every line after the marker. Install re-runs and uninstall can therefore destroy unrelated profile content, contrary to the requirement to remove only the delimited block and leave every other line unchanged. — Only remove a block when both the start and matching end marker are present. If the end marker is missing, leave the file unchanged (or restore the original content), and add regression tests for an unmatched start marker on both install and uninstall paths.
