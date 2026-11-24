# Session State: Emit a machine-readable engine version

- Task: `20261124152248_emit-a-machine-readable-engine-version`
- Session: 5
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- On request, the engine states its own version in a form another program reads directly, without interpreting human-readable text.
- The stated version is the version the release declares; the engine does not keep a second, independently editable statement of that version that can disagree with it.
- The version is expressed so that two versions can be compared component by component.
- The version can be obtained on a machine with no project, no stored configuration, no model credential, no pre-existing user data and no network, from any working directory, and obtaining it leaves no state behind.
- Obtaining the version neither starts model work nor reads or changes project, task or account records.
- When the version cannot be stated, the failure is signalled to the caller as a failure and carries its reason in the same place as the engine's other program-facing reports.
- The engine's other program-facing reports and its human-readable outputs keep their current behaviour.
- The automated check that reads the install instructions in the user documentation is removed, together with any helper data that reproduces the documentation text for that check.
- No other automated check of the documentation text is added in its place: whether the documented install instructions are correct is decided by reading the text, not by an automated check.
- No other check or test is removed, weakened or relaxed; the behaviour of the installer and of the client stays as it is.

## Acceptance Criteria

- A program obtains the engine's own version directly, without interpreting human-readable text, and the value equals the version the release declares.
- The version is obtainable on a machine with no project, no stored configuration, no model access and no network, from any working directory, and obtaining it leaves nothing behind.
- The verification run contains no check that reads the documentation text about installation.
- All remaining checks pass unchanged.
- The documented install instructions are accepted or returned for correction on the basis of reading their text.

## Constraints

- The engine states the released version; it never invents, rounds or renumbers a version of its own.
- The version is obtainable at no cost and with no access: no project, no stored configuration, no credential, no network.
- The engine's existing conventions for program-facing reports are reused, not redefined by this task.
- Documentation is text and is judged by reading it; no automated check may read a documentation file.
- Existing behaviour of the installer and of the client stays as it is.
- Existing program-facing reports and human-readable outputs keep their current behaviour and wording.
- The change touches nothing the task does not need.

## Assumptions

- none

## Files Changed

- docs/program/agent/20261124152248_emit-a-machine-readable-engine-version.state.md
- docs/program/agent/20261124152248_emit-a-machine-readable-engine-version.transcript.jsonl
- docs/program/tasks/20261124152248_emit-a-machine-readable-engine-version.json

## Actions

- read_file: src/forgel/presets.py
- read_file: tests/e2e/run_client_e2e.py
- recall
- recall
- recall
- list_files
- run: ['find', 'tests', '-name', '*.py']
- recall
- recall
- read_file: tests/test_install_sh.py
- recall
- run: ['git', 'ls-files', 'tests']
- recall
- read_file: tests/test_install.py
- list_files
- recall
- run: ['python3', '-m', 'pytest', 'tests', '--collect-only', '-q', '-k', 'readme or install or docs']
- run: ['git', 'status', '--porcelain']
- read_file: src/forgel/cli.py
- read_file: README.md

## Commands

- `['python3', '-m', 'pytest', 'tests', '--collect-only', '-q']` -> exit 0
- `['python3', '-m', 'pytest', 'tests', '--collect-only', '-q', '-k', 'readme or docs or install or document']` -> exit 0
- `['python3', '-m', 'pytest', '--collect-only', '-q']` -> exit 2
- `['git', 'status', '--porcelain']` -> exit 0
- `['python3', '-m', 'pytest', 'tests', '--collect-only', '-q']` -> exit 0
- `['python3', '-m', 'pytest', 'tests', '--collect-only', '-q', '-k', 'readme or install or docs']` -> exit 0
- `['python3', '-m', 'pytest', 'sandbox_tests', '--collect-only', '-q']` -> exit 0
- `['git', 'log', '--oneline', '-8']` -> exit 0
- `['python3', '-m', 'pytest', 'tests', '--collect-only', '-q', '-k', 'readme or install or docs']` -> exit 0
- `['git', 'status', '--porcelain']` -> exit 0

## Recent Observations

- run git status --porcelain -> exit 0
- read_file src/forgel/cli.py: src/forgel/cli.py: lines 2050-2350 of 2350
- read_file README.md: README.md: lines 1-782 of 782

## Next Step

Continue from the current repository state and the changed files.
