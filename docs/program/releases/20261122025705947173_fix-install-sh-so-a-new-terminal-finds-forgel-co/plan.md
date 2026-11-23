# Release plan 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Project: `forgel-1d2bf685`
- Request: Fix install.sh so a new terminal finds forgel-code on PATH
- Class: patch
- Status: released
- Created: 2026-11-22T02:57:06+00:00


## Request

The installer currently completes while the launcher directory never reaches PATH in a freshly opened terminal. It picks the profile file from $SHELL alone: on macOS a bash login shell never reads ~/.bashrc, and under `curl … | sh` $SHELL can be empty, sending the block to ~/.profile while the terminal reads ~/.zshrc. It also never checks that its own change took effect. This change makes the installer detect the real login shell, write the block into a profile file a new terminal actually reads, start a clean login shell afterwards and verify that `forgel-code` resolves, and fail with a message naming the edited file and the observed PATH when it does not. --uninstall removes the block from every profile file the installer can have written.

## Repositories

- `code` — released, preset python, base 0.1.0, releases 0.1.1

## Tasks

- `20261122025705_fix-install-sh-so-a-new-terminal-finds-f` — Fix install.sh so a new terminal finds forgel-code on PATH (code, done)
- `20261122034544_release-audit-uninstall-no-longer-honors` — Release audit: --uninstall no longer honors FORGEL_CODE_PROFILE. The old code removed the block (code, done)
- `20261122034544_release-audit-uninstall-omits-bashrc-alt` — Release audit: --uninstall omits ~/.bashrc, although the previous installer wrote the marked bl (code, done)
- `20261122062911_make-install-sh-put-forgel-code-on-path-` — Make install.sh put forgel-code on PATH for a new terminal (code, done)
- `20261122174453_make-the-install-sh-path-check-strictly-` — Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install (code, done)
- `20261122192217_release-audit-remove-profile-block-and-u` — Release audit: `remove_profile_block` and `uninstall_profile` remove a block whenever `# >>> fo (code, done)
- `20261122192217_release-audit-the-final-task-s-recorded-` — Release audit: The final task's recorded test run shows only `timed out after 120s` and partial (code, done)
- `20261123062514_release-audit-bounded-run-does-not-make-` — Release audit: `bounded_run` does not make the watchdog's timeout decision authoritative. After (code, done)
- `20261123062514_release-audit-on-a-successful-check-boun` — Release audit: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check` (code, done)
- `20261123062514_release-audit-readme-md-still-documents-` — Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo (code, done)
- `20261123164954_release-audit-bounded-run-clears-check-c` — Release audit: bounded_run clears CHECK_CHILD before calling cleanup_check, and install.sh deli (code, done)
- `20261123164954_release-audit-install-sh-s-bounded-run-s` — Release audit: install.sh's bounded_run still decides the timeout by testing for the timed-out (code, done)
- `20261123164954_release-audit-the-suite-runtime-regresse` — Release audit: The suite runtime regressed past the bound the release established. Task 2026112 (code, done)

## Audit

- Rounds: 3
- Verdict: pass
- Report: `docs/program/releases/20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co/audit.md`
