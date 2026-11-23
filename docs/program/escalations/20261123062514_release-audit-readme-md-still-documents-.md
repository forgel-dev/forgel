# Escalated changes

- Task: `20261123062514_release-audit-readme-md-still-documents-`
- Title: Release audit: README.md still documents `.../v0.1.0/install.sh` for the install command and fo

These files stayed uncommitted because they are unrelated to the task. The planner decides: a separate task when the change is needed, or removal when it is unnecessary, partial or harmful.

| Path | Reason |
|---|---|
| `install.sh` | The bounded fresh-shell check rework (watchdog, dedicated process group, cleanup on every exit path) belongs to a separate change set and is unrelated to the README install-URL fix. |
| `tests/test_install.py` | The late/login-shell and withheld-watchdog tests exercise the separate install.sh rework; unrelated to this task. |
| `tests/test_check_cleanup.py` | Untracked new module asserting the reworked check's process-group cleanup; part of the separate install.sh task, not this README task. |
