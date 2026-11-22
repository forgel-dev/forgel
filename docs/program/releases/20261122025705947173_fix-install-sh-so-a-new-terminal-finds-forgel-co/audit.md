# Release audit 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Round: 1
- Verdict: fail
- At: 2026-11-22T03:45:44+00:00

## Summary

The install/profile-selection and fresh-shell verification changes match the main requirements and the recorded suite passes, but --uninstall is incomplete. It only cleans six hard-coded files, so blocks written through the documented FORGEL_CODE_PROFILE override and legacy ~/.bashrc blocks from the previous installer are left behind. That breaks the uninstall contract and is a regression from the previous uninstall.

## Findings

- [major] code: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block from the overridden profile; the new loop only visits PROFILE_NAMES, so a custom profile edited by a successful or failed install keeps the marked PATH block after uninstall. — Add ${FORGEL_CODE_PROFILE:-} to the uninstall candidate set when it is set (deduplicate against PROFILE_NAMES), and add a test that installs and uninstalls with a custom profile path.
- [major] code: --uninstall omits ~/.bashrc, although the previous installer wrote the marked block there for bash when ~/.bashrc existed or when no ~/.bash_profile existed. Upgrading and uninstalling therefore leaves the old PATH block behind. — Include ~/.bashrc in the legacy cleanup set for uninstall, update the README list, and extend CANDIDATE_PROFILES/test_uninstall_clears_every_candidate_profile to cover it.
