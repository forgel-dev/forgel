# Agent Run: Release audit: The session does not refresh task and release state on its own while the owner i

- Task: `20261123213155_release-audit-the-session-does-not-refre`
- Status: `done`
- Repository: `code`
- Steps: 105
- Finished: 2026-11-24T00:24:32+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- A refresh interval of 0.5 s was chosen as the developer's cadence; it is not a product commitment.
- A state that has not changed prints nothing, because show_state compares the rendered lines with what was last shown.
- An engine failure during an idle refresh is stated once per distinct message and the session keeps running, matching how other engine failures are reported.
- Repeated reads still cost one engine invocation per state command per interval, which the task treats as the developer's choice of cadence.
- The unrelated README and CHANGELOG edits left by an earlier attempt of this task (they documented the multilingual reply behavior, not the idle refresh) were reverted, because this task requires no documentation change and forbids unrelated edits.
- The pre-existing stdlib allowlist test had to learn the stdlib module the session now imports; its scenario (client sources import only the standard library and never the engine) is unchanged.

## Test Removals

- tests/test_cli.py::NoEngineImportTest::test_client_sources_import_only_stdlib: replaced -> tests/test_cli.py::NoEngineImportTest::test_client_sources_import_only_stdlib

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 105
- Estimated input tokens (all calls): 4862035
- Provider input/output tokens: 5000884 / 260575
- Provider cache hit/miss tokens: 4853248 / 147636
- Estimated prompt at the end: 67496 tokens
- State: `docs/program/agent/20261123213155_release-audit-the-session-does-not-refre.state.md`

## Specification (`docs/program/specs/20261123213155_release-audit-the-session-does-not-refre.md`)

# Task Spec: Release audit: The session does not refresh task and release state on its own while the owner i

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: The session does not refresh task and release state on its own while the owner i |
| Project | — |
| Task | `20261123213155_release-audit-the-session-does-not-refre` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T23:48:21+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

When the owner leaves the session idle, the client refreshes the project's task and release state only at start-up and then again only after the owner submits something, so it blocks waiting for input and shows nothing new. A task or release that changes while the owner waits is invisible until the owner types a sentence, which contradicts the promised behavior that progress appears without the owner asking for a status. The audit evidence is also weak: the existing check only reached a second refresh by feeding empty sentences, so it never demonstrated refresh during idle waiting.

**Outcome:** While the owner sits idle and submits nothing, the client keeps the visible task and release state up to date by re-reading it from the engine on its own, so a change made on the engine side appears in the session without the owner typing anything; refresh happens repeatedly for as long as the owner waits, adds no output when nothing changed, does not disturb text the owner is typing, and the session still ends cleanly when input ends. The idle behavior is demonstrated without the owner feeding empty sentences.

## Product Intent

Forgel Code is a thin console client over the engine's machine-readable commands (D-002, D-007): it shows what the engine reports and never calls a model, reads a project or runs a check itself. The owner should see progress as it happens rather than having to ask for a status, which is only true if the session keeps the state current while the owner is not typing.

## User Experience

The owner starts the session, sees the current tasks and release, and can step away from the keyboard. If a task moves or the release state changes on the engine side, the session shows the new state on its own while the owner is still sitting there; when nothing changes the screen stays quiet, and whatever the owner types next is delivered exactly as typed. Leaving ends the session as quietly as before.

## Roadmap

—

## Goals

- The session keeps the project's task and release state current on its own while the owner is idle and submits nothing.
- A change made on the engine side while the owner waits becomes visible without any input from the owner, including empty sentences.
- Idle refreshing stays quiet when nothing changes and never interferes with what the owner types.
- The session still ends cleanly at end of input and all earlier behavior and tests remain intact.

## Non-Goals

- Changing which engine commands exist, what they answer, or how the client maps a sentence to one of them.
- Adding new kinds of state, new panels or new status commands to the session.
- Refreshing anything other than the project's task list and the current release state.
- Changing the session's wording, prompt text, languages or failure/clarification messages.
- Calling the model, reading project files or running checks from the client (stays in the engine, D-002).
- Setting, promising or rewriting release versions or tags.
- Documentation or changelog edits beyond what this fix needs; no documentation file is required by this task.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, User, 2026-11-16 18:31 |
| — | The client's working name is Forgel Code, installed as a Python client that follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, User accepted the proposal, 2026-11-16 18:34 |
| — | The single free-text engine entry point is `forgel say`; every client-facing operation is a parameterized command with an optional single JSON object on stdout, and the active project is an engine-side session with the default key `local`. | D-007, User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: While the owner is idle and has submitted nothing, the client re-reads the project's task list and the current release state from the engine on its own.
- **FR-2**: A task or release change that happens while the owner waits becomes visible in the session without the owner submitting any sentence, including an empty one.
- **FR-3**: The refresh repeats for as long as the owner keeps waiting, so a second change after the first is also shown without input.
- **FR-4**: A refresh that finds the state unchanged adds no state text to the session; the visible output is unaffected.
- **FR-5**: The refreshed state is shown in the same form the session already uses for that state, so the owner cannot tell an idle update from a prompted one except that no prompt was answered.
- **FR-6**: A refresh while the owner is part-way through a sentence does not remove, repeat, reorder or alter the characters already typed, and the sentence the owner submits reaches the engine as typed.
- **FR-7**: When the owner's input ends, the session ends cleanly as it does today, with the session's closing notice and the same success outcome, and it neither hangs nor needs an extra sentence to stop.
- **FR-8**: If the engine cannot be reached or answers with a failure during an idle refresh, the session keeps running and the owner can still submit the next sentence; the failure is reported in the same cause-and-next-step form the session already uses for failures.
- **FR-9**: Idle waiting stays quiet and cheap: with no changes on the engine side, the owner's visible output and the machine's work stay essentially unchanged for the whole wait.
- **FR-10**: The behavior is the same whether the owner's input is an interactive terminal or a supplied stream of sentences.
- **FR-11**: The idle refresh is demonstrated by a session whose input provides no further sentences for the duration of the observation, so the evidence does not depend on empty sentences triggering another round.

