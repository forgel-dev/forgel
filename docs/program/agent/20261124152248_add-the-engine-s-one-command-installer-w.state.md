# Session State: Add the engine's one-command installer with pre-install version resolution

- Task: `20261124152248_add-the-engine-s-one-command-installer-w`
- Session: 2
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- The installer installs the engine for the invoking user only, completes without administrator or elevated rights, and changes no other user's settings and no shared machine-wide settings.
- A successful install reports the installed engine version as a single plain value on one line of its result; progress and advisory text appear elsewhere, and the reported value equals the version the installed engine reports about itself.
- After a successful install the engine is runnable by name in a newly started terminal session with no further user action and without the user editing any start-up setting.
- The installer's contribution to the user's terminal start-up settings is identifiable and limited to that contribution; every other user setting is preserved and repeated installs never duplicate it. When the engine would still not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.
- Re-running the installer for a target that is already installed completes successfully, reports the same version again, and leaves exactly one engine reachable by name.
- Re-running for a target that provides a newer version installs it, reports the newer version, and leaves no older engine competing; no re-run requires a prior removal, and no run leaves a partially replaced installation.
- Removal takes back exactly what the installer added — the installed engine and the installer's start-up contribution — leaves every other user setting unchanged, and afterwards the engine is not reachable by name in a newly started terminal session.
- Removal leaves the user's engine data intact, and removal when nothing was installed completes successfully with a message saying that nothing was installed.
- The installer offers a read-only resolution mode that reports the engine version the chosen target source and reference would install and completes successfully, whether or not an engine is installed.
- The resolution mode changes nothing: it installs nothing, changes no start-up setting, and an already installed engine keeps its version.
- The resolution mode reports the version as a single plain value on one line so a caller can read and compare it; when the version cannot be determined — an unreachable source, an unknown reference, or target information that carries no version — it ends unsuccessfully, names the cause and the next action, and reports no version at all.
- Target source, target reference and runtime interpreter are supplied to both modes as inputs without any interactive prompt; when an input is absent a documented default applies: the project's official distribution channel, its latest stable release, and a supported interpreter already present on the machine.
- The installer requires a runtime interpreter at or above the engine's minimum supported version and, when none is present, stops before changing anything and names the required minimum and what to obtain. Any failure or interruption leaves a previously working installation working at its previous version and ends unsuccessfully with a message naming the failed step and the next action the user can take.

## Acceptance Criteria

- An ordinary user runs the installer once on a machine with no engine and ends up with an engine that runs as that user; no settings of other users and no shared machine-wide settings are changed and no elevated rights are requested.
- The successful install reports exactly one plain version value, and that value equals the version the installed engine reports about itself.
- In a newly started terminal session the engine runs by name with no further action from the user.
- After the install the user's other start-up settings are unchanged, and a second install does not duplicate the installer's contribution.
- When the engine would not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.
- A second run for the same target succeeds, reports the same version again, and leaves exactly one engine reachable by name.
- A run for a newer target reports the newer version, the engine that runs is that newer version, no older engine competes, and no removal step was needed beforehand.
- After removal the engine is no longer reachable by name in a newly started terminal session, and the user's other start-up settings match their state before the install.
- User engine data present before removal is still present and unchanged afterwards.
- Removal on a machine where nothing was installed succeeds and says that nothing was installed.
- The resolution mode reports exactly one plain version value and completes successfully, both when no engine is installed and when one is.
- The resolution mode leaves the machine unchanged: the installed state, the settings and any installed engine's version are exactly as before it ran.
- The version the resolution mode reports equals the version that an install of the same target then produces.
- When the version cannot be determined, the resolution mode ends unsuccessfully, names the cause and the next action, and reports no version value at all.
- Supplied target source, target reference and runtime interpreter are honoured by both modes, and the value the resolution mode reports matches what the install then produces.
- With no supported runtime interpreter present, the install stops before changing anything, ends unsuccessfully, and names the required minimum and what to obtain.
- A failure partway through an install over an existing installation leaves that engine running and reporting its previous version.

## Constraints

- The installer never requires administrator or elevated rights and never affects another user's settings or shared machine-wide settings.
- The installer is non-interactive in both modes so another installer can drive it unattended.
- Both modes read the same target inputs, so a caller can resolve a target and then install that same target.
- The resolution mode has no side effects, so a caller can use it as a pure question.
- The installer's start-up contribution is identifiable and removable without guesswork, so removal never damages unrelated user settings.
- A failed or interrupted run cannot leave the user with a worse environment than before the run.
- All text this task produces for the project is written in English.
- No automated check reads documentation; documentation is verified by review.
- The task does not assign, promise or rewrite a published release version.
- Supported platforms are those the project already targets for terminal use; any other platform is reported as unsupported rather than partially supported.

## Assumptions

- none

## Files Changed

- docs/program/agent/20261124152248_add-the-engine-s-one-command-installer-w.state.md
- docs/program/agent/20261124152248_add-the-engine-s-one-command-installer-w.transcript.jsonl
- docs/program/tasks/20261124152248_add-the-engine-s-one-command-installer-w.json
- install.sh

## Actions

- search_files: 20261124145600 @ docs/program *
- search_files: pypi|PyPI|github.com/forgel-dev/forgel|releases/download @ . *.{md,toml,py}
- search_files: installer|install.sh|install command @ PLAN.md
- read_file: src/forgel/entry.py
- search_files: __main__ @ src/forgel *.py
- read_file: src/forgel/engine_version.py
- read_file: README.md
- search_files: ##  @ README.md
- search_files: registry @ src/forgel *.py
- read_file: README.md
- write_file: install.sh
- edit_file: install.sh
- read_file: install.sh
- edit_file: install.sh
- read_file: install.sh
- read_file: install.sh
- run: ['python3', '-m', 'unittest', 'tests.test_install', '-v']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- search_files: test_install @ . *
- read_file: tests/test_install.py

## Commands

- `['python3', '-m', 'unittest', 'tests.test_install', '-v']` -> exit 1
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']` -> exit 5

## Last Test Outcome

failed: python3 -m unittest discover -s tests -p test_install.py -v (exit 5)

## Failing Check

python3 -m unittest discover -s tests -p test_install.py -v

## Recent Observations

- run python3 -m unittest discover -s tests -p test_install.py -v -> exit 5
- search_files: tests/test_contract.py:40:                "## Affected Files\n\n- install.sh\n- tests/test_install.py\n",
- read_file tests/test_install.py: file not found: tests/test_install.py

## Next Step

Investigate the failing command `python3 -m unittest discover -s tests -p test_install.py -v` and change the code or the approach; do not repeat it unchanged.
