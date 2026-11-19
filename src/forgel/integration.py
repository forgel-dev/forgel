"""Whether a project needs a program e2e and whether the contract provides one.

The program e2e tests the whole construction, not one repository. It is
required when repositories interact (a ``depends_on`` edge), when the project
has a frontend/acceptance repository, or when the environment mounts sibling
repositories. These are hard requirements: the planner and QA refuse to work
around them.

A mobile repository is different. A simulator or emulator is expensive,
platform-bound and often absent on one of the machines the project runs on.
Its e2e is expected, but a missing or unavailable simulator is a deferred
requirement: the planner records a warning instead of blocking, and QA records
the e2e step as ``skipped`` with instructions. The e2e can be added later once
the dependency is installed.

A database or a cache that the project's unit-test framework already handles
is not a reason for a program e2e. External tools without a standard test
harness (a browser, a live service, a broker) belong in a real-interface
command check; a mobile simulator is the one heavy exception handled here.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .environment import Environment
from .layout import ProjectLayout
from .program_manifest import entries

FRONTEND_ROLES = {"frontend", "acceptance", "e2e"}
MOBILE_ROLES = {"mobile", "ios", "android"}


def _repo_reasons(
    repos: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    deferred: list[str] = []
    edges = [
        (str(repo.get("id")), str(parent))
        for repo in repos
        for parent in (repo.get("depends_on") or [])
    ]
    if edges:
        hard.append(
            "repositories interact: "
            + ", ".join(f"{child}->{parent}" for child, parent in edges)
        )
    roles = {str(repo.get("role") or "") for repo in repos}
    special = sorted(roles & FRONTEND_ROLES)
    if special:
        hard.append(
            "the project has a " + "/".join(special) + " repository"
        )
    mobile = sorted(roles & MOBILE_ROLES)
    if mobile:
        deferred.append(
            "the project has a " + "/".join(mobile) + " repository "
            "(needs a simulator or emulator)"
        )
    return hard, deferred


def integration_reasons(
    layout: ProjectLayout,
    environment: Environment | None,
    extra_repos: Sequence[Mapping[str, Any]] = (),
) -> tuple[list[str], list[str]]:
    """Hard and deferred reasons a program e2e is expected."""

    repos = [*entries(layout), *extra_repos]
    hard, deferred = _repo_reasons(repos)
    if environment is not None and environment.mounts:
        hard.append("the environment mounts sibling repositories")
    return hard, deferred


def integration_required(
    layout: ProjectLayout,
    environment: Environment | None,
    extra_repos: Sequence[Mapping[str, Any]] = (),
) -> tuple[bool, str]:
    """Whether a program e2e is expected at all, and why."""

    hard, deferred = integration_reasons(
        layout, environment, extra_repos
    )
    reasons = [*hard, *deferred]
    return bool(reasons), "; ".join(reasons)


def integration_problem(
    layout: ProjectLayout,
    environment: Environment | None,
    extra_repos: Sequence[Mapping[str, Any]] = (),
) -> str:
    """A hard reason the project lacks a required program e2e, or ``""``."""

    hard, _deferred = integration_reasons(
        layout, environment, extra_repos
    )
    if not hard:
        return ""
    if environment is not None and environment.e2e:
        return ""
    return (
        f"the project needs a program e2e ({'; '.join(hard)}); declare "
        "e2e commands in environment.yaml and provide the image, services "
        "and tools they need"
    )


def integration_warning(
    layout: ProjectLayout,
    environment: Environment | None,
    extra_repos: Sequence[Mapping[str, Any]] = (),
) -> str:
    """The deferred mobile e2e note, or ``""``."""

    _hard, deferred = integration_reasons(
        layout, environment, extra_repos
    )
    if not deferred:
        return ""
    if environment is not None and environment.e2e:
        return ""
    return (
        "the project has a mobile repository, so a program e2e with a "
        f"simulator or emulator is expected ({'; '.join(deferred)}). It is "
        "deferred until that environment is available; add the e2e step "
        "later after installing the simulator or emulator"
    )
