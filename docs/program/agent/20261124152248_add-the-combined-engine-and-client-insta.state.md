# Session State: Add the combined engine and client install mode

- Task: `20261124152248_add-the-combined-engine-and-client-insta`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- Running the client installation with no mode selection installs the client and, in the same run, brings an engine the client supports into place.
- The engine source used by the run is a configuration with a documented default; when the configuration is unset the project's own public engine source is used.
- The run determines, without installing anything, which engine version the configured engine source provides, and determines which version of an engine is already in place if one is.
- When no engine is in place, the run installs the available engine.
- When an engine is in place at a version equal to or above the available one and satisfies the declared minimum, the run keeps it untouched and reports it as kept.
- When the available version is strictly newer than the engine in place, the run replaces it with the available version.
- A successful run never leaves an engine below the client's declared minimum supported engine version.
- When the finished state cannot satisfy the declared minimum, the run exits with a non-zero status and prints one message that names the required minimum, the engine version found and the action the user can take.
- A successful run states the engine version left in place and how it was obtained: installed, kept or replaced.
- The client installation has a mode that installs the client alone; in that mode it never installs, replaces or otherwise touches an engine and succeeds whether or not an engine or the engine project's installation mechanism is available.
- When the engine project's installation mechanism cannot be found or fails, a default run exits with a non-zero status and an actionable message that names the client-only mode as the way to proceed without an engine, rather than silently installing only the client.
- Uninstalling removes the client installation and its path entry and leaves any installed engine in place.
- Re-running the default installation is idempotent: the client installation is replaced rather than duplicated, exactly one path entry remains, and an engine that is kept is not reinstalled.
- The declared minimum supported engine version has exactly one source, which both the installation and the client's startup check honour.
- Two engine versions are ordered numerically component by component; one leading version marker and trailing zero components do not affect the comparison; a version that cannot be ordered numerically is treated as not satisfying the minimum.
- The installation's own usage text describes the combined mode as the default, the client-only mode, and the engine source with its default.
- The user documentation presents exactly one one-command installation as the main path, and that path installs the client and the engine together.
- The one-command installation the documentation presents is served by the release of this project that contains the combined mode, not by an earlier release that installed the client alone; the update and uninstall instructions name the same release location.
- The documentation shows how to install only the client, states that this route touches no engine and that the user then supplies an engine meeting the declared minimum, and states that uninstalling leaves the engine in place.
- The documentation states the engine source default and how to point the run at another engine source, states that an already installed supported engine is kept and a strictly older one replaced, and states that the run reports the engine version it leaves in place.
- The documentation no longer tells the user that a working engine must already be present before the one-command installation.
- The project's existing installation-documentation standards keep their full strength: the main path is still led by the one-command installation, the update and uninstall routes are still documented, exactly one current-release location is named, no alternative main installation route is introduced, and no editable installation is proposed. Any disagreement with those standards is resolved by bringing the documentation in line with the delivered behaviour, never by dropping, loosening or rephrasing a standard into a weaker one; the only change permitted to the documented current-release location is its advance to the release that carries the combined mode.
- The changelog records the combined installation, the client-only mode, the keep/replace behaviour and the reported engine version.

## Acceptance Criteria

- On a machine with no engine, a default run against a configured engine source that provides a supported version leaves an installed client and an installed engine at that version, and reports the version and that it was installed.
- On a machine whose engine is at or above the available version and satisfies the minimum, a default run leaves the installed engine untouched and reports it as kept.
- On a machine whose engine is older than the available version, a default run replaces it and reports the new version as installed.
- When the run cannot leave an engine meeting the declared minimum, it exits non-zero and its single message names the required minimum, the version found and the action the user can take.
- A client-only run succeeds with no engine and no engine installation mechanism available, installs the client, and leaves an engine that is present unchanged.
- A default run with no engine installation mechanism available exits non-zero with a message that names the client-only route as the way to proceed.
- Running the default installation twice leaves the kept engine unchanged and exactly one path entry in the profile.
- Engine versions that differ only by a leading marker or trailing zero components compare equal, a strictly newer available version wins, and a non-numeric version never satisfies the minimum.
- Uninstalling removes the client installation and its path entry and leaves the installed engine in place.
- The installation's usage text describes the combined default, the client-only mode and the engine source default.
- The documentation's single main one-command installation installs the client and the engine together.
- The documentation shows how to install only the client and says that route touches no engine.
- The documentation names the default engine source and its override, the keep-supported and replace-strictly-older behaviour, the reported engine version and the fact that uninstalling keeps the engine; it no longer requires a pre-installed engine for the one-command installation.
- The documented installation, update and uninstall instructions all name the release that carries the combined mode, and no earlier release that installed the client alone is named.
- No existing installation-documentation standard has been dropped, loosened or rephrased into a weaker one; the only change to the documented current-release location is its advance to the release carrying the combined mode.
- The changelog records the combined installation, the client-only mode, the comparison behaviour and the reported engine version.
- The whole test suite passes, including the existing installation and packaging expectations.

## Constraints

- none

## Assumptions

- none

## Files Changed

- forgel_code/__init__.py
- install.sh
- tests/stub_engine_install.py
- tests/test_cli.py
- tests/test_install.py
- tests/test_readme_install.py

## Actions

- recall
- recall
- read_file: tests/test_readme_install.py
- read_file: tests/test_cli.py
- read_file: install.sh
- run: ['git', 'status', '--porcelain']
- run: ['python3', '-m', 'pytest', '-q']
- read_file: README.md
- read_file: CHANGELOG.md
- read_file: README.md
- read_file: install.sh
- read_file: README.md

## Commands

- `['git', 'status', '--porcelain']` -> exit 0
- `['python3', '-m', 'pytest', '-q']` -> exit 0

## Recent Observations

- read_file README.md: README.md: lines 200-267 of 267
- read_file install.sh: install.sh: lines 700-1251 of 1251
- read_file README.md: README.md: lines 130-201 of 267

## Next Step

Continue from the current repository state and the changed files.
