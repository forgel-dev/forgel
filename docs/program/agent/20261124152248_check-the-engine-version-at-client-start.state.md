# Session State: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Session: 5
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- R-1: The client declares exactly one minimum supported engine version. That value cannot be overridden, lowered or skipped by any option, setting or configuration the user controls, and the value shown to the user is the same value enforced before use, with no second copy that could differ.
- R-2: Asking the client for its own version prints the client version and the declared minimum engine version, exits successfully, and works on a machine with no engine installed, sending nothing to the engine.
- R-3: The client's usage help is produced and exits successfully on a machine with no engine installed, sending nothing to the engine.
- R-4: Before the client first uses the engine in an invocation, it confirms that the engine is present and asks the version the engine reports about itself, and carries that result through the rest of the invocation. Reporting the client's own version and printing usage help are exempt from this confirmation.
- R-5: When the engine cannot be found or cannot be started, the invocation fails with one message that names the engine, states that the client requires it, and contains a single-line instruction that installs the engine and can be pasted and run unchanged. The requested work is not attempted, and the message never leaves the user with the low-level operating-system error text as the only thing shown.
- R-6: When the engine reports a version below the declared minimum, the invocation fails with one message that names the required minimum version, the version found and a single-line instruction that installs a newer engine and can be pasted and run unchanged. The requested work is not attempted.
- R-7: When the engine answers but no version can be confirmed from its answer, the invocation fails in the same actionable shape as the too-old case: it states that compatibility could not be confirmed, names the required minimum version and carries the upgrade instruction. The requested work is not attempted.
- R-8: When the engine reports the declared minimum or a newer version, the requested operation proceeds exactly as before: the same requests reach the engine, the human-readable and machine-readable output is unchanged, and the exit status is unchanged.
- R-9: Versions compare as sequences of numeric components, numerically, one component at a time from the first. A version with fewer components equals the same version with trailing zero components, a leading version marker and any non-numeric suffix after the numeric components do not affect the outcome, and a larger later component counts as newer even when its text is longer.
- R-10: The engine's version is requested at most once per invocation. After a failed confirmation the invocation sends no request of its own to the engine.
- R-11: In the client's machine-readable output form, the missing-engine and the not-compatible failures each surface as exactly one failure result carrying the same message and a non-zero exit status, consistent with the client's other failures.
- R-12: Starting the interactive session performs the same confirmation first. With a missing, too-old or unconfirmable engine the session prints the actionable message and exits non-zero without opening a prompt.
- R-13: The client never installs, upgrades or otherwise modifies the engine; every failure path only reports what the user can do.

## Acceptance Criteria

