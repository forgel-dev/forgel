#!/bin/sh
# Forgel engine installer: one action, for the invoking user only.
#
# Modes, inputs and defaults are documented in docs/install.md. Standard output
# carries one plain value and nothing else: the engine version for an install
# and for --resolve, and the outcome line for --uninstall. Progress, advice and
# every failure message go to standard error.

set -eu

MIN_MAJOR=3
MIN_MINOR=11
MARKER='# Installed by the Forgel installer'
MARKER_START='# >>> forgel installer >>>'

MODE=install
ROOT=${FORGEL_INSTALL_ROOT:-${HOME:-}/.local/share/forgel}
BIN=${FORGEL_BIN_DIR:-${HOME:-}/.local/bin}
SOURCE=${FORGEL_SOURCE:-pypi}
REF=${FORGEL_REF:-latest}
PYTHON_INPUT=${FORGEL_PYTHON:-}

STEP=''
STAGE=''
BACKUP=''
PUBLISHED=''
PROFILE=''
BLOCK_STATE='absent'
ROOT_CREATED=0
BIN_CREATED=0
PY=''

HELPER=$(cat <<'PYTHON'
"""The installer's parsing and probing, kept in one program.

``install.sh`` invokes it with a subcommand and never by a user directly.
Every failure raises :class:`Failure`, which writes a cause and the next action
to standard error and exits non-zero, so standard output stays the only place a
caller reads a value from.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import NoReturn

CHANNEL = "https://pypi.org/pypi/forgel/json"
CHANNELS = {"", "pypi", "channel", "official"}
DISTRIBUTION = "forgel"
VERSION = re.compile(r"^v?(\d+\.\d+\.\d+)$")
LATEST = {"", "latest", "latest-stable", "stable"}
START = "# >>> forgel installer >>>"
END = "# <<< forgel installer <<<"
LAUNCHER_MARK = "# Installed by the Forgel installer"

PYTHON_LAUNCHER = '''"""Start the installed engine from its own tree."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for candidate in (os.path.join(HERE, "src"), HERE):
    if os.path.isdir(os.path.join(candidate, "forgel")):
        sys.path.insert(0, candidate)
        break

from forgel.entry import main

raise SystemExit(main(sys.argv[1:]))
'''


class Failure(Exception):
    """A step that cannot be completed, with the action that follows it."""

    def __init__(self, cause: str, next_action: str) -> None:
        super().__init__(cause)
        self.cause = cause
        self.next_action = next_action


def fail(cause: str, next_action: str) -> NoReturn:
    raise Failure(cause, next_action)


def comparable(raw: object) -> str:
    """The version carried by ``raw`` as ``major.minor.patch``, or empty."""

    if not isinstance(raw, str):
        return ""
    match = VERSION.match(raw.strip())
    return match.group(1) if match else ""


def ordering(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


def reported_version(text: str) -> str:
    """The engine version the engine's own report carries, or empty."""

    version = ""
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("ok"):
            found = comparable(data.get("version"))
            if found:
                version = found
    return version


def resolve(source: str, reference: str) -> str:
    """The version the target source and reference would install."""

    text = source.strip()
    if text.lower() in CHANNELS:
        text = CHANNEL
    tree = Path(text).expanduser()
    if tree.is_dir():
        return resolve_tree(tree, reference)
    if text.startswith(("http://", "https://")):
        return resolve_channel(text, reference)
    fail(
        f"the target source '{source}' is neither a directory nor a channel address",
        "set FORGEL_SOURCE to the engine source tree or to the official channel "
        "(pypi), then run the installer again",
    )


def resolve_tree(root: Path, reference: str) -> str:
    declaration = root / "pyproject.toml"
    if not declaration.is_file():
        fail(
            f"the target source '{root}' carries no version information",
            "point FORGEL_SOURCE at an engine source tree, or leave it unset to "
            "use the official channel",
        )
    if not (root / "src" / "forgel" / "__init__.py").is_file():
        fail(
            f"the target source '{root}' is not an engine source tree",
            "point FORGEL_SOURCE at the engine repository root, or leave it "
            "unset to use the official channel",
        )
    try:
        data = tomllib.loads(declaration.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        fail(
            f"the version declaration in '{declaration}' cannot be read: {exc}",
            "check that the file is readable and is a valid pyproject.toml, then "
            "run the installer again",
        )
    project = data.get("project")
    declared = project.get("version") if isinstance(project, dict) else None
    version = comparable(declared)
    if not version:
        fail(
            f"the target source '{root}' carries no comparable version",
            "declare the engine version in pyproject.toml, or leave FORGEL_SOURCE "
            "unset to use the official channel",
        )
    return choose(version, reference, f"the target source '{root}'")


def choose(available: str, reference: str, what: str) -> str:
    wanted = reference.strip()
    if wanted.lower() in LATEST:
        return available
    version = comparable(wanted)
    if not version:
        fail(
            f"the target reference '{reference}' is not a release version",
            "pass FORGEL_REF=latest or a version such as 0.1.0, then run the "
            "installer again",
        )
    if version != available:
        fail(
            f"{what} provides version {available}, not {version}",
            f"pass FORGEL_REF=latest or FORGEL_REF={available}, then run the "
            "installer again",
        )
    return version


def resolve_channel(url: str, reference: str) -> str:
    data = fetch(url)
    known: list[str] = []
    releases = data.get("releases")
    if isinstance(releases, dict):
        for name in releases:
            version = comparable(name)
            if version:
                known.append(version)
    info = data.get("info")
    latest = comparable(info.get("version")) if isinstance(info, dict) else ""
    if latest and latest not in known:
        known.append(latest)
    if not known:
        fail(
            f"the target source '{url}' carries no release version",
            "check FORGEL_SOURCE and FORGEL_REF, or leave FORGEL_SOURCE unset to "
            "use the official channel",
        )
    ordered = sorted(set(known), key=ordering)
    wanted = reference.strip()
    if wanted.lower() in LATEST:
        return ordered[-1]
    version = comparable(wanted)
    if not version:
        fail(
            f"the target reference '{reference}' is not a release version",
            "pass FORGEL_REF=latest or a version such as 0.1.0, then run the "
            "installer again",
        )
    if version not in ordered:
        fail(
            f"the target source '{url}' has no release {version}",
            f"pass FORGEL_REF=latest or one of {', '.join(ordered[-3:])}, then "
            "run the installer again",
        )
    return version


def fetch(url: str) -> dict[str, object]:
    """The channel's release document, as the channel itself serves it."""

    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "forgel-installer"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        fail(
            f"the target source '{url}' cannot be reached: {exc}",
            "check the network connection and the source address, then run the "
            "installer again",
        )
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        fail(
            f"the target source '{url}' did not answer with release information: {exc}",
            "check the source address, then run the installer again",
        )
    if not isinstance(data, dict):
        fail(
            f"the target source '{url}' did not answer with release information",
            "check the source address, then run the installer again",
        )
    return data


def stage(source: str, version: str, destination: str) -> None:
    """Prepare the engine tree in ``destination`` without touching a live one."""

    text = source.strip()
    if text.lower() in CHANNELS:
        text = CHANNEL
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    tree = Path(text).expanduser()
    if tree.is_dir():
        copy_tree(tree, target)
    elif text.startswith(("http://", "https://")):
        unpack_wheel(text, version, target)
    else:
        fail(
            f"the target source '{source}' is neither a directory nor a channel address",
            "set FORGEL_SOURCE to the engine source tree or to the official "
            "channel (pypi), then run the installer again",
        )
    (target / "forgel-launcher.py").write_text(PYTHON_LAUNCHER, encoding="utf-8")


def copy_tree(root: Path, target: Path) -> None:
    for name in ("src", "registry", "jurisdiction"):
        source = root / name
        if source.is_dir():
            try:
                shutil.copytree(source, target / name, dirs_exist_ok=True)
            except OSError as exc:
                fail(
                    f"the target source '{root}' cannot be copied: {exc}",
                    "check that you can read the source tree and write to "
                    "FORGEL_INSTALL_ROOT, then run the installer again",
                )
    try:
        shutil.copy2(root / "pyproject.toml", target / "pyproject.toml")
    except OSError as exc:
        fail(
            f"the version declaration of '{root}' cannot be copied: {exc}",
            "check that the source tree is readable, then run the installer again",
        )


def unpack_wheel(url: str, version: str, target: Path) -> None:
    data = fetch(url)
    entries: object = None
    releases = data.get("releases")
    if isinstance(releases, dict):
        entries = releases.get(version)
    if not entries:
        info = data.get("info")
        if isinstance(info, dict) and comparable(info.get("version")) == version:
            entries = data.get("urls")
    wheels = [
        entry
        for entry in (entries if isinstance(entries, list) else [])
        if isinstance(entry, dict)
        and str(entry.get("filename", "")).startswith(f"{DISTRIBUTION}-{version}-")
        and str(entry.get("filename", "")).endswith(".whl")
    ]
    if not wheels:
        fail(
            f"the target source provides no installable wheel for version {version}",
            "publish a wheel for that release, or install from an engine source "
            "tree with FORGEL_SOURCE",
        )
    wheel = wheels[0]
    filename = str(wheel.get("filename"))
    package = target.parent / f".{filename}"
    digests = wheel.get("digests")
    expected = digests.get("sha256") if isinstance(digests, dict) else None
    request = urllib.request.Request(
        str(wheel.get("url")), headers={"User-Agent": "forgel-installer"}
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            package.write_bytes(response.read())
    except (urllib.error.URLError, OSError, ValueError) as exc:
        package.unlink(missing_ok=True)
        fail(
            f"the wheel for version {version} cannot be downloaded: {exc}",
            "check the network connection, then run the installer again",
        )
    if isinstance(expected, str) and expected:
        actual = hashlib.sha256(package.read_bytes()).hexdigest()
        if actual != expected:
            package.unlink(missing_ok=True)
            fail(
                f"the wheel for version {version} does not match its published checksum",
                "run the installer again; if it repeats, report the target",
            )
    try:
        with zipfile.ZipFile(package) as archive:
            for member in archive.infolist():
                path = Path(member.filename)
                if path.is_absolute() or ".." in path.parts:
                    fail(
                        f"the wheel for version {version} contains an unsafe path",
                        "report the target release",
                    )
                archive.extract(member, target)
    except zipfile.BadZipFile as exc:
        fail(
            f"the wheel for version {version} cannot be read: {exc}",
            "run the installer again; if it repeats, report the target",
        )
    finally:
        package.unlink(missing_ok=True)
    if not (target / "forgel" / "__init__.py").is_file():
        fail(
            f"the wheel for version {version} does not carry the engine",
            "report the target release",
        )


def sh_launcher(path: str, python: str, engine: str) -> None:
    text = (
        "#!/bin/sh\n"
        f"{LAUNCHER_MARK}. Removed by: sh install.sh --uninstall\n"
        f'exec "{python}" "{engine}" "$@"\n'
    )
    target = Path(path)
    target.write_text(text, encoding="utf-8")
    target.chmod(0o755)


def check(tree: str, python: str, version: str) -> None:
    engine = Path(tree) / "forgel-launcher.py"
    try:
        completed = subprocess.run(
            [python, str(engine), "version", "--json"],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(
            f"the prepared engine cannot be started: {exc}",
            "check that the runtime interpreter works, then run the installer again",
        )
    reported = reported_version(completed.stdout)
    if completed.returncode != 0 or reported != version:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        hint = detail[-1] if detail else "no output"
        fail(
            f"the prepared engine reports {reported or 'no version'} instead of "
            f"{version}: {hint}",
            "run the installer again; if it repeats, report the target and the "
            "output of the engine's version command",
        )


def block_for(bin_dir: str) -> str:
    return (
        f"{START}\n"
        "# Added by the Forgel installer; removed by: sh install.sh --uninstall\n"
        'case ":$PATH:" in\n'
        f'  *":{bin_dir}:"*) ;;\n'
        f'  *) PATH="{bin_dir}:$PATH" ;;\n'
        "esac\n"
        "export PATH\n"
        f"{END}\n"
    )


def strip_blocks(text: str, target: Path) -> str:
    kept: list[str] = []
    inside = False
    stray = False
    found = False
    for line in text.splitlines(keepends=True):
        marker = line.strip()
        if marker == START:
            if inside:
                stray = True
            inside = True
            found = True
            continue
        if marker == END:
            if inside:
                inside = False
            else:
                stray = True
            continue
        if not inside:
            kept.append(line)
    if inside or stray:
        fail(
            f"the installer's block in '{target}' is incomplete or out of order",
            f"open '{target}' and delete the lines from '{START}' to '{END}' by "
            "hand, then run the installer again",
        )
    return "".join(kept)


def profile(path: str, bin_dir: str, mode: str) -> None:
    """Add, replace or take back the installer's start-up contribution."""

    target = Path(path)
    text = ""
    if target.is_dir():
        fail(
            f"the start-up file '{target}' is a directory, so the installer cannot edit it",
            "move that directory aside and create the file, or add the PATH line "
            "by hand and stop using the installer's start-up contribution",
        )
    if target.exists():
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            fail(
                f"the start-up file '{target}' cannot be read: {exc}",
                f"check that you own '{target}', then run the installer again",
            )
    had_block = any(line.strip() == START for line in text.splitlines())
    cleaned = strip_blocks(text, target)
    if mode == "remove":
        if cleaned == text:
            print("absent")
            return
        write_profile(target, cleaned)
        print("removed")
        return
    updated = block_for(bin_dir) + cleaned
    if updated == text:
        print("unchanged")
        return
    write_profile(target, updated)
    print("kept" if had_block else "added")


def write_profile(target: Path, text: str) -> None:
    try:
        if not text.strip() and target.exists():
            target.unlink()
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        fail(
            f"the start-up file '{target}' cannot be written: {exc}",
            f"check that you own '{target}' and that its directory is writable, "
            "then run the installer again",
        )


def session(
    shell: str, expected: str, version: str, home: str, profile_path: str, login: str
) -> None:
    """Run a newly started terminal session and check what it reaches by name."""

    probe = 'printf "FORGEL-PATH=%s\\n" "$(command -v forgel 2>/dev/null)"\nforgel version --json 2>/dev/null || true\n'
    command = [shell, "-i"]
    if login == "login":
        command.append("-l")
    command += ["-c", probe]
    environment = {
        "HOME": home,
        "SHELL": shell,
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "TERM": "dumb",
        "LC_ALL": "C",
    }
    try:
        completed = subprocess.run(
            command,
            env=environment,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(
            f"a newly started terminal session cannot be checked: {exc}",
            "run 'forgel version' in a new terminal session; if the name is "
            "missing, run the installer again",
        )
    found = ""
    for line in completed.stdout.splitlines():
        if line.startswith("FORGEL-PATH="):
            found = line[len("FORGEL-PATH=") :].strip()
    if not found:
        fail(
            "the engine is not reachable by name in a newly started terminal session",
            f"start a new terminal session and run 'forgel version'; if the name "
            f"is still missing, check that '{profile_path}' is read by '{shell}' "
            "and run the installer again",
        )
    if Path(found) != Path(expected):
        if found.startswith("/"):
            fail(
                f"a different engine at '{found}' is chosen before '{expected}' "
                "in a newly started terminal session",
                f"remove '{found}' or put '{Path(expected).parent}' ahead of it in "
                "PATH, then run the installer again",
            )
        fail(
            f"in a newly started terminal session 'forgel' is '{found}', not the "
            "installed engine",
            "remove that shell function or alias from your start-up settings, "
            "then run the installer again",
        )
    reported = reported_version(completed.stdout)
    if reported != version:
        fail(
            f"the engine a newly started terminal session runs reports "
            f"{reported or 'no version'} instead of {version}",
            "run the installer again; if it repeats, report the output of "
            "'forgel version'",
        )
    print("reachable", file=sys.stderr)


def main(argv: list[str]) -> int:
    if not argv:
        fail("the installer helper was called without a step", "run install.sh")
    step, arguments = argv[0], argv[1:]
    try:
        if step == "resolve":
            print(resolve(arguments[0], arguments[1]))
        elif step == "stage":
            stage(arguments[0], arguments[1], arguments[2])
        elif step == "check":
            check(arguments[0], arguments[1], arguments[2])
        elif step == "sh-launcher":
            sh_launcher(arguments[0], arguments[1], arguments[2])
        elif step == "profile":
            profile(arguments[0], arguments[1], arguments[2])
        elif step == "session":
            session(
                arguments[0],
                arguments[1],
                arguments[2],
                arguments[3],
                arguments[4],
                arguments[5],
            )
        else:
            fail(f"unknown installer step '{step}'", "run install.sh")
    except Failure as failure:
        print(f"error: {failure.cause}", file=sys.stderr)
        print(f"next: {failure.next_action}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PYTHON
)

info() {
    printf '%s\n' "$*" >&2
}

die() {
    printf 'error: %s\nnext: %s\n' "$1" "$2" >&2
    exit 1
}

cleanup() {
    if [ -n "$STAGE" ]; then
        rm -rf "$STAGE"
    fi
    if [ -n "$BACKUP" ]; then
        rm -f "$BACKUP"
    fi
}

trap cleanup EXIT

trap 'exit 1' INT TERM HUP

usage() {
    cat <<'USAGE'
Install Forgel for the current user. No administrator rights are needed.

Usage: sh install.sh [--resolve|--uninstall|--help]

  (no argument)   install or upgrade Forgel for this user
  --resolve       print the version the chosen target would install, change nothing
  --uninstall     remove what the installer added and keep engine data

Inputs (environment): FORGEL_SOURCE, FORGEL_REF, FORGEL_PYTHON,
FORGEL_INSTALL_ROOT, FORGEL_BIN_DIR. Defaults are in docs/install.md.
USAGE
}

platform_supported() {
    case $(uname -s 2>/dev/null || printf unknown) in
        Linux | Darwin) return 0 ;;
        *) return 1 ;;
    esac
}

check_platform() {
    if ! platform_supported; then
        die "this platform is not supported by the installer; it installs Forgel for a user on Linux and macOS" \
            "on another platform install with 'pip install forgel' and put the 'forgel' command on PATH yourself"
    fi
}

python_ok() {
    "$1" -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= ($MIN_MAJOR, $MIN_MINOR) else 1)" >/dev/null 2>&1
}

interpreter() {
    if [ -n "$PYTHON_INPUT" ]; then
        resolved=$PYTHON_INPUT
        if [ -z "$(printf '%s' "$PYTHON_INPUT" | grep / 2>/dev/null)" ]; then
            resolved=$(command -v "$PYTHON_INPUT" 2>/dev/null || printf '%s' "$PYTHON_INPUT")
        fi
        if [ ! -x "$resolved" ]; then
            die "the supplied runtime interpreter '$PYTHON_INPUT' is missing or not executable, and the engine needs Python $MIN_MAJOR.$MIN_MINOR or newer" \
                "install Python $MIN_MAJOR.$MIN_MINOR or newer, then run the installer again with FORGEL_PYTHON set to it, or unset FORGEL_PYTHON to use the interpreter already on PATH"
        fi
        if ! python_ok "$resolved"; then
            die "the supplied runtime interpreter '$PYTHON_INPUT' is older than Python $MIN_MAJOR.$MIN_MINOR, the engine's minimum supported version" \
                "install Python $MIN_MAJOR.$MIN_MINOR or newer, then run the installer again with FORGEL_PYTHON set to it"
        fi
        printf '%s' "$resolved"
        return 0
    fi
    for name in python3 python3.14 python3.13 python3.12 python3.11 python; do
        candidate=$(command -v "$name" 2>/dev/null || true)
        if [ -z "$candidate" ]; then
            continue
        fi
        if python_ok "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    die "no supported runtime interpreter was found, and the engine needs Python $MIN_MAJOR.$MIN_MINOR or newer" \
        "obtain Python $MIN_MAJOR.$MIN_MINOR or newer from python.org or your operating system, then run the installer again"
}

profile_path() {
    case ${SHELL:-} in
        */zsh | zsh) printf '%s' "$HOME/.zshrc" ;;
        */bash | bash)
            if [ "$(uname -s 2>/dev/null)" = Darwin ]; then
                printf '%s' "$HOME/.bash_profile"
            else
                printf '%s' "$HOME/.bashrc"
            fi
            ;;
        *) printf '%s' "$HOME/.profile" ;;
    esac
}

session_mode() {
    case ${SHELL:-} in
        */zsh | zsh | */bash | bash)
            if [ "$(uname -s 2>/dev/null)" = Darwin ]; then
                printf '%s' login
            else
                printf '%s' plain
            fi
            ;;
        *) printf '%s' login ;;
    esac
}

rollback() {
    if [ -n "$BACKUP" ] && [ -f "$BACKUP" ]; then
        mv -f "$BACKUP" "$BIN/forgel" 2>/dev/null || true
        BACKUP=''
    else
        rm -f "$BIN/forgel" 2>/dev/null || true
    fi
    if [ -n "$PUBLISHED" ]; then
        rm -rf "$PUBLISHED" 2>/dev/null || true
        PUBLISHED=''
    fi
    if [ "$BLOCK_STATE" = added ]; then
        "$PY" -c "$HELPER" profile "$PROFILE" "$BIN" remove >/dev/null 2>&1 || true
    fi
    if [ -n "$STAGE" ]; then
        rm -rf "$STAGE" 2>/dev/null || true
        STAGE=''
    fi
    if [ "$ROOT_CREATED" -eq 1 ] && [ -d "$ROOT" ]; then
        rmdir "$ROOT/versions" "$ROOT" 2>/dev/null || true
    fi
    if [ "$BIN_CREATED" -eq 1 ] && [ -d "$BIN" ]; then
        rmdir "$BIN" 2>/dev/null || true
    fi
}

do_resolve() {
    STEP='resolve'
    PY=$(interpreter)
    version=$("$PY" -c "$HELPER" resolve "$SOURCE" "$REF")
    printf '%s\n' "$version"
}

do_install() {
    STEP='platform'
    check_platform
    if [ -z "${HOME:-}" ]; then
        die "HOME is not set, so the installer cannot place anything for this user" \
            "set HOME to your home directory, then run the installer again"
    fi
    STEP='interpreter'
    PY=$(interpreter)
    STEP='resolve'
    version=$("$PY" -c "$HELPER" resolve "$SOURCE" "$REF")
    info "Resolved the target: Forgel $version"

    STEP='location'
    if [ ! -d "$ROOT" ]; then
        ROOT_CREATED=1
    fi
    if [ ! -d "$BIN" ]; then
        BIN_CREATED=1
    fi
    mkdir -p "$ROOT/versions" 2>/dev/null || die "the install location '$ROOT' cannot be created" \
        "check that you own '$ROOT' and its parent, or set FORGEL_INSTALL_ROOT to a directory you own, then run the installer again"
    printf 'forgel installer\n' >"$ROOT/.installer" || die "the install location '$ROOT' is not writable" \
        "check that you own '$ROOT', or set FORGEL_INSTALL_ROOT to a directory you own, then run the installer again"

    STEP='prepare'
    STAGE="$ROOT/.staging.$$"
    rm -rf "$STAGE"
    mkdir -p "$STAGE"
    info "Preparing the engine in $STAGE"
    "$PY" -c "$HELPER" stage "$SOURCE" "$version" "$STAGE"
    "$PY" -c "$HELPER" check "$STAGE" "$PY" "$version"

    STEP='publish'
    PUBLISHED="$ROOT/versions/$version-$$"
    rm -rf "$PUBLISHED"
    if ! mv "$STAGE" "$PUBLISHED"; then
        die "the prepared engine cannot be moved into '$ROOT/versions'" \
            "check the free space and your permissions on '$ROOT', then run the installer again"
    fi
    STAGE=''

    STEP='start-up settings'
    PROFILE=$(profile_path)
    info "Making the engine reachable through $PROFILE"
    BLOCK_STATE=$("$PY" -c "$HELPER" profile "$PROFILE" "$BIN" install)

    STEP='launcher'
    mkdir -p "$BIN" 2>/dev/null || die "the command directory '$BIN' cannot be created" \
        "check that you own '$BIN' and its parent, or set FORGEL_BIN_DIR to a directory you own, then run the installer again"
    if [ -f "$BIN/forgel" ]; then
        BACKUP="$ROOT/.launcher.$$"
        cp -p "$BIN/forgel" "$BACKUP"
    fi
    "$PY" -c "$HELPER" sh-launcher "$BIN/.forgel.$$" "$PY" "$PUBLISHED/forgel-launcher.py"
    if ! mv -f "$BIN/.forgel.$$" "$BIN/forgel"; then
        rm -f "$BIN/.forgel.$$"
        rollback
        die "the engine command cannot be placed at '$BIN/forgel'" \
            "check that you own '$BIN', then run the installer again"
    fi
    if [ -n "$BACKUP" ]; then
        rm -f "$BACKUP"
        BACKUP=''
    fi

    STEP='reachability'
    info "Checking a newly started terminal session"
    mode=$(session_mode)
    if ! "$PY" -c "$HELPER" session "${SHELL:-/bin/sh}" "$BIN/forgel" "$version" "$HOME" "$PROFILE" "$mode"; then
        rollback
        exit 1
    fi

    STEP='clean up'
    for old in "$ROOT/versions"/*; do
        if [ ! -e "$old" ]; then
            continue
        fi
        if [ "$old" = "$PUBLISHED" ]; then
            continue
        fi
        rm -rf "$old"
    done

    info "Installed Forgel $version; start a new terminal session to run 'forgel'."
    printf '%s\n' "$version"
}

do_uninstall() {
    STEP='uninstall'
    present=0
    if [ -f "$BIN/forgel" ] && grep -Fq "Installed by the Forgel installer" "$BIN/forgel" 2>/dev/null; then
        present=1
    fi
    if [ -f "$ROOT/.installer" ]; then
        present=1
    fi
    for candidate in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
        if [ -f "$candidate" ] && grep -Fq "$MARKER_START" "$candidate" 2>/dev/null; then
            present=1
        fi
    done
    if [ "$present" -eq 0 ]; then
        printf 'Nothing was installed for this user; nothing was removed.\n'
        return 0
    fi
    PY=$(interpreter)
    if [ -f "$BIN/forgel" ] && grep -Fq "Installed by the Forgel installer" "$BIN/forgel" 2>/dev/null; then
        rm -f "$BIN/forgel"
    fi
    for candidate in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.profile"; do
        if [ -f "$candidate" ] && grep -Fq "$MARKER_START" "$candidate" 2>/dev/null; then
            "$PY" -c "$HELPER" profile "$candidate" "$BIN" remove >/dev/null
        fi
    done
    if [ -f "$ROOT/.installer" ]; then
        rm -rf "$ROOT"
    fi
    printf 'Forgel was removed for this user; engine data was left in place.\n'
}

while [ "$#" -gt 0 ]; do
    case $1 in
        --resolve) MODE=resolve ;;
        --uninstall) MODE=uninstall ;;
        --help | -h) usage; exit 0 ;;
        *)
            printf 'error: unknown argument: %s\nnext: run with --resolve, --uninstall or no argument\n' "$1" >&2
            exit 1
            ;;
    esac
    shift
done

case $MODE in
    resolve) do_resolve ;;
    uninstall) do_uninstall ;;
    *) do_install ;;
esac
