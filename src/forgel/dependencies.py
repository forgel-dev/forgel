"""Investigate the external dependencies of a task before it is queued.

An external service, tool or format is deterministic from the outside, so the
client cannot guess its interface. This scout reads the repository (docs,
environment contract, vendored source) and records one of three modes:

- ``direct``: the dependency can be exercised through a local or test
  interface; the evidence names it;
- ``stub``: no usable interface is available; the scout supplies a stub and
  the documentation/source evidence it is based on;
- ``unavailable``: no reliable documentation or source exists. Guessing is
  forbidden, so this blocks planning.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .layout import ProjectLayout
from .model import ModelClient, ModelError, ModelMessage, project_model_name
from .model_output import json_objects
from .program_manifest import entries as manifest_entries
from .repo_tools import RepoActionError, execute_repo_action

MAX_SCOUT_STEPS = 10
MODES = {"direct", "stub", "unavailable"}


class DependencyError(RuntimeError):
    """An external dependency cannot be used deterministically."""


class DependencyBlocked(DependencyError):
    """A dependency has no reliable documentation/source; planning stops."""


DEPENDENCY_PROMPT = """You are Forgel's dependency scout. The specification
lists external dependencies; decide how each one can be used deterministically
by the code and its tests.

Inspect the repository first (environment contract, docs, vendored source,
tests) and cite what you find. Do not run commands and do not invent an
interface. You may inspect any repository of this project by passing its
``repo_id`` in an action.

A dependency that is another repository in this same project, a locally
installed executable, or a local/test service declared by the project's
environment contract is "direct": cite the repository/source/contract in
evidence. Check those before calling a dependency unavailable.

For every dependency choose one mode:
- "direct": it is available through a local or test interface in this
  environment; put the concrete command, service, package or fixture in
  evidence and interface.
- "stub": it is not available; provide a deterministic stub implementation and
  base it on documentation or source present in the repository. Put the exact
  source (path, URL or excerpt) in evidence and the complete stub code in
  "stub". A stub without evidence is invalid.
- "unavailable": no reliable documentation or source exists. Never guess the
  interface; this blocks the task.