- AC-1: With no engine installed, asking the client for its version exits successfully and prints the client version together with the declared minimum engine version, and no request reaches an engine. Check: repository test gate exercises the version request with no engine available and asserts the printed pair and the successful exit.
- AC-2: With no engine installed, the client's usage help is printed and exits successfully, and no request reaches an engine. Check: repository test gate exercises the help request with no engine available.
- AC-3: With no engine installed, an operation that needs the engine exits non-zero and prints one message that names the engine, says the client requires it, and contains a single-line install instruction readable and pasteable as printed; the printed text is not the bare low-level operating-system error. Check: repository test gate runs an engine-backed operation with no engine and asserts the named engine, the requirement statement and the pasted instruction line.
- AC-4: With an engine reporting a version below the declared minimum, an engine-backed operation exits non-zero, prints one message naming the required minimum, the version found and a single-line upgrade instruction, and the engine receives no request from the operation itself beyond the version question. Check: repository test gate uses an engine reporting an older version and asserts the message content and that no operation request was made.
- AC-5: With an engine that answers but reports no usable version, an engine-backed operation exits non-zero with the same actionable shape as the too-old case, and the engine receives no request from the operation itself. Check: repository test gate uses an engine whose answer carries no version and asserts the actionable message and the absence of an operation request.
- AC-6: With an engine exactly at the declared minimum and with an engine newer than it, every engine-backed operation and the interactive session behave as before: the same requests reach the engine, the same human-readable output appears and the exit status is unchanged. Check: repository test gate exercises the operations against both engines and compares the requests, text and exit statuses with the behaviour that precedes this change.
- AC-7: An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0, and an engine reporting 0.9.0 is accepted against a declared minimum of 0.9.0. Check: repository test gate exercises both comparisons.
- AC-8: An engine reporting the declared minimum with a non-numeric suffix is accepted as equal to the minimum. Check: repository test gate exercises that engine answer.
- AC-9: An invocation that uses the engine several times causes the engine's version to be asked at most once, and a failed confirmation leaves the engine with no request from the operation itself. Check: repository test gate counts the requests the engine receives in both situations.
- AC-10: In the machine-readable output form, a missing-engine failure and a too-old-engine failure each yield exactly one failure result carrying the same message as the human-readable form and a non-zero exit status. Check: repository test gate exercises both failures in the machine-readable form and asserts one result, the message and the exit status.
- AC-11: Starting the interactive session with no engine installed prints the install guidance and exits non-zero without ever showing a prompt, and the same holds for a too-old engine. Check: repository test gate starts the session against an absent and an old engine and asserts the guidance, the non-zero exit and the absence of a prompt.
- AC-12: The minimum engine version printed by the version report and the one enforced before use are identical, and no user-facing option, setting or configuration changes the enforced value. Check: review compares the reported value with the enforced value and inspects the client's options and settings for any way to skip or lower it.
- AC-13: The install and upgrade instruction lines shown in the failure messages are complete single lines that a user can paste into a terminal and run unchanged. Check: review reads the messages and judges the instruction lines to be complete and runnable as printed.

## Constraints

- The client remains a thin surface over the engine's parameterized commands: it calls no model, reads no project and runs no check itself.
- The client omits nothing the engine provides and adds no capability of its own; only the confirmation described here is added.
- Only one minimum supported engine version exists in the client, and it is a fixed value rather than a user setting.
- The engine version is asked through the engine's own version reporting and the answer is the only source of the engine's version.
- An engine whose version cannot be confirmed is treated as not compatible; the client never proceeds on an unconfirmed engine.
- The client never imports the engine or shares a process with it.
- All user-facing messages produced by this task are English.
- The client's existing failure convention is reused for these failures instead of introducing a second shape.
- Nothing in the engine changes, and the client does not install or upgrade the engine.

## Assumptions

- none

## Files Changed

- forgel_code/cli.py

## Actions

- read_file: forgel_code/commands.py
- read_file: forgel_code/session.py
- read_file: forgel_code/render.py
- read_file: forgel_code/cli.py
- read_file: forgel_code/compat.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/interactive.py
- read_file: tests/stub_engine.py
- read_file: tests/test_cli.py
- read_file: tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['git', 'diff', 'forgel_code/cli.py']
- run: ['git', 'show', '--stat', '--oneline', 'HEAD']
- run: ['git', 'grep', '-n', '0.1.0', '--', 'install.sh', 'forgel_code', 'tests']
- read_file: README.md
- run: ['git', 'ls-files']
- read_file: forgel_code/__main__.py
- read_file: tests/stub_engine_install.py
- read_file: tests/test_install_engine.py
- read_file: tests/test_install.py

## Commands

- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 1
- `['git', 'diff', 'forgel_code/cli.py']` -> exit 0
- `['git', 'show', '--stat', '--oneline', 'HEAD']` -> exit 0
- `['git', 'status', '--porcelain']` -> exit 0
- `['git', 'diff']` -> exit 0
- `['git', 'log', '--oneline', '-8']` -> exit 0
- `['git', 'show', '--stat', 'HEAD']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 1
- `['git', 'diff', 'forgel_code/cli.py']` -> exit 0
- `['git', 'show', '--stat', '--oneline', 'HEAD']` -> exit 0

## Recent Observations

- read_file tests/stub_engine_install.py: tests/stub_engine_install.py: lines 1-137 of 137
- read_file tests/test_install_engine.py: tests/test_install_engine.py: lines 1-272 of 272
- read_file tests/test_install.py: tests/test_install.py: lines 1-1937 of 1937

## Next Step

Continue from the current repository state and the changed files.
