# Release audit 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Round: 1
- Verdict: fail
- At: 2026-11-23T06:25:08+00:00

## Summary

The installer implementation and the final recorded test run cover most of the requested behavior, but the release is not ready: the README still sends users to the v0.1.0 installer for both install and uninstall, so new users do not get the fixed installer and the documented uninstall does not perform the new cleanup. The bounded fresh-shell check also has a timeout race and does not clean processes started by a successful login-shell check.

## Findings

- [major] code: README.md still documents `.../v0.1.0/install.sh` for the install command and for the uninstall command, while the release describes v0.1.1 behavior. The v0.1.0 script predates the login-shell detection, fresh-shell verification, guarded block, cross-profile uninstall, and FORGEL_CODE_PROFILE cleanup, so a new user following the documentation still gets the original PATH bug and an uninstall that can leave the new block/separator and override-profile block behind. — Update both documented commands to the current release installer (v0.1.1 or a versionless latest URL) and add a README guard test that asserts the install and uninstall commands use the release installer.
- [major] code: `bounded_run` does not make the watchdog's timeout decision authoritative. After the checked shell exits, the parent immediately kills the watchdog if the `timed-out` marker is absent. If the shell finishes after the configured limit but before the watchdog has written the marker, the check can be reported as successful, so the hard bound and the rule that a timed-out check is a failure are not guaranteed. — Have the watchdog record the final child/timeout status and wait for that status before deciding success, or measure the deadline in the parent and fail on any overrun; add a test whose checked shell returns just after FORGEL_CODE_TIMEOUT.
- [major] code: On a successful check, `bounded_run` clears `CHECK_CHILD` before `cleanup_check` and never signals the checked login shell's process group or descendants. A profile that starts a background process leaves that process running after the check, contrary to the requirement that no process started by the check remains. The timeout path also relies on a process-tree walk and does not preserve a dedicated group for cleanup. — Run the checked shell in its own process group/session (with stdin/stdout detached so an interactive shell does not stop) and terminate that group after every outcome, including success; otherwise reliably enumerate and kill descendants before clearing `CHECK_CHILD`. Add a test with a profile that starts a background process.