Every listed dependency must appear in the answer. Return exactly one JSON
object:
{"dependencies": [
  {"name": "...", "mode": "direct" | "stub" | "unavailable",
   "interface": "how it is used", "docs": "source",
   "evidence": "what document/source proves the contract",
   "stub": "complete stub code or empty"}
]}
"""


def _listing(
    dependencies: Sequence[Mapping[str, Any]],
    repo_id: str,
    repos: Sequence[Mapping[str, Any]],
) -> str:
    lines = [f"Repository: {repo_id or '(sole)'}", "", "Project repositories:"]
    lines.extend(
        f"- {item.get('id')}: {item.get('role') or 'application'}"
        for item in repos
    )
    lines.extend(["", "Dependencies:"])
    for item in dependencies:
        lines.append(
            f"- {item.get('name')}: interface: "
            f"{item.get('interface') or '—'}; docs: "
            f"{item.get('docs') or '—'}"
        )
    return "\n".join(lines)


def _parse(
    raw: str,
    dependencies: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    objects = json_objects(raw)
    items: list[dict[str, Any]] = []
    for obj in objects:
        if isinstance(obj.get("dependencies"), list):
            items = [
                item for item in obj["dependencies"] if isinstance(item, dict)
            ]
            break
    if not items:
        # Some models return the dependency objects without the wrapper.
        items = [
            item
            for item in objects
            if str(item.get("name") or "").strip()
            and str(item.get("mode") or "").strip()
        ]
    if not items:
        raise DependencyError(
            "the dependency scout did not return a dependency list; "
            f"output: {raw[:600]}"
        )
    reported = {
        str(item.get("name") or "").strip(): item for item in items
    }
    result: list[dict[str, str]] = []
    unavailable: list[str] = []
    for dependency in dependencies:
        name = str(dependency.get("name") or "").strip()
        item = reported.get(name)
        if item is None:
            raise DependencyError(
                f"the dependency scout did not report {name!r}"
            )
        mode = str(item.get("mode") or "").strip().lower()
        if mode not in MODES:
            raise DependencyError(
                f"the dependency scout gave {name!r} an unknown mode "
                f"{mode!r}"
            )
        evidence = str(item.get("evidence") or "").strip()
        stub = str(item.get("stub") or "").strip()
        if mode in {"direct", "stub"} and not evidence:
            raise DependencyError(
                f"the dependency scout gave no evidence for {name!r}; "
                "an external contract cannot be guessed"
            )
        if mode == "stub" and not stub:
            raise DependencyError(
                f"the dependency scout gave no stub for {name!r}"
            )
        if mode == "unavailable":
            unavailable.append(name)
        result.append(
            {
                "name": name,
                "interface": str(
                    item.get("interface")
                    or dependency.get("interface")
                    or ""
                ).strip(),
                "docs": str(
                    item.get("docs") or dependency.get("docs") or ""
                ).strip(),
                "mode": mode,
                "evidence": evidence,
                "stub": stub,
            }
        )
    if unavailable:
        raise DependencyBlocked(
            "external dependencies have no reliable documentation or "
            "source and cannot be stubbed: " + ", ".join(unavailable)
        )
    return result


def investigate(
    layout: ProjectLayout,
    intent: Mapping[str, Any],
    spec: Mapping[str, Any],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> list[dict[str, str]]:
    """Read the repository and resolve each external dependency's mode."""

    dependencies = [
        item
        for item in (spec.get("external_dependencies") or [])
        if isinstance(item, dict)
        and str(item.get("name") or "").strip()
    ]
    if not dependencies:
        return []
    repo_id = str(spec.get("repo_id") or intent.get("repo_id") or "")
    repos = manifest_entries(layout)
    scout_retries = 0
    messages = [
        ModelMessage("system", DEPENDENCY_PROMPT),
        ModelMessage(
            "user",
            "Task: "
            f"{intent.get('title') or spec.get('title') or '—'}\n\n"
            f"Summary: {intent.get('summary') or '—'}\n\n"
            + _listing(dependencies, repo_id, repos)
            + "\n\nInspect the repository, then return the dependency JSON.",
        ),
    ]
    for _ in range(MAX_SCOUT_STEPS):
        try:
            raw = client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError as exc:
            raise DependencyError(
                f"the dependency scout failed: {exc}"
            ) from exc
        objects = json_objects(raw)
        actions = [
            item
            for item in objects
            if str(item.get("action", "")) in {"list_files", "read_file"}
        ]
        finals = [
            item
            for item in objects
            if str(item.get("action", ""))
            not in {"list_files", "read_file"}
        ]
        observations: list[str] = []
        for action in actions:
            args = dict(action.get("action_args") or {})
            for key in ("path", "repo_id"):
                if key in action and key not in args:
                    args[key] = action[key]
            try:
                observation = execute_repo_action(
                    layout,
                    repos,
                    {"action": str(action["action"]), **args},
                )
            except RepoActionError as exc:
                observation = f"error: {exc}"
            observations.append(observation)
        if observations:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observations:\n"
                    + "\n\n".join(item[:6000] for item in observations)
                    + "\n\nReturn the dependency JSON.",
                )
            )
            continue
        if finals:
            try:
                result = _parse(raw, dependencies)
            except DependencyBlocked:
                raise
            except DependencyError as exc:
                if scout_retries < 2:
                    messages.append(ModelMessage("assistant", raw.strip()))
                    messages.append(
                        ModelMessage(
                            "user",
                            "Return exactly one JSON object with every "
                            "dependency: {\"dependencies\": [{\"name\", "
                            "\"mode\", \"interface\", \"docs\", \"evidence\", "
                            "\"stub\"}]}. " + str(exc),
                        )
                    )
                    scout_retries += 1
                    continue
                raise
            log(
                f"[deps] {repo_id or 'main'}: "
                f"{len(dependencies)} dependency(ies) checked"
            )
            return result
        messages.append(ModelMessage("assistant", raw.strip()))
        messages.append(
            ModelMessage(
                "user",
                "Return exactly one JSON object with the dependencies "
                "list. Do not use prose or tool-call markup.",
            )
        )
    raise DependencyError("the dependency scout exceeded its step limit")
