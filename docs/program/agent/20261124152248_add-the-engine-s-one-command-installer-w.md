# Agent Run: Add the engine's one-command installer with pre-install version resolution

- Task: `20261124152248_add-the-engine-s-one-command-installer-w`
- Status: `done`
- Repository: `main`
- Steps: 169
- Finished: 2026-11-28T00:26:46+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- The install location is `~/.local/share/forgel` and the command directory `~/.local/bin`, both overridable by environment inputs, never shared.
- The default target source is the official PyPI channel addressed by its JSON API, the default reference its latest stable release, and the default interpreter a supported interpreter already on PATH.
- A target source may also be a local engine source tree (declared version read from `pyproject.toml`), which is what the end-to-end tests drive, since the published channel cannot be exercised offline.
- Removal is a mode of the same script (`--uninstall`), its outcome line goes to stdout because it carries no version.
- The start-up contribution is a single marked block in one start-up file chosen from the invoking user's shell (`.zshrc`, `.bash_profile`/`.bashrc`, otherwise `.profile`), removed by marker so unrelated settings are never touched.
- Engine data lives under `~/.forgel` and is never touched by install or removal.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 3
- Handoffs: 2
- Model calls: 169
- Estimated input tokens (all calls): 8122745
- Provider input/output tokens: 8256583 / 461925
- Provider cache hit/miss tokens: 7964544 / 292039
- Estimated prompt at the end: 77419 tokens
- State: `docs/program/agent/20261124152248_add-the-engine-s-one-command-installer-w.state.md`

## Specification (`docs/program/specs/20261124152248_add-the-engine-s-one-command-installer-w.md`)

# Task Spec: Add the engine's one-command installer with pre-install version resolution

## Document Information

