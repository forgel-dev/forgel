# Installing Forgel for one user

Forgel has a one-command installer. It installs the engine for the invoking
user on Linux and macOS, without administrator rights, without a shared
location and without asking questions, so another installer can drive it
unattended.

```
sh install.sh
```

Progress, advice and failures go to standard error. Standard output carries
exactly one line on success: the installed engine version as a plain value,
the same version the installed engine reports about itself with
`forgel version --json`. Start a new terminal session and run `forgel`; no
start-up setting needs to be edited by hand.

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

Removal takes back exactly what the installer added: the installed engine and
the installer's contribution to the user's terminal start-up settings. It
leaves every other user setting as it was and leaves the user's engine data in
place. Afterwards `forgel` is no longer reachable by name in a newly started
terminal session. When nothing was installed, removal succeeds and says that
nothing was installed.

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
