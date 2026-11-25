# Session State: Add the combined engine and client install mode

- Task: `20261124152248_add-the-combined-engine-and-client-insta`
- Session: 5
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- The default client installation also ensures a supported engine is in place in the same run.
- The installation learns which engine version the configured engine source offers without changing anything on the machine.
- When no engine is present, the installation obtains the offered engine version.
- When an engine is present and the offered version is not strictly newer, the installation keeps the present engine and changes nothing about the engine installation.
- When the offered version is strictly newer than the present engine, the installation replaces the present engine with that newer one.
- The installation never installs an engine older than, or equal to, the one already present.
- The finished state always satisfies the client's declared minimum supported engine version; when it cannot, the installation ends as a failure instead of reporting the pair as installed.
- A failed engine outcome reports the required minimum version, the version that was found or offered, and a concrete action the user can take, and is clearly distinguishable from a successful run.
- A successful installation states the engine version in place and how it was obtained: installed, kept or replaced.
- Engine versions are ordered numerically component by component, tolerating one leading version prefix and trailing zero components; a version that cannot be ordered never counts as satisfying the minimum.
- The documented client-only installation installs the client and neither queries nor changes any engine.
- Removing the client installs nothing and leaves any engine in place.
- The documented option that keeps the user's startup configuration unchanged does not disable the engine part of the installation.
- The engine source the installation resolves against is documented configuration with a stated default and a documented way to point it elsewhere.
- Repeating the default installation changes nothing about an engine that needs no change, and leaves exactly one client installation and one startup entry.
- The user documentation presents the default installation as the way to obtain a working client-and-engine pair, documents the client-only installation and the engine source configuration, and no longer instructs the user to supply an engine separately.
- The project's automated checks contain no check that reads documentation text, and no automated check of documentation text is added in its place.
- The correctness of the installation instructions is accepted or returned solely by review of their text.
- Every other automated check stays in place and unchanged, and the installer and client behavior outside the combined installation is unchanged.

## Acceptance Criteria

- Starting the default installation on a machine with no engine ends successfully, leaves a usable client, leaves an engine at or above the declared minimum, and reports that version and that it was installed.
- Starting the default installation with an engine already present at exactly the offered version ends successfully, leaves the engine installation unchanged, and reports the engine as kept with its version.
- Starting the default installation with an engine present below the offered version ends successfully, leaves the strictly newer offered engine in place, and reports it as replaced.
- Starting the default installation with an engine present above the offered version and at or above the declared minimum ends successfully, leaves the engine installation unchanged, and reports the engine as kept.
- When the offered version is below the declared minimum and no suitable engine is present, the installation ends as a failure whose message names the required minimum, the version found or offered, and the action the user can take.
- When obtaining the engine fails, the installation ends as a failure with a message naming what went wrong and the next action, and never reports the pair as installed.
- Choosing the documented client-only installation installs the client, performs no engine version query, and leaves an engine present beforehand unchanged.
- Running the default installation twice in a row leaves exactly one client installation and one startup entry, and the second run does not change the engine the first run left.
- Versions differing only by a leading version prefix or by trailing zero components are treated as the same version, and a version that cannot be ordered never satisfies the minimum.
- Removing a client installed with an engine leaves the engine in place and leaves no client artifacts behind.
- The documentation presents the default installation as producing a working client alongside a supported engine, states that the engine version in place and how it was obtained are reported, and describes what a successful installation reports.
- The documentation states that an absent engine is obtained, that a present engine is kept when the offered version is not strictly newer, that a strictly newer offered engine replaces it, and that the finished state always satisfies the declared minimum or the installation fails with an actionable message naming the minimum and the version found or offered.
- The documentation documents the client-only installation, the engine source with its default and how to point it elsewhere, and the option that keeps the user's startup configuration unchanged; it no longer instructs the user to supply an engine separately for the default installation.
- The automated checks contain no check that reads documentation text, and no automated check of documentation text replaces the removed one.
- All other automated checks run unchanged and pass, and installer and client behavior outside the combined installation is unchanged.
- The installation instructions are accepted or returned solely by review of their text; a passing or failing verdict on their wording comes from a person reading them, never from an automated check.

## Constraints

- No automated check reads documentation text; the installation instructions are verified by review of their text only, and no automated documentation check is added in place of the removed one.
- The removed documentation check is deleted in full, including the supporting data that reproduces the documentation text.
- No other automated check is removed, weakened or skipped, and installer and client behavior outside the combined installation is unchanged.
- The combined installation is idempotent, never installs an engine older than or equal to the one present, and always ends at or above the declared minimum or as a failure.
- All project artifacts are written in English, regardless of chat language.

## Assumptions

- none

## Files Changed

- README.md
- forgel_code/__init__.py
- install.sh
- tests/.restore.sed
- tests/_restore_cli_comments.py
- tests/stub_engine_install.py
- tests/test_cli.py
- tests/test_install.py
- tests/test_install_engine.py
- tests/test_readme_install.py

## Actions

- read_file: tests/test_cli.py
- run: ['git', 'status', '--porcelain']
- read_file: tests/test_cli.py
- read_file: install.sh
- read_file: tests/test_cli.py
- write_file: tests/.restore.sed
- run: ['sed', '-i.bak', '-f', 'tests/.restore.sed', 'tests/test_cli.py']
- delete_file: tests/.restore.sed
- write_file: tests/_restore_cli_comments.py
- run: ['python3', 'tests/_restore_cli_comments.py']
- delete_file: tests/_restore_cli_comments.py
- run: ['git', 'diff', '--stat', '--', 'tests/test_cli.py']
- read_file: README.md
- run: ['sh', '-n', 'install.sh']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- run: ['rg', '-l', 'README', 'tests']
- run: ['python3', '-m', 'pytest', '-q', 'tests/test_cli.py', 'tests/test_install_engine.py']
- read_file: forgel_code/engine.py
- read_file: forgel_code/engine.py
- read_file: forgel_code/cli.py

## Commands

- `['git', 'status', '--porcelain']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 0
- `['git', 'status', '--porcelain']` -> exit 0
- `['git', 'diff', '--', 'tests/test_cli.py']` -> exit 0
- `['python3', '-m', 'pytest', '--collect-only', '-q', '-k', 'readme or docs or documentation']` -> exit 5
- `['git', 'status', '--porcelain']` -> exit 0
- `['python3', 'tests/_restore_cli_comments.py']` -> exit 0
- `['git', 'diff', '--stat', '--', 'tests/test_cli.py']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests']` -> exit 0
- `['python3', '-m', 'pytest', '-q', 'tests/test_cli.py', 'tests/test_install_engine.py']` -> exit 0

## Recent Observations

- read_file forgel_code/engine.py: forgel_code/engine.py: lines 1-120 of 205
- read_file forgel_code/engine.py: forgel_code/engine.py: lines 121-205 of 205
- read_file forgel_code/cli.py: forgel_code/cli.py: lines 1-60 of 439

## Next Step

Continue from the current repository state and the changed files.
