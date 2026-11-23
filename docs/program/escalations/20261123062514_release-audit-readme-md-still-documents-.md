# Escalated changes

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Title: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

These files stayed uncommitted because they are unrelated to the task. The planner decides: a separate task when the change is needed, or removal when it is unnecessary, partial or harmful.

| Path | Reason |
|---|---|
| `install.sh` | The bounded fresh-shell check rework (watchdog, dedicated process group, cleanup on every exit path) is a separate task's change set, not part of the README install-URL fix; it must stay uncommitted for the planner. |
| `tests/test_install.py` | The late/login-shell and withheld-watchdog tests exercise the same separate install.sh rework; they are unrelated to this task and must stay uncommitted. |
| `tests/test_check_cleanup.py` | Untracked new module asserting the reworked check's process-group cleanup; unrelated to this README task and must remain uncommitted. |
