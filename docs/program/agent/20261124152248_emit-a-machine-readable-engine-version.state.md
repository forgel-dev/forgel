# Session State: Emit a machine-readable engine version

- Task: `20261124152248_emit-a-machine-readable-engine-version`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- FR-1: On request, the engine states its own version in a form another program reads directly, without interpreting human-readable text.
- FR-2: The stated version is the version the release declares; the engine does not keep a second, independently editable statement of that version that can disagree with it.
- FR-3: The version is expressed so that two versions can be compared component by component.
- FR-4: The version can be obtained on a machine with no project, no stored configuration, no model credential, no pre-existing user data and no network, from any working directory, and obtaining it leaves no state behind.
- FR-5: Obtaining the version neither starts model work nor reads or changes project, task or account records.
- FR-6: When the version cannot be stated, the failure is signalled to the caller as a failure and carries its reason in the same place as the engine's other program-facing reports.
- FR-7: The engine's other program-facing reports and its human-readable outputs keep their current behaviour.
- FR-8: No other check or test is removed, weakened or relaxed; the behaviour of the installer and of the client stays as it is.

## Acceptance Criteria

- AC-1: A program obtains the engine's own version directly, without interpreting human-readable text, and the value equals the version the release declares.
- AC-2: The version is obtainable on a machine with no project, no stored configuration, no model access and no network, from any working directory, and obtaining it leaves nothing behind.
- AC-3: All remaining checks pass unchanged.

## Constraints

- The version the release declares is the single authority; the new report must not introduce a second editable statement of it.
- The change adds a program-facing report and must not alter any existing program-facing report or human-readable output.
- The change must be usable before the surrounding system is configured, because that is where a caller needs it.
- No existing check or test may be removed, weakened or relaxed by this change.

## Assumptions

- none

## Files Changed

- docs/program/agent/20261124152248_emit-a-machine-readable-engine-version.transcript.jsonl
- docs/program/tasks/20261124152248_emit-a-machine-readable-engine-version.json
- src/forgel/__init__.py
- src/forgel/client.py
- src/forgel/engine_version.py
- src/forgel/entry.py

## Actions

- search_files: def main @ src/forgel/cli.py
- read_file: src/forgel/cli.py
- edit_file: src/forgel/client.py
- write_file: src/forgel/engine_version.py
- write_file: src/forgel/engine_version.py
- edit_file: src/forgel/entry.py
- read_file: src/forgel/entry.py
- edit_file: src/forgel/entry.py
- edit_file: src/forgel/entry.py
- read_file: src/forgel/entry.py
- edit_file: src/forgel/entry.py
- search_files: __version__|forgel --version|import __version__ @ .
- read_file: src/forgel/orchestrator.py
- read_file: tests/test_client.py
- read_file: src/forgel/engine_version.py
- write_file: src/forgel/engine_version.py
- write_file: src/forgel/__init__.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- read_file: tests/test_e2e.py
- run: ['python3', 'tests/e2e/run_client_e2e.py']

## Commands

- `['python3', '-c', "import importlib.metadata as m; print(m.version('forgel'))"]` -> exit 0
- `['python3', '-c', "import forgel, importlib.metadata as m; print(forgel.__file__); print(m.distribution('forgel')._path)"]` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 1
- `['python3', 'tests/e2e/run_client_e2e.py']` -> exit 1

## Last Test Outcome

failed: python3 tests/e2e/run_client_e2e.py (exit 1)

## Failing Check

python3 tests/e2e/run_client_e2e.py

## Recent Observations

- run python3 -m unittest discover -s tests -> exit 1
- read_file tests/test_e2e.py: sha256:0a2ae94a02688014
- run python3 tests/e2e/run_client_e2e.py -> exit 1

## Next Step

Investigate the failing command `python3 tests/e2e/run_client_e2e.py` and change the code or the approach; do not repeat it unchanged.