## User Stories

- As the owner, I want the session to show a task or release change that happens while I am not typing, so that I see progress without asking for a status.
- As the owner, I want repeated changes to keep appearing while I sit idle, so that a long wait does not leave me looking at stale state.
- As the owner, I want the waiting screen to stay quiet when nothing changes, so that the session does not scroll away what I am reading.
- As the owner, I want what I type to arrive exactly as typed even though the session updates itself meanwhile, so that my sentence is never mangled.
- As the owner, I want the session to end normally when my input ends, so that the self-updating behavior never traps me in the session.

## Acceptance Criteria

- **AC-1**: With the engine reporting one state, an observation is made of a session that supplies no further sentences; while it waits, the engine's reported task and release state change, and the new state appears in the session's output without any sentence being submitted.
- **AC-2**: In the same idle-waiting observation the engine's reported state changes a second time and the second change also appears, showing the refresh repeats.
- **AC-3**: With the engine reporting an unchanged state, the idle waiting period produces no repeated state text beyond what was already shown.
- **AC-4**: A sentence submitted after an idle refresh has occurred still reaches the engine exactly as typed, and the session outcome is the same success outcome it has today.
- **AC-5**: A session whose input ends immediately still shows its prompt, prints the closing notice and ends with the same success outcome as today.
- **AC-6**: An engine failure reported during an idle refresh does not end the session, is shown in the session's existing cause-and-next-step failure form, and the next submitted sentence still works.
- **AC-7**: The proof of the idle refresh does not rely on empty sentences: the supplying side stays silent for the observation window.
- **AC-8**: All tests that existed before the change still pass.

## Scope Boundaries

- The client re-reads the project's task list and the current release state from the engine while the owner is idle and has submitted nothing.
- A change found by such a refresh becomes visible in the session without any input from the owner.
- Repeated refreshes continue for as long as the owner waits, so more than one change is shown.
- A refresh that finds no change adds nothing visible to the session.
- Idle refresh does not drop, duplicate, reorder or alter text the owner is typing or has submitted.
- Idle refresh covers the same two pieces of state the session already shows and nothing else.
- The session still ends cleanly when the owner's input ends, and the existing request, failure and clarification behavior stays as it is.
- Evidence for the idle refresh comes from a session whose input supplies no further sentences, including no empty ones.
- Changing which engine commands exist, what they answer, or how the client maps a sentence to one of them.
- Adding new kinds of state, new panels or new status commands to the session.
- Refreshing anything other than the project's task list and the current release state.
- Changing the session's wording, prompt text, languages or failure/clarification messages.
- Calling the model, reading project files or running checks from the client (stays in the engine, D-002).
- Setting, promising or rewriting release versions or tags.
- Documentation or changelog edits beyond what this fix needs; no documentation file is required by this task.

## Risks

- Waiting for owner input while also refreshing requires input handling that can be interrupted or accompanied by other work; a naive change can swallow typed text, end the session on end-of-input incorrectly, or keep the session open forever.
- A refresh that prints the state every cycle would flood the owner's screen and violate the quiet-waiting requirement.
- A short refresh cadence with no change detection can spin the machine; a long cadence makes the fix too slow to observe sitting at the keyboard.
- Timing-based observations can be flaky: an observation window that is too short fails intermittently and one that is too long makes the checks slow.
- The existing check reaches a second refresh through empty sentences; leaving it as it is would let the defect return unnoticed, while replacing it carelessly could break the session's end-of-input behavior.
- The engine binary itself is exercised through a stand-in in the current checks; the contract read by the client is unchanged by this task, but a behavior difference in the real engine would not be caught here.
- A failing engine during an unattended wait could end an otherwise healthy session if the new refresh path does not reuse the existing failure handling.

## Open Questions

- None.

## Assumptions

- The refresh cadence is chosen by the developer as long as a change made while the owner waits appears promptly enough to be seen during the wait rather than only after the next submitted sentence; no exact interval is a product commitment.
- Unchanged state prints nothing, because the session already shows the state before each prompt and repeating it during a wait would flood the output.
- A refresh does not run while a request is being executed; the state is read between the owner's requests and while the owner is idle.
- State already shown is remembered, and a refresh is displayed only when the reported task or release content differs from what was last displayed.
- A failing engine answer during a refresh is treated like any other engine failure the session already reports, not as a reason to end the session.
- The pieces of engine output the session reads for tasks and releases stay the ones it reads today; this task changes when they are read, not what is read.

