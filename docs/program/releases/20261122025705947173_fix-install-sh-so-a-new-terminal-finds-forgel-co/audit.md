# Release audit 20261122025705947173_fix-install-sh-so-a-new-terminal-finds-forgel-co

- Round: 1
- Verdict: fail
- At: 2026-11-23T06:19:10+00:00

## Summary

The release meets the main install.sh PATH requirements and the final suite passes, but the bounded fresh-shell verification is unsafe and incomplete: the checked shell is never placed in its own process group, the root is reaped before the grace-period KILL, and the cleanup can leave reparented descendants or signal a recycled PID. This violates the bounded-check cleanup contract and can affect unrelated processes. Two smaller evidence/edge-case gaps are also present.

## Findings

- [critical] code: `bounded_run` starts the checked login shell in the installer's own process group. Because `signal_run` compares the checked process's pgid with `$$`, it always falls back to `process_tree` and never signals a dedicated group. At timeout the watcher sends TERM, then waits `VERIFY_GRACE` before KILL, while the main path's `wait "$child"` reaps the root immediately. Descendants that outlive the root are reparented and disappear from the process tree, so they can survive the cleanup; the delayed KILL also targets an already-reaped PID, which can be reused and cause an unrelated process or process group to be killed. — Run the checked command in a private process group and signal that group, or keep the root unreaped until the watcher finishes and verify PID identity/start time before any delayed kill. Ensure cleanup also covers descendants that have been reparented after the root exits.
- [minor] code: `remove_profile_block` identifies the installer's `MARKER_SEPARATOR` solely by line content and end-of-file position. If a user's file ends with that exact comment and a final newline, the uninstall removes the user's line. If content follows the block, the separator can be left behind instead of being removed. — Record the separator's presence with a distinct, non-user-reproducible marker or encode the original trailing-newline state in the block itself, so removal never infers it from ordinary line content.
- [minor] code: Task 7 requirement R10/AC8 calls for measured before/after per-module or per-test durations. The review states those numbers were not in its context, so the speedup diagnosis is not evidenced in the provided audit artifacts. — Attach or record the measured before/after durations in the task report so the runtime reduction is verified rather than inferred.