| Field | Value |
|-------|-------|
| Feature | Add the engine's one-command installer with pre-install version resolution |
| Project | — |
| Task | `20261124152248_add-the-engine-s-one-command-installer-w` |
| Plan | `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Repository | `main` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-27T23:37:41+00:00 |
| Source | Plan `20261124145600_make-forgel-and-forgel-code-install-and-` |
| Author | Forgel requirements writer |

## Overview

The engine has no installer of its own. A user must assemble a runtime environment, make the engine reachable by hand, and there is no way for another program to learn which engine version a chosen target provides without actually installing it. Because of that, the companion client cannot be offered as a combined install and cannot decide whether an installed engine is usable. This task gives the engine a first-class per-user installer, a clean removal, and a non-destructive version answer that another installer can use before it decides anything.

**Outcome:** A user installs the engine with one action as themselves, gets a working engine in a newly started terminal session, can repeat that action safely and is told the installed version as one plain value; removal takes back exactly what the installer added and keeps user data; and a separate read-only mode answers which version a chosen target would provide, so the companion client's installer can compare it with an installed engine and install only a strictly newer one.

## Product Intent

Forgel and Forgel Code must install and run as one working pair. Both must be installable by a non-expert on their own machine without administrator rights and without hand-editing start-up settings, and the pair must be installable together by one action. That is only possible when the engine's installer can answer 'which engine version would I get' without installing anything, and can install a chosen target reproducibly.

## User Experience

The user copies one line into a terminal and ends up with a working engine, with no administrator prompt, no manual environment assembly and no hand-edited start-up configuration. Repeating the same line is safe and gives a newer engine when one exists. The last line of a successful install tells the user exactly which engine version is now installed. If something cannot be done — no supported runtime, unreachable source, or an older engine that would still win — the user gets a plain message naming the cause and the next action instead of a broken environment. A second, read-only mode answers 'which version would I get' without touching the machine, which is what makes the combined install trustworthy.

## Roadmap

—

## Goals

- Give the engine a single-action, unprivileged, per-user install that leaves a working engine in a newly started terminal session.
- Make repeating the installer safe, so the same action both repairs and upgrades an installation.
- Make removal clean and reversible in effect, taking back exactly what the installer added and keeping user data.
- Report the installed version so a person can read it and a program can compare it without parsing prose.
- Answer which engine version a chosen target would provide without changing anything, so the companion client's installer can compare versions and install only a strictly newer engine.
- Replace confusing failures with one message naming the cause and the next action, and never leave the machine worse than before the run.

## Non-Goals

- The combined mode of the Forgel Code installer that installs both binaries together, and the version comparison and strictly-newer rule it applies.
- The declared minimum supported engine version of Forgel Code and the startup check that produces the actionable message for a missing or too-old engine.
- The Forgel Code product and its installer.
- Publishing engine release artifacts, computing release versions, or changing the release train.
- System-wide installation, installation for several users at once, and administrator-level installation.
- Installers for platforms the project does not target for terminal use, and operating-system package distributions.
- Migrating, downgrading or removing engine installations that this installer did not create.
- Unattended or scheduled upgrades; only an explicit run installs anything.

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | D-003 — The base parameterized command line stays in the engine; the separate client replaces the interactive chat mode. | User, 2026-11-16 18:31 |
| — | D-004 — The client's working name is Forgel Code; it is a separate Python client, follows a Pareto 20/80 scope and imports nothing from the engine. | User accepted the proposal, 2026-11-16 18:34 |
| — | D-005 — The companion client repository is public and lives in the same organization as the engine. | User, 2026-11-16 21:14 |
| — | D-006 — The work happens in order: machine-readable engine commands first, then the client repository and the console move, then removal of the replaced chat mode from the engine. | User accepted the proposal, 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: The installer installs the engine for the invoking user only, completes without administrator or elevated rights, and changes no other user's settings and no shared machine-wide settings.
- **FR-2**: A successful install reports the installed engine version as a single plain value on one line of its result; progress and advisory text appear elsewhere, and the reported value equals the version the installed engine reports about itself.
- **FR-3**: After a successful install the engine is runnable by name in a newly started terminal session with no further user action and without the user editing any start-up setting.
- **FR-4**: The installer's contribution to the user's terminal start-up settings is identifiable and limited to that contribution; every other user setting is preserved and repeated installs never duplicate it. When the engine would still not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.
- **FR-5**: Re-running the installer for a target that is already installed completes successfully, reports the same version again, and leaves exactly one engine reachable by name.
- **FR-6**: Re-running for a target that provides a newer version installs it, reports the newer version, and leaves no older engine competing; no re-run requires a prior removal, and no run leaves a partially replaced installation.
- **FR-7**: Removal takes back exactly what the installer added — the installed engine and the installer's start-up contribution — leaves every other user setting unchanged, and afterwards the engine is not reachable by name in a newly started terminal session.
- **FR-8**: Removal leaves the user's engine data intact, and removal when nothing was installed completes successfully with a message saying that nothing was installed.
- **FR-9**: The installer offers a read-only resolution mode that reports the engine version the chosen target source and reference would install and completes successfully, whether or not an engine is installed.
- **FR-10**: The resolution mode changes nothing: it installs nothing, changes no start-up setting, and an already installed engine keeps its version.
- **FR-11**: The resolution mode reports the version as a single plain value on one line so a caller can read and compare it; when the version cannot be determined — an unreachable source, an unknown reference, or target information that carries no version — it ends unsuccessfully, names the cause and the next action, and reports no version at all.
- **FR-12**: Target source, target reference and runtime interpreter are supplied to both modes as inputs without any interactive prompt; when an input is absent a documented default applies: the project's official distribution channel, its latest stable release, and a supported interpreter already present on the machine.
- **FR-13**: The installer requires a runtime interpreter at or above the engine's minimum supported version and, when none is present, stops before changing anything and names the required minimum and what to obtain. Any failure or interruption leaves a previously working installation working at its previous version and ends unsuccessfully with a message naming the failed step and the next action the user can take.

## User Stories

- As a user on a fresh machine, I want one action to install the engine as myself, so that I get a working engine without administrator rights, manual environment assembly or hand-edited settings.
- As a user who already installed the engine, I want repeating the same action to be safe and to give me a newer engine when one exists, so that I never have to decide whether to remove first.
- As a user who wants the machine clean again, I want one removal to take back what the installer added while keeping my engine data, so that I can start over without losing work.
- As the companion client's installer, I want to learn which engine version a chosen target provides without changing anything, so that it can compare that with an installed engine and install only when the target is strictly newer.
- As a user whose machine cannot run the engine, I want to be told plainly what is missing and what to do, rather than have the install fail halfway and leave a broken engine behind.

## Acceptance Criteria

- **AC-1**: An ordinary user runs the installer once on a machine with no engine and ends up with an engine that runs as that user; no settings of other users and no shared machine-wide settings are changed and no elevated rights are requested.
- **AC-2**: The successful install reports exactly one plain version value, and that value equals the version the installed engine reports about itself.
- **AC-3**: In a newly started terminal session the engine runs by name with no further action from the user.
- **AC-4**: After the install the user's other start-up settings are unchanged, and a second install does not duplicate the installer's contribution.
- **AC-5**: When the engine would not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.
- **AC-6**: A second run for the same target succeeds, reports the same version again, and leaves exactly one engine reachable by name.
- **AC-7**: A run for a newer target reports the newer version, the engine that runs is that newer version, no older engine competes, and no removal step was needed beforehand.
- **AC-8**: After removal the engine is no longer reachable by name in a newly started terminal session, and the user's other start-up settings match their state before the install.
- **AC-9**: User engine data present before removal is still present and unchanged afterwards.
- **AC-10**: Removal on a machine where nothing was installed succeeds and says that nothing was installed.
- **AC-11**: The resolution mode reports exactly one plain version value and completes successfully, both when no engine is installed and when one is.
- **AC-12**: The resolution mode leaves the machine unchanged: the installed state, the settings and any installed engine's version are exactly as before it ran.
- **AC-13**: The version the resolution mode reports equals the version that an install of the same target then produces.
- **AC-14**: When the version cannot be determined, the resolution mode ends unsuccessfully, names the cause and the next action, and reports no version value at all.
- **AC-15**: Supplied target source, target reference and runtime interpreter are honoured by both modes, and the value the resolution mode reports matches what the install then produces.
- **AC-16**: With no supported runtime interpreter present, the install stops before changing anything, ends unsuccessfully, and names the required minimum and what to obtain.
- **AC-17**: A failure partway through an install over an existing installation leaves that engine running and reporting its previous version.

## Work Packages

### 1. Unprivileged per-user install and version report
- The installer installs the engine for the invoking user only, completes without administrator or elevated rights, and changes no other user's settings and no shared machine-wide settings.
- A successful install reports the installed engine version as a single plain value on one line of its result; progress and advisory text appear elsewhere, and the reported value equals the version the installed engine reports about itself.
- An ordinary user runs the installer once on a machine with no engine and ends up with an engine that runs as that user; no settings of other users and no shared machine-wide settings are changed and no elevated rights are requested.
- The successful install reports exactly one plain version value, and that value equals the version the installed engine reports about itself.

### 2. Reachable engine in a newly started terminal session
- After a successful install the engine is runnable by name in a newly started terminal session with no further user action and without the user editing any start-up setting.
- The installer's contribution to the user's terminal start-up settings is identifiable and limited to that contribution; every other user setting is preserved and repeated installs never duplicate it. When the engine would still not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.
- In a newly started terminal session the engine runs by name with no further action from the user.
- After the install the user's other start-up settings are unchanged, and a second install does not duplicate the installer's contribution.
- When the engine would not be reachable by name — including when an older engine would be chosen first — the install ends unsuccessfully, names the cause and the next action, and does not report success.

### 3. Safe repetition and upgrade
- Re-running the installer for a target that is already installed completes successfully, reports the same version again, and leaves exactly one engine reachable by name.
- Re-running for a target that provides a newer version installs it, reports the newer version, and leaves no older engine competing; no re-run requires a prior removal, and no run leaves a partially replaced installation.
- A second run for the same target succeeds, reports the same version again, and leaves exactly one engine reachable by name.
- A run for a newer target reports the newer version, the engine that runs is that newer version, no older engine competes, and no removal step was needed beforehand.

### 4. Clean removal
- Removal takes back exactly what the installer added — the installed engine and the installer's start-up contribution — leaves every other user setting unchanged, and afterwards the engine is not reachable by name in a newly started terminal session.
- Removal leaves the user's engine data intact, and removal when nothing was installed completes successfully with a message saying that nothing was installed.
- After removal the engine is no longer reachable by name in a newly started terminal session, and the user's other start-up settings match their state before the install.
- User engine data present before removal is still present and unchanged afterwards.
- Removal on a machine where nothing was installed succeeds and says that nothing was installed.

### 5. Read-only version answer for another installer
- The installer offers a read-only resolution mode that reports the engine version the chosen target source and reference would install and completes successfully, whether or not an engine is installed.
- The resolution mode changes nothing: it installs nothing, changes no start-up setting, and an already installed engine keeps its version.
- The resolution mode reports the version as a single plain value on one line so a caller can read and compare it; when the version cannot be determined — an unreachable source, an unknown reference, or target information that carries no version — it ends unsuccessfully, names the cause and the next action, and reports no version at all.
- The resolution mode reports exactly one plain version value and completes successfully, both when no engine is installed and when one is.
- The resolution mode leaves the machine unchanged: the installed state, the settings and any installed engine's version are exactly as before it ran.
- The version the resolution mode reports equals the version that an install of the same target then produces.
- When the version cannot be determined, the resolution mode ends unsuccessfully, names the cause and the next action, and reports no version value at all.

### 6. Inputs, runtime check and failure safety
- Target source, target reference and runtime interpreter are supplied to both modes as inputs without any interactive prompt; when an input is absent a documented default applies: the project's official distribution channel, its latest stable release, and a supported interpreter already present on the machine.
- The installer requires a runtime interpreter at or above the engine's minimum supported version and, when none is present, stops before changing anything and names the required minimum and what to obtain. Any failure or interruption leaves a previously working installation working at its previous version and ends unsuccessfully with a message naming the failed step and the next action the user can take.
- Supplied target source, target reference and runtime interpreter are honoured by both modes, and the value the resolution mode reports matches what the install then produces.
- With no supported runtime interpreter present, the install stops before changing anything, ends unsuccessfully, and names the required minimum and what to obtain.
- A failure partway through an install over an existing installation leaves that engine running and reporting its previous version.

## Scope Boundaries

- A single-action installer for the engine that installs for the invoking user only, without elevated rights.
- Making the engine reachable by name in a newly started terminal session without the user editing anything.
- Safe repetition of the installer, including installing a newer chosen target over an existing installation.
- A removal path that takes back exactly what the installer added, is safe when nothing was installed, and keeps user data.
- Reporting the installed engine version as one plain value at the end of a successful install.
- A read-only mode that reports the engine version the chosen target would install, changing nothing on the machine.
- Accepting the target source, target reference and runtime interpreter as inputs, with documented defaults and no interactive prompts.
- Checking for a supported runtime before anything is changed, and failing without damaging a previously working installation.
- The combined mode of the Forgel Code installer that installs both binaries together, and the version comparison and strictly-newer rule it applies.
- The declared minimum supported engine version of Forgel Code and the startup check that produces the actionable message for a missing or too-old engine.
- The Forgel Code product and its installer.
- Publishing engine release artifacts, computing release versions, or changing the release train.
- System-wide installation, installation for several users at once, and administrator-level installation.
- Installers for platforms the project does not target for terminal use, and operating-system package distributions.
- Migrating, downgrading or removing engine installations that this installer did not create.
- Unattended or scheduled upgrades; only an explicit run installs anything.

## Risks

- The external interfaces this task needs were not investigated to completion, so the release distribution channel and its version metadata remain unverified; the resolution mode cannot be shown to report a real version until that interface is recorded. This is the main risk of the task.
- The resolution mode is a contract consumed by another task's installer; if 'one plain value, no side effects' is weakened, the combined installer's comparison becomes unreliable and the pair fails as a whole rather than locally.
- Verification that the engine is reachable in a newly started terminal session is environment sensitive: a machine that does not apply the user's start-up configuration, or that already offers an older engine, can fail in ways users read as an installer bug rather than a conflict.
- A per-user install differs from the source-checkout workflow the project documents today, which may confuse existing users and any documentation that still describes only that path.
- Upgrades over an existing installation risk leaving a half-replaced install; verifying before replacing adds steps that must themselves be exercised, otherwise a failed upgrade breaks a working install.
- Removal touching start-up settings can damage unrelated configuration if the installer's contribution is not reliably delimited on every path, including the case where a user edited it by hand.
- The engine release train publishes versions; this task must not imply or hardcode one, or it contradicts the rule that a published release is immutable.
- The task intent belongs to a milestone that also covers the companion client; any cross-task interface beyond the resolution mode, if left unstated, is a risk to the pair rather than to this task alone.

## Open Questions

- None.

## Assumptions

- The engine is distributed as a versioned installable artifact that carries its own version, so the resolution mode can report a version without running the engine.
- The default source is the project's official distribution channel and the default reference is its latest stable release; both are replaceable inputs.
- The install location is a single location owned by and reserved for the invoking user, created when absent; no shared location is ever used.
- When no interpreter is supplied the installer uses a supported interpreter already present on the machine and never installs one itself.
- The reported version is the plain engine version with no label, so a caller can compare it as-is.
- Removal is a mode of the same installer rather than a separate artifact.
- An install over an existing installation replaces it only after the new installation is verified, so the previous version keeps working until then.
- Engine data lives independently of the install location, which is why removal can leave it alone.
- When the user's terminal start-up configuration is of a kind the installer cannot change safely, the installer reports that as a failure with instructions instead of guessing.

## Related Documents

- README.md
- PLAN.md
- FORGEL.md
- AGENTS.md
- CONTRIBUTING.md
- pyproject.toml
- docs/program/decisions.md

## Revision History

- 1.0.0 — placeholder blocked because the specification needed a decision; no requirements, acceptance or dependencies recorded, and the required external interfaces were not investigated.
- 1.1.0 — rewritten as a complete specification covering the per-user install, reachability in a newly started terminal session, safe repetition, clean removal, the read-only version answer another installer consumes, inputs with defaults, the supported-runtime check and safe failure.
- 1.2.0 — respec: split the flat requirement and acceptance set into six cohesive work packages with integer indices and at most four acceptance criteria each; removed implementation detail from requirements, acceptance, constraints, goals, user stories, risks and assumptions, keeping those details only in the external-dependency records; acceptance stated as observable outcomes with no test command or automated check.
- 1.3.0 — respec: every work package carries an explicit title and the indices are JSON integers; requirement and acceptance coverage is unchanged.
- 1.4.0 — respec: constraints no longer name a repository rule file or a commit step; the language and documentation-review rules are restated as behaviour, and the release rule is restated as immutability of a published version, with no product choice left open.


## Summary

Added the engine's one-command per-user installer and its read-only version resolution, plus the documentation that states its behavior.

- `install.sh` (new): a POSIX `sh` installer with three non-interactive modes — install/upgrade (default), `--resolve`, `--uninstall`. It installs only for the invoking user under `~/.local/share/forgel` with the `forgel` launcher under `~/.local/bin`, adds one delimited, self-identifying block to one user start-up file (never duplicating it and preserving every other line), starts a terminal session the way the user's settings would and fails with cause plus next action when the engine is not reachable by name or an older engine would win. It resolves the target, stages and verifies the engine (asking the engine for its own version) before replacing anything live, rolls back on failure, and prints exactly one plain version value on stdout equal to what the installed engine reports. `--resolve` prints the version the target would install and writes nothing; `--uninstall` removes exactly the launcher, the installer's block and the install root, keeps engine data, and reports when nothing was installed. Inputs come only from the environment (`FORGEL_SOURCE`, `FORGEL_REF`, `FORGEL_PYTHON`, `FORGEL_INSTALL_ROOT`, `FORGEL_BIN_DIR`) with documented defaults; the runtime check stops before any change and names the minimum (Python 3.11) and what to obtain.
- `tests/test_install.py` (new): 13 end-to-end tests running the real script against an isolated home and target trees — resolve output/side effects/failure, install version equals the engine's own `version --json`, reachability in a newly started session, preserved settings and no duplicate block, idempotent re-run, newer target replacing the older one with a single reachable engine, clean removal with data intact and empty-session afterwards, no-op removal message, missing interpreter stopping with nothing changed, a shadowing engine failing and restoring settings, and a failed upgrade keeping the previous engine working.
- `docs/install.md` (new) and a short `README.md` install section: states the behavior, the three modes, the output contract, the inputs and defaults, the start-up contribution and the failure/repetition rules. Documentation only; no check reads it.

Tested with the repository gate `python3 -m unittest discover -s tests` (819 tests, OK) and the new installer suite (13 tests, OK).

## Files Changed

- `README.md`
- `docs/install.md`
- `install.sh`
- `tests/test_install.py`

## Commands

- `["python3", "-m", "unittest", "tests.test_install", "-v"]` → exit 1
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 5
- `["python3", "-m", "unittest", "tests.test_install", "-v"]` → exit 1
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 5
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 1
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-p", "test_install.py", "-v"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests"]` → exit 0

