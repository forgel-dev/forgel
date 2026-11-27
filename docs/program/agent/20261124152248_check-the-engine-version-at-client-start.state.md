# Session State: Check the engine version at client startup

- Task: `20261124152248_check-the-engine-version-at-client-start`
- Session: 4
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- The client declares exactly one minimum supported engine version; the value it shows the user is the same value it enforces before using the engine, and no user-controlled option or setting lowers, skips or overrides it.
- Asking the client for its own version reports the client version together with the declared minimum supported engine version, ends successfully, works on a machine with no engine installed, and contacts no engine.
- The client's usage help is produced and ends successfully on a machine with no engine installed, and contacts no engine.
- Reporting the client's version and printing usage help are the only surfaces exempt from engine confirmation; every other client operation confirms the engine before doing anything else.
- Before the client first uses the engine in an invocation it confirms that the engine is present and asks the engine the version it reports about itself, and carries that result through the rest of the invocation.
- The engine's version is asked at most once per invocation.
- After a failed confirmation the invocation makes no further request to the engine and does not attempt the requested work.
- When the engine cannot be found or cannot be started, the invocation fails with one message that names the engine, states that the client requires it, and contains one line that installs a current engine and can be copied and run unchanged; the low-level system error text is never the only thing the user sees.
- When the engine reports a version below the declared minimum, the invocation fails with one message that names the required minimum version, the version found, and one line that installs a newer engine and can be copied and run unchanged; the requested work is not attempted.
- When the engine answers but no version can be confirmed from its answer, the invocation fails in the same actionable shape as the too-old case: it states that compatibility could not be confirmed, names the required minimum version and carries the line that installs a newer engine; the requested work is not attempted.
- The installation line carried by every failure message is one complete line that a user can copy and run unchanged; the same line serves the missing and the too-old case because running it installs a current engine in either situation.
- Versions compare as sequences of numeric components, numerically, one component at a time from the first; a version with fewer components equals the same version with trailing zero components; a leading version marker and any non-numeric suffix after the numeric components do not affect the outcome; a larger later component counts as newer even when its text is longer; the declared minimum is an inclusive lower bound.
- When the engine reports the declared minimum or a newer version, the requested operation behaves exactly as before: the same requests reach the engine, the human-readable and structured output is unchanged, and the outcome is unchanged.
- The client never installs, upgrades or otherwise modifies the engine; every failure path only reports what the user can do.
- When the client reports a failure in its structured form, a missing engine and a not-compatible engine each appear as exactly one reported failure carrying the same message as the plain form and a non-zero outcome, consistent with the client's other failures.
- Starting the interactive session performs the same confirmation first; with a missing, too-old or unconfirmable engine the session prints the actionable message and ends with a non-zero outcome without opening a prompt.

## Acceptance Criteria

- With no engine installed, asking the client for its version ends successfully and reports the client version together with the declared minimum engine version, contacting no engine. Check: review observes the version request on a machine without the engine and confirms the reported pair, the successful outcome and the absence of engine contact.
- With no engine installed, the client's usage help is printed and ends successfully without contacting an engine. Check: review observes the help request on a machine without the engine and confirms the printed help, the successful outcome and the absence of engine contact.
- An engine reporting a version one numeric component below the minimum shown by the version report is refused as too old, and an engine reporting exactly that shown minimum is accepted. Check: review observes both boundary cases against the value the version report shows.
- No user-facing option or setting lowers, skips or overrides the enforced minimum. Check: review compares the shown and enforced values and inspects the client's options and settings.
- An invocation that asks the engine for several things causes the engine's version to be asked at most once. Check: review observes such an invocation and counts the version questions the engine receives.
- A failed confirmation leaves the engine with no request beyond the version question, whether the engine is too old or reports no usable version. Check: review observes both failure cases and confirms that no operation request followed.
- Every operation covered by the confirmation asks the engine about its version before any other request. Check: review observes the order of the requests such an operation makes to the engine.
- With no engine installed, an operation that needs the engine fails and prints one message that names the engine, says the client requires it, and contains a single installation line that can be copied and run unchanged; the low-level system error is not what the user sees alone. Check: review reads the message produced without an engine.
- With an engine older than the declared minimum, an operation fails and prints one message naming the required minimum, the version found and a single installation line, with no work attempted. Check: review reads the message produced against an older engine and confirms that no work was attempted.
- With an engine that answers but reports no usable version, the operation fails in the same actionable shape, names the required minimum and carries the installation line. Check: review reads the message produced against an engine that reports no version and compares its shape with the too-old message.
- The installation lines shown in the failure messages are complete single lines that can be copied and run unchanged. Check: review judges the printed lines to be complete and runnable as printed.
- An engine reporting 0.10.0 is accepted against a declared minimum of 0.9.0; an engine reporting 0.9.0 is accepted against a minimum of 0.9.0; a minimum reported with a non-numeric suffix or with trailing zero components is accepted as equal; a leading version marker changes nothing. Check: review observes each of these comparisons.
- With an engine exactly at the declared minimum and with a newer engine, every operation and the interactive session behave as before: the same requests reach the engine, the same output appears and the outcome is unchanged. Check: review compares this behaviour with the behaviour that precedes the change.
- The client never installs, upgrades or modifies the engine: after each failure path nothing is installed, and an engine that was present keeps its version and content. Check: review observes the engine's state after the missing-engine and too-old failure paths.
- When the client reports in its structured form, a missing engine and an engine below the minimum each yield exactly one reported failure carrying the same message as the plain form and a non-zero outcome. Check: review observes both failures in the structured form and compares the message and the outcome with the plain form.
- Starting the interactive session with no engine, or with an engine below the minimum, prints the actionable message and ends with a non-zero outcome without ever showing a prompt, and the engine receives no request beyond the version question. Check: review observes the session start against an absent and an older engine.

