# Session State: Release audit: The session does not refresh task and release state on its own while the owner i

- Task: `20261123213155_release-audit-the-session-does-not-refre`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- While the owner is idle and has submitted nothing, the client re-reads the project's task list and the current release state from the engine on its own.
- A task or release change that happens while the owner waits becomes visible in the session without the owner submitting any sentence, including an empty one.
- The refresh repeats for as long as the owner keeps waiting, so a second change after the first is also shown without input.
- A refresh that finds the state unchanged adds no state text to the session; the visible output is unaffected.
- The refreshed state is shown in the same form the session already uses for that state, so the owner cannot tell an idle update from a prompted one except that no prompt was answered.
- A refresh while the owner is part-way through a sentence does not remove, repeat, reorder or alter the characters already typed, and the sentence the owner submits reaches the engine as typed.
- When the owner's input ends, the session ends cleanly as it does today, with the session's closing notice and the same success outcome, and it neither hangs nor needs an extra sentence to stop.
- If the engine cannot be reached or answers with a failure during an idle refresh, the session keeps running and the owner can still submit the next sentence; the failure is reported in the same cause-and-next-step form the session already uses for failures.
- Idle waiting stays quiet and cheap: with no changes on the engine side, the owner's visible output and the machine's work stay essentially unchanged for the whole wait.
- The behavior is the same whether the owner's input is an interactive terminal or a supplied stream of sentences.
- The idle refresh is demonstrated by a session whose input provides no further sentences for the duration of the observation, so the evidence does not depend on empty sentences triggering another round.

## Acceptance Criteria

- With the engine reporting one state, an observation is made of a session that supplies no further sentences; while it waits, the engine's reported task and release state change, and the new state appears in the session's output without any sentence being submitted.
- In the same idle-waiting observation the engine's reported state changes a second time and the second change also appears, showing the refresh repeats.
- With the engine reporting an unchanged state, the idle waiting period produces no repeated state text beyond what was already shown.
- A sentence submitted after an idle refresh has occurred still reaches the engine exactly as typed, and the session outcome is the same success outcome it has today.
- A session whose input ends immediately still shows its prompt, prints the closing notice and ends with the same success outcome as today.
- An engine failure reported during an idle refresh does not end the session, is shown in the session's existing cause-and-next-step failure form, and the next submitted sentence still works.
- The proof of the idle refresh does not rely on empty sentences: the supplying side stays silent for the observation window.
- All tests that existed before the change still pass.

## Constraints

- none

## Assumptions

- none

## Files Changed

- CHANGELOG.md
- README.md
- forgel_code/interactive.py

## Actions

- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/cli.py
- recall
- run: ['python', '-m', 'pytest', '-q', 'tests']
- read_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py

## Commands

- `['python', '-m', 'pytest', '-q', 'tests']` -> exit 0

## Recent Observations

- run python -m pytest -q tests -> exit 0
- read_file forgel_code/interactive.py: forgel_code/interactive.py: lines 1745-1835 of 1835
- write_file forgel_code/interactive.py

## Next Step

Continue from the current repository state and the changed files.