## Related Documents

- README.md
- CHANGELOG.md
- releases/0.1.1/plan.md

## Revision History

- 1 — initial specification resolving the release audit finding that the session does not refresh task and release state while the owner is idle.


## Summary

Implemented idle state refresh for the interactive session, so the task list and current release are re-read from the engine while the owner submits nothing, and added evidence that does not depend on empty sentences. forgel_code/interactive.py: the state read was split into read_state() (raises an EngineError) and state_lines(quiet) (keeps the previous failure behaviour), show_state() prints only when the rendered state differs from the last shown one, refresh(force, quiet) reuses show_state, and a new idle_refresh() re-reads the state, shows a change and reports an engine failure once per distinct message in the session's existing cause-and-next-step form without ending the session. wait_for_line() reads one input line on a background thread and joins it for IDLE_REFRESH_SECONDS; while the line has not arrived it runs idle_refresh(), so the loop repeats for as long as the owner waits, leaves typed characters untouched (the line is returned exactly as read), and end of input still yields an empty line that ends the session with the existing closing notice and exit code 0. The session loop now takes its line from wait_for_line(). tests/test_idle_refresh.py proves this with a stand-in engine whose reported state comes from a file the test rewrites while a threaded session waits on a pipe: the pipe stays silent for the whole observation, two successive engine-side changes appear in the output, an unchanged state is printed exactly once although the engine keeps being read, a sentence half-typed across a refresh reaches the engine as `status` and the session ends with code 0, an engine failure during the idle wait is shown as `failed:`/`next step:` and the next sentence still works, and an input that ends at once still shows the prompt, the closing notice and code 0. All pre-existing tests still pass (289 passed, 232 subtests).

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_cli.py`
- `tests/test_idle_refresh.py`

## Commands

- `["python", "-m", "pytest", "-q", "tests"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_idle_refresh.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests"]` → exit 1
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-c", "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','tests/test_cli.py']).returncode)"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "diff", "CHANGELOG.md", "README.md"]` → exit 0
- `["python", "-c", "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','tests/test_cli.py']).returncode)"]` → exit 0
- `["python", "-c", "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','CHANGELOG.md','README.md']).returncode)"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "-U3", "--", "forgel_code/interactive.py"]` → exit 0
- `["git", "diff", "--stat", "--", "tests/test_cli.py"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests"]` → exit 0

## Final Test Output

```
.............................................................................................. [ 32%]
........................................................................ [ 57%]
.......................................................................................... [ 88%]
.................................                                                        [100%]
289 passed, 232 subtests passed in 182.60s (0:03:02)

```

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
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- read_file: tests/stub_engine.py
- read_file: tests/test_interactive.py
- recall
- read_file: tests/test_extras.py
- write_file: tests/test_idle_refresh.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_idle_refresh.py']
- run: ['python', '-m', 'pytest', '-q', 'tests']
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- write_file: tests/test_cli.py
- run: ['git', 'checkout', '--', 'tests/test_cli.py']
- run: ['git', 'restore', '--source=HEAD', '--worktree', 'tests/test_cli.py']
- run: ['git', 'status', '--porcelain']
- run: ['sh', '-c', 'git show HEAD:tests/test_cli.py > tests/test_cli.py && wc -l tests/test_cli.py']
- run: ['python', '-c', "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','tests/test_cli.py']).returncode)"]
- run: ['git', 'status', '--porcelain']
- read_file: tests/test_cli.py
- run: ['git', 'diff', '--stat']
- run: ['git', 'diff', 'CHANGELOG.md', 'README.md']
- write_file: tests/test_cli.py
- read_file: tests/test_cli.py
- run: ['python', '-c', "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','tests/test_cli.py']).returncode)"]
- run: ['python', '-c', "import subprocess,sys; sys.exit(subprocess.run(['git','checkout','--','CHANGELOG.md','README.md']).returncode)"]
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', '-U3', '--', 'forgel_code/interactive.py']
- read_file: tests/test_cli.py
- run: ['python', '-c', 'import pathlib; p=pathlib.Path(\'tests/test_cli.py\'); s=p.read_text(encoding=\'utf-8\'); old=\'        "sys",\\n        "typing",\\n\'; new=\'        "sys",\\n        "threading",\\n        "typing",\\n\'; assert s.count(old)==1, s.count(old); p.write_text(s.replace(old,new), encoding=\'utf-8\')']
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- read_file: tests/test_cli.py
- write_file: tests/test_cli.py
- run: ['git', 'diff', '--stat', '--', 'tests/test_cli.py']
- read_file: CHANGELOG.md
- read_file: CHANGELOG.md
- read_file: CHANGELOG.md
- read_file: README.md
- run: ['python', '-m', 'pytest', '-q', 'tests']
- run: ['git', 'status', '--porcelain']