## Constraints

- Only the client changes; the engine, the engine's installer and the version the engine reports stay as they are.
- The client stays independent of the engine and never installs, upgrades or modifies it.
- Every user-facing message is English.
- The declared minimum is a client-owned value chosen by the developer as the oldest engine that answers the client's needs; it is not a user setting.
- Failures reuse the client's existing failure reporting conventions; no second failure shape is introduced.
- The project's existing cross-repository verification remains the proof that the real engine and the real client work together; it is neither replaced nor relaxed.
- The confirmation is exercised through the client's real startup path and is never bypassed.
- User documentation and release notes are not updated here; the milestone plans them separately.

## Assumptions

- none

## Files Changed

- forgel_code/cli.py
- forgel_code/interactive.py
- tests/stub_engine.py
- tests/test_cli.py
- tests/test_cli_extra.py

## Actions

- search_files: --version|minimum_engine_version|forgel-code 0\.2\.0 @ tests
- search_files: def default_engine|def show_failure|def write @ forgel_code/interactive.py
- search_files: stub_engine|STUB_ENGINE\b @ tests
- search_files: FORGEL_STUB_SLEEP|FAKE_ENGINE_SLEEP|SESSION_STUB_SLEEP|124 @ tests
- read_file: forgel_code/interactive.py
- search_files: interactive\.run\(|compat|confirm @ tests
- read_file: tests/stub_engine.py
- edit_file: forgel_code/interactive.py
- search_files: main\(\[\]\)|interactive\.run\(|run_interactive @ tests
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- edit_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- edit_file: tests/stub_engine.py
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract', 'tests.test_interactive']
- read_file: tests/stub_engine.py
- run: ['python3', '-m', 'unittest', 'tests.test_stub_contract']

## Commands

- `['git', 'show', '--name-only', 'HEAD']` -> exit 0
- `['git', 'show', '--name-status', '36510fb']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 1
- `['git', 'status', '--porcelain', '--untracked-files=all']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 1
- `['git', 'diff', '--', 'forgel_code/interactive.py', 'tests/test_cli_extra.py', 'tests/test_cli.py']` -> exit 0
- `['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']` -> exit 1
- `['python3', '-m', 'unittest', 'tests.test_stub_contract', '-v']` -> exit 1
- `['python3', '-m', 'unittest', 'tests.test_stub_contract', 'tests.test_interactive']` -> exit 1
- `['python3', '-m', 'unittest', 'tests.test_stub_contract']` -> exit 1

## Last Test Outcome

failed: python3 -m unittest tests.test_stub_contract (exit 1)

## Failing Check

python3 -m unittest tests.test_stub_contract

## Recent Observations

- run python3 -m unittest tests.test_stub_contract tests.test_interactive -> exit 1
- read_file tests/stub_engine.py: sha256:16001c8ec1a5dd1f
- run python3 -m unittest tests.test_stub_contract -> exit 1

## Next Step

Investigate the failing command `python3 -m unittest tests.test_stub_contract` and change the code or the approach; do not repeat it unchanged.