## Final Test Output

```
[agent] 20261128002311_inspect-and-finish: context handoff to session 2 (~6510/3072 tokens)
[agent] 20261128002317_record-the-handoff: context handoff to session 2 (~2758/3072 tokens)
[agent] 20261128002317_record-the-handoff: context handoff to session 3 (~7033/3072 tokens)
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[intake] running
[intake] completed
[jurisdiction] running
[jurisdiction] completed
[recipe] running
[recipe] completed
[architecture] running
[architecture] completed
[repo_plan] running
[repo_plan] completed
[feature_plan] running
[feature_plan] completed
[spec] running
[spec] completed
[spec_review] running
[spec_review] completed
[dev] running
[dev] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[review] running
[review] completed
[qa] running
[qa] completed
[acceptance] running
[acceptance] completed
[audit] running
[audit] completed
[approval] running
[approval] awaiting staging approval (pending)
[approval] running
[approval] completed
[done] running
[done] completed
[github] GitHub API is unreachable; the branch is pushed without pull-request checks
[github] demo-be1e699a: no API credentials (no usable GitHub credentials; GitHub App is not configured; no PAT; no GitHub CLI session); pushing the branch without a pull request
.........................................................................error: unknown project 'missing-project'
..error: unknown project 'missing-project'
...[model] script mode: /private/var/folders/2g/9_qkdxhs6hx0fm8bm1wtlshr0000gq/T/tmps80js3mp/model-script.json does not exist
.....error: say needs text: --text "..." or a trailing argument
................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 819 tests in 159.100s

OK

```

