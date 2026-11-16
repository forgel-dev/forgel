# User Decisions

Product decisions explicitly stated by the user. They are binding requirements:
a requirements or specification document must carry the relevant decisions and
must not re-open them. A later decision overrides an earlier one.

| ID | Decision | Source |
|----|----------|--------|
| D-001 | The interactive client moves to a separate public repository in the same organization as the engine. | User, 2026-11-16 21:14 |
| D-002 | The client is a thin UI over the engine's parameterized commands. It does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | User, 2026-11-16 18:31 |
| D-003 | The base parameterized command line (`forgel <command>`) stays in the engine. The separate client replaces the interactive chat mode. | User, 2026-11-16 18:31 |
| D-004 | The client's working name is Forgel Code. It is a Python client installed as `forgel-code`, follows a Pareto 20/80 scope and imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| D-005 | The second repository is public and lives in the same organization as the first (`forgel-dev`). | User, 2026-11-16 21:14 |
| D-006 | The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| D-007 | The single free-text engine entry point is `forgel say`. Every client-facing operation is a parameterized command with an optional single JSON object on stdout; the active project is an engine-side session with the default key `local`. | User accepted the proposal, 2026-11-16 18:34 |
