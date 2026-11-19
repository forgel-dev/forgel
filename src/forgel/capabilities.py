"""Heavy e2e capability detection on the current machine.

A simulator, emulator or Docker daemon is expensive, platform-bound and often
absent on one of the machines a project runs on. The QA runner probes these
tools before an e2e command; when one is missing, the e2e step is recorded as
``skipped`` with an explanation and instructions instead of blocking the task.

A browser is deliberately not probed: it is installable almost everywhere and
a missing browser is reported by the e2e command itself.

The environment contract declares heavy requirements in ``e2e_requires``; when
it is silent, a mobile repository role infers the simulator requirement.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .environment import Environment
from .layout import ProjectLayout
from .program_manifest import entries


@dataclass(frozen=True)
class Capability:
    name: str
    available: bool
    detail: str
    how_to: str


def _run(argv: Sequence[str], timeout: float = 8.0) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    output = (completed.stdout + completed.stderr).strip()
    return completed.returncode == 0, output


def _ios() -> Capability:
    if sys.platform != "darwin":
        return Capability(
            "ios-simulator",
            False,
            "the iOS simulator is available only on macOS",
            "run the e2e on a Mac with Xcode and a simulator runtime, "
            "then add the e2e step",
        )
    if not shutil.which("xcrun"):
        return Capability(
            "ios-simulator",
            False,
            "Xcode command-line tools are not installed",
            "install Xcode and its command-line tools, install a simulator "
            "runtime, open Xcode once, then add the e2e step",
        )
    ok, output = _run(
        ["xcrun", "simctl", "list", "devices", "available"]
    )
    if not ok:
        return Capability(
            "ios-simulator",
            False,
            "xcrun simctl is not usable",
            "install an iOS simulator runtime in Xcode, then add the "
            "e2e step",
        )
    if not output.strip():
        return Capability(
            "ios-simulator",
            False,
            "no iOS simulator device is available",
            "install a simulator runtime in Xcode and create a device, "
            "then add the e2e step",
        )
    return Capability(
        "ios-simulator", True, "xcrun simctl is available", ""
    )


def _android_emulator() -> Path | None:
    found = shutil.which("emulator")
    if found:
        return Path(found)
    for variable in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        root = os.environ.get(variable, "").strip()
        if not root:
            continue
        candidate = Path(root) / "emulator" / "emulator"
        if candidate.is_file():
            return candidate
    return None


def _android() -> Capability:
    adb = shutil.which("adb")
    emulator = _android_emulator()
    if emulator is None:
        return Capability(
            "android-emulator",
            False,
            "the Android emulator is not installed"
            + ("" if adb else " (adb is missing too)"),
            "install the Android SDK and an emulator, create an AVD, then "
            "add the e2e step",
        )
    ok, output = _run(
        [str(emulator), "-list-avds"], timeout=15.0
    )
    devices = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.strip().startswith("INFO")
    ]
    if not ok or not devices:
        return Capability(
            "android-emulator",
            False,
            "no Android AVD is configured",
            "create an AVD in Android Studio or with avdmanager, then add "
            "the e2e step",
        )
    return Capability(
        "android-emulator",
        True,
        "an Android AVD is available",
        "",
    )


def _docker() -> Capability:
    if not shutil.which("docker"):
        return Capability(
            "docker",
            False,
            "Docker is not installed",
            "install Docker, start the daemon and add the e2e step",
        )
    ok, output = _run(["docker", "info"], timeout=10.0)
    if not ok:
        return Capability(
            "docker",
            False,
            "the Docker daemon is not reachable",
            "start Docker and add the e2e step",
        )
    return Capability("docker", True, "the Docker daemon is reachable", "")


def _mobile_simulator() -> Capability:
    ios = _ios()
    android = _android()
    if ios.available or android.available:
        detail = "; ".join(
            item.detail for item in (ios, android) if item.available
        )
        return Capability(
            "mobile-simulator", True, detail or "a mobile simulator is available", ""
        )
    return Capability(
        "mobile-simulator",
        False,
        "neither an iOS simulator nor an Android emulator is available",
        "install Xcode with a simulator runtime on macOS, or the Android "
        "SDK with an AVD, then add the e2e step",
    )


def check(name: str) -> Capability:
    if name == "ios-simulator":
        return _ios()
    if name == "android-emulator":
        return _android()
    if name == "mobile-simulator":
        return _mobile_simulator()
    if name == "docker":
        return _docker()
    return Capability(name, True, "not probed", "")


def required(
    environment: Environment | None, layout: ProjectLayout
) -> list[str]:
    """Heavy requirements declared by the contract or inferred from roles."""

    if environment is not None and environment.e2e_requires:
        return list(environment.e2e_requires)
    roles = {str(entry.get("role") or "") for entry in entries(layout)}
    if "ios" in roles:
        return ["ios-simulator"]
    if "android" in roles:
        return ["android-emulator"]
    if "mobile" in roles:
        return ["mobile-simulator"]
    return []


def unavailable(
    environment: Environment | None, layout: ProjectLayout
) -> list[Capability]:
    return [
        capability
        for name in required(environment, layout)
        if not (capability := check(name)).available
    ]


def message(capabilities: Sequence[Capability]) -> str:
    lines = [
        f"e2e skipped: {item.name} is not available ({item.detail}). "
        f"To enable it: {item.how_to}."
        for item in capabilities
    ]
    return "\n".join(lines)
