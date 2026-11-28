# Installing Forgel for one user

Forgel has a one-command installer. It installs the engine for the invoking
user on Linux and macOS, without administrator rights, without a shared
location and without asking questions, so another installer can drive it
unattended. Before you start, satisfy its prerequisites: a Linux or macOS
machine, a checkout of this repository, and Python 3.11 or newer on `PATH`.
Nothing else is required, and the command below — run from the checkout root —
is the complete install step.

```
sh install.sh
```

Progress, advice and failures go to standard error. Standard output carries
exactly one line on success: the installed engine version as a plain value.
Start a new terminal session and run `forgel`; no start-up setting needs to be
edited by hand.

## Placing the engine and reaching it

The installer puts the engine under `FORGEL_INSTALL_ROOT` and its entry point
at `FORGEL_BIN_DIR` as the `forgel` command. It then makes that directory
reachable in newly started terminal sessions, and checks a newly started
session the way your start-up settings would: when the name does not reach the
installed engine there — including when an older engine would be chosen first
— the install ends unsuccessfully, names the cause and the next action, and
reports no version.

A session that was already running keeps the start-up settings it read before
the install. Start a new one. When the name is still missing there, run the
entry point by its full path — `~/.local/bin/forgel` by default, or the
`forgel` command in the command directory the installer named — and check that
your shell reads the start-up file the installer named; adding that directory
to `PATH` in the file your shell reads has the same effect.

## Confirming the installation

Ask the installed engine which version it is:

```
forgel version --json
```

The answer is exactly one JSON object on standard output, and its `version`
field is the installed engine version — the same value the install reported.
Reading it needs no project, no model credential and no particular working
directory, and it writes nothing. A program consumes that object directly
instead of interpreting human-oriented text, so this report is the supported
way for another tool to judge engine compatibility. When the engine cannot
state a comparable version, the command ends unsuccessfully, names the cause
and reports no version, so a caller never reads a partial answer.

When the name `forgel` does not reach the entry point in the session at hand,
run `$FORGEL_BIN_DIR/forgel version --json`; the report is the same.

## Answering which version a target would install

```
sh install.sh --resolve
```

This mode answers one question and changes nothing: it installs nothing, edits
no start-up setting and leaves an installed engine at its version. Standard
output carries exactly one line, the version the same inputs would install, so
a caller can read and compare it. When the version cannot be determined — an
unreachable source, an unknown reference, or target information that carries no
version — the mode ends unsuccessfully, names the cause and the next action,
and reports no version at all.

## Removing the installation

```
sh install.sh --uninstall
```

Removal takes back exactly what the installer added: the installed engine
under `FORGEL_INSTALL_ROOT` and the `forgel` entry point in `FORGEL_BIN_DIR`,
together with the installer's contribution to the user's terminal start-up
settings. It leaves every other line of that file as it was and keeps the
user's own configuration and project material under `~/.forgel`, which the
engine's home holds. Afterwards `forgel` is no longer reachable by name in a
newly started terminal session. When nothing was installed, removal succeeds
and says that nothing was installed.

## Inputs

The installer reads its inputs from the environment and never prompts.

| Input | Default | Meaning |
|-------|---------|---------|
| `FORGEL_SOURCE` | the official distribution channel (PyPI) | the target source: the engine source tree directory, or a channel address |
| `FORGEL_REF` | the latest stable release | the target reference: a release version, or `latest` |
| `FORGEL_PYTHON` | a supported interpreter already on `PATH` | the runtime interpreter |
| `FORGEL_INSTALL_ROOT` | `~/.local/share/forgel` | the install location, owned by and reserved for the invoking user |
| `FORGEL_BIN_DIR` | `~/.local/bin` | the directory that holds the `forgel` command |

Both modes read the same inputs, so a caller can resolve a target and then
install that same target; the version the resolution mode reports is the
version that install then produces. An unknown or unsupported value ends
unsuccessfully with a message naming the cause and the next action.

The resolved version is what an already installed engine is compared against.
The comparison rule is strictly newer: only an available version that is
strictly newer than the installed one replaces it, and an equal or older
available version leaves the installed engine untouched. `sh install.sh`
installs the target it resolved, so a tool that keeps the engine current asks
for the available version first and installs only when the rule says to.

## Requirements

The engine needs Python 3.11 or newer. When no interpreter at or above that
version is present, the installer stops before changing anything, ends
unsuccessfully and names the required minimum and what to obtain. The
installer never installs an interpreter itself.

Platforms other than Linux and macOS are reported as unsupported rather than
partially supported.

## The start-up contribution

The installer makes the engine reachable in newly started terminal sessions by
adding one delimited block to one start-up file of the invoking user. The block
names itself and the command that removes it, so it is identifiable without
guesswork. Every other line of that file is preserved, and repeated installs
replace the block instead of adding another one.

After installing, the installer starts a terminal session the way the user's
start-up settings would and checks what it reaches by name. When the engine is
not reachable that way — including when an older engine would be chosen first —
the install ends unsuccessfully, names the cause and the next action, and does
not report a version.

## Repeating and upgrading

Running the same installer again is the supported way to repair or upgrade an
installation. A run for the target that is already installed reports the same
version again; a run for a newer target installs it, reports the newer version
and leaves no older engine competing. No prior removal is needed and no run
leaves a partially replaced installation: the chosen target is prepared and
checked before anything live is replaced.

## Failure safety

Every failure or interruption ends unsuccessfully with a message naming the
failed step and the next action the user can take, and leaves a previously
working installation working at its previous version. Nothing outside the
invoking user's own home and the chosen install location is changed.