## Actions

- search_files: install @ . *.sh
- list_files
- search_files: install\.sh @ . *
- search_files: install @ src *.py
- search_files: *.sh @ . *
- search_files: forgel-code @ . *
- search_files: pipx|PyPI|pypi|latest stable|download @ . *
- search_files: install\.sh @ docs *
- search_files: curl -fsSL @ . *
- search_files: scripts/ @ . *
- read_file: docs/program/specs/20261124152248_add-the-engine-s-one-command-installer-w.md
- read_file: pyproject.toml
- search_files: 20261124145600 @ . *
- read_file: src/forgel/engine_version.py
- search_files: install @ README.md *
- search_files: install\.sh @ . *
- read_file: Makefile
- read_file: tests/test_engine_version.py
- read_file: tests/test_presets.py
- search_files: install @ PLAN.md *
- read_file: README.md
- read_file: docs/program/agent/20261119210845_install-forgel-code-with-one-command-via.md
- read_file: src/forgel/entry.py
- search_files: registry|jurisdiction @ src/forgel *.py
- read_file: src/forgel/engine_version.py
- search_files: distribution channel|PyPI|pipx @ docs/program/decisions.md *
- read_file: src/forgel/config.py
- read_file: src/forgel/client_cli.py
- recall
- recall
- recall
- recall
- list_files
- search_files: install @ tests
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
- recall
- recall
- read_file: install.sh
- read_file: install.sh
- read_file: install.sh
- list_files
- search_files: install @ docs *.md
- search_files: docs/install.md @ . *.md
- list_files
- search_files: install @ tests *.py
- search_files: test_install @ .
- read_file: pyproject.toml
- recall
- read_file: src/forgel/engine_version.py
- write_file: docs/install.md
- read_file: src/forgel/entry.py
- read_file: src/forgel/client_cli.py
- search_files: def envelope|def write @ src/forgel *.py
- search_files: forgel_home|FORGEL_HOME|"\.forgel @ src/forgel/config.py
- read_file: install.sh
- run: ['python3', '-m', 'unittest', 'tests.test_install', '-v']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- search_files: class InstallerTest @ . *.py
- read_file: tests/test_install.py
- write_file: tests/test_install.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- edit_file: install.sh
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- read_file: install.sh
- read_file: tests/test_install.py
- edit_file: tests/test_install.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- edit_file: install.sh
- read_file: install.sh
- search_files: ^#|install @ README.md *.md
- search_files: ##  @ README.md
- read_file: README.md
- read_file: README.md
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_install.py', '-v']
- read_file: README.md
- edit_file: README.md
- run: ['sh', '-n', 'install.sh']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests']
- search_files: registry @ src/forgel *.py
- read_file: src/forgel/config.py
- search_files: pip install @ README.md
- read_file: install.sh
