# Release audit 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Round: 3
- Verdict: pass
- At: 2026-11-23T18:57:35+00:00

## Summary

The release delivers the requested installer behaviour and its follow-up audits: login-shell detection ($SHELL, then invoking process, then account login shell, then /bin/sh), per-shell profile selection (zsh ~/.zshrc; bash first existing of ~/.bash_profile/.bash_login/.profile or a created ~/.bash_profile; POSIX ~/.profile with a warning), a guarded, byte-stable, idempotent marked block, bounded fresh-login-shell verification that only reports success when `command -v forgel-code` equals the newly written launcher and otherwise fails non-zero naming the file, block, shell and observed PATH, and `--uninstall` that strips the block from every candidate profile (.zshrc, .zprofile, .zshenv, .bash_profile, .bash_login, .profile, .bashrc) plus FORGEL_CODE_PROFILE without creating or altering other lines. README and CHANGELOG were updated to match, the earlier v0.1.0 URL and 120-second runtime claim were removed, and the recorded suite runs complete with 218 tests passing. No blocking defect was found; remaining items are non-blocking hardening/cleanup observations.

## Findings

- [minor] code: When /dev/urandom or od is unavailable, random_token falls back to `$$$$$$`, making the private `forgel-code-check` directory name predictable under a shared ${TMPDIR:-/tmp}; another local user could pre-create or guess the path (the mkdir -m 700 retry mitigates but does not remove the predictability). — Fail closed (diagnose and abort the check) or derive the token from another non-predictable source instead of the PID when /dev/urandom and od are unavailable, and keep the owner-only mkdir check.
- [minor] code: On the success path bounded_run reaps the watchdog but leaves CHECK_WATCHER set, so cleanup_check sends TERM to an already-reaped PID; if the PID were reused in that window an unrelated process could be signalled. — Clear CHECK_WATCHER after the successful wait in bounded_run before cleanup_check runs, or have cleanup_check skip signalling when the watcher has already been reaped.
- [minor] code: The CHANGELOG [Unreleased] 'Changed' entry describes volatile implementation detail of the test suite ('one read-only checkout copy and one prepared installation per scenario group... configure a limit below the product default'), which D-109 asks documentation not to carry. — Reword the entry to state the outcome (a faster suite with unchanged coverage) without internal test structure or limit/timing detail.
