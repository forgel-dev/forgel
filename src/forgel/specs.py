"""Formal task specifications and the release requirements gate.

The planner decomposes a milestone into task intents. A separate requirements
writer turns each intent into a formal specification document; a release gate
then judges the complete set against the original problem, the recorded user
decisions and each other. The specification is the artifact the coding agent,
QA and the independent reviewer work from; the task record is an index.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from . import requirements as requirements_doc
from .artifacts import write_text
from .context_window import CONTEXT_ACTION, ContextWindow, Item
from .instructions import instruction_context
from .layout import ProjectLayout
from .model_output import json_objects
from .model import (
    ModelClient,
    ModelError,
    ModelMessage,
    project_model_name,
)
from .program_manifest import entries as manifest_entries
from .repo_tools import RESEARCH_ACTIONS, RepoActionError, execute_repo_action

MAX_SPEC_STEPS = 50
MAX_SPEC_CHARS = 12_000
MAX_SPEC_RETRIES = 5
MAX_REVIEW_PAGES = 40
MAX_WORK_PACKAGE_ACCEPTANCE = 4
SPEC_KEYS = {
    "problem",
    "outcome",
    "scope",
    "non_goals",
    "requirements",
    "acceptance",
    "constraints",
    "external_dependencies",
}
SPEC_DIR = "docs/program/specs"
CANCEL_MARKER = "<!-- forgel:cancelled -->"
CANCEL_NOTE = (
    f"{CANCEL_MARKER}\n"
    "\n"
    "> **Cancelled.** This task was cancelled. The runtime does not accept "
    "this requirements document for work.\n"
)


class SpecError(RuntimeError):
    """The requirements writer could not produce a usable specification."""


@dataclass
class ReleaseReview:
    sufficient: bool
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_markdown(self) -> str:
        if self.sufficient:
            return "The release review found the set sufficient."
        lines = ["The release review found defects in the set:"]
        lines.extend(
            f"- task {item.get('task')} [{item.get('kind')}]: "
            f"{item.get('issue')}"
            for item in self.findings
        )
        return "\n".join(lines)


SPEC_SYSTEM_PROMPT = """You are Forgel's requirements writer for exactly one
task. The planner has split a milestone into tasks; your job is the formal
specification for one of them.

You may inspect the repository before writing:
{"action": "list_files", "path": ".", "repo_id": "main"}
{"action": "read_file", "path": "relative/path", "repo_id": "main"}
Paths are relative to the repository and may not leave it. Read the code you
depend on instead of assuming it exists; stop once you know enough.

Return exactly one JSON object:
{
  "problem": "what problem this task solves",
  "outcome": "what is true when the task is done",
  "product_intent": "the product intent this task serves, when stated",
  "user_experience": "how the user experiences this task's result, when stated",
  "scope": ["in scope"],
  "non_goals": ["explicitly out of scope"],
  "requirements": ["explicit, testable requirement"],
  "acceptance": ["observable acceptance criterion"],
  "constraints": ["constraint"],
  "assumptions": ["what you assumed where the intent was silent"],
  "external_dependencies": [
    {"name": "service, tool or format",
     "interface": "how the task uses it",
     "docs": "path, URL or excerpt source, or empty"}
  ],
  "risks": ["what could make this task fail or miss the goal"],
  "goals": ["outcome this task must achieve"],
  "user_decisions": [
    {"decision": "binding product decision", "source": "where it was recorded"}
  ],
  "user_stories": ["as a ... I want ... so that ..."],
  "open_questions": ["only a truly undecidable choice, never a way to avoid deciding"],
  "related_documents": ["path"],
  "revision_history": ["version and what changed"]
}

Rules:
- Requirements must be explicit and testable; acceptance must say how the
  result is judged. Do not add features beyond the intent, and do not
  prescribe an implementation file list: state the required behavior, the
  developer chooses the files.
- Requirements, acceptance, constraints, goals, user stories, risks and open
  questions describe observable product behavior and outcomes only. Never put
  a command (shell, git, package manager), a file path, code, an identifier, a
  tool or provider name, an environment variable, an interface, a contract, an
  endpoint, a request or response format, a schema, a commit/PR/worktree step
  or any other implementation detail into them. Runtime mechanics (git,
  commit, worktree, done report) are never requirements. This is a
  requirements document: the permission to document a stable interface in
  user documentation does not apply. If the intent or the respec issue names
  a command, a file or a runtime step, restate the behavior it must produce.
- Documentation is text and is verified by review. Never require or add a
  test, guard, assertion or automated check that reads a documentation file.
- Acceptance criteria describe observable outcomes. The repository test gate
  and the reviewer judge them; the specification does not carry a test
  command or an automated check.
- Group every requirement and acceptance criterion into cohesive work
  packages. Each package is one related behavior set; every index appears in
  exactly one requirement or acceptance list; a package covers at most four
  acceptance criteria. Do not define a package by file name, path or
  implementation step.
- A respec issue is a binding decision: the rewritten requirements and
  acceptance must remove the option the issue rejected and must not leave a
  product choice open when the acceptance depends on it. Requirements and
  acceptance must be mutually consistent; a requirement that permits an
  option the acceptance forbids is invalid. Decide the remaining details from
  the issue, the task intent and the recorded decisions and write the
  requirement; never use an open question to avoid the decision, and never
  leave the specification waiting for an answer.
- Do not default to open questions. Decide every reversible detail yourself,
  record it as an assumption, and write the requirement. An open question is
  reserved for a truly undecidable choice and never stops the work.
- Give every acceptance criterion a check. Use a command when the criterion
  can be verified by one; use review only for a subjective criterion. Never
  use a vacuous check.
- The task is one repository change that a coding agent can finish, test and
  commit on its own.
- Product decisions recorded in the project's user-decision log are binding.
  Include the decisions relevant to this task under "user_decisions" with
  their IDs and sources; do not re-open them. If the task contradicts a
  recorded decision, say so in risks and open_questions.
- If the intent is ambiguous or cannot achieve the milestone problem, record
  the gap in risks and keep the scope honest; do not invent a solution.
- If the task depends on an external interface (a tool, a service, a data
  format, a protocol), record the contract the implementation needs, derived
  from its authoritative source, and add a command check that exercises the
  real interface when it is available; a hand-written stub is not proof of
  the contract. A task that needs a browser, a mobile simulator or emulator,
  a live third-party service, a message broker, object storage or another
  tool without a standard test harness must include at least one command
  check that exercises that real interface; a fake engine, a mock or a stub
  is not proof. A database or cache that the project's unit-test framework
  already handles needs the normal test command, not a separate integration
  environment.
- A specification is rewritten only for the concrete defect the planner
  reported; keep unrelated scope stable and never treat a preference, a
  simpler path or a wording change as a defect.
- List every external dependency the task touches — a service, tool, binary,
  API, schema or data format from outside this project and its repositories.
  A sibling project repository, the standard library or a package already
  provided by the project environment is not external; use it directly. Give
  the documentation source; leave it empty when none is known. Do not invent
  the interface; the dependency scout investigates it.
- Follow the project and repository instructions in the prompt. Repository
  rules are more specific and take precedence on conflict. Write the
  specification in the artifact language they require.
- Return JSON only; no tool-call markup, XML or prose.
"""


RELEASE_REVIEW_PROMPT = """You are Forgel's release requirements gate. The
planner has split one milestone into tasks, and writers have produced every
task specification. You review the complete set before coding starts.

This is a safety gate, not an improvement pass. Report only a concrete defect
that makes the set unsound to start. Do not report a preference, a wording or
style change, a simpler alternative, missing polish, or an opportunity to make
an already valid plan better.

Follow the project and repository instructions in the prompt. Repository rules
are more specific and take precedence on conflict. Write findings in the
artifact language they require.

Check the set as a whole:
1. Cross-task contradiction: requirements, acceptance criteria, constraints,
   non-goals or user decisions of different tasks that cannot all hold; two
   tasks owning the same behavior in conflicting ways.
2. Intent alignment: every outcome in the milestone goal, product intent, user
   experience and recorded decisions is covered; no task conflicts with a
   recorded decision or adds a product choice the owner did not ask for.
3. Completeness and integrity: a required behavior no task delivers; an
   assumption or promise no task delivers; a gap between tasks; a task that
   can pass while the goal remains unmet; duplicate or overlapping tasks; an
   impossible task order or repository split.
4. A specification's internal defect: a logical contradiction, an unachievable
   requirement, a security or architectural problem.

Every finding must name the task index (use -1 for a set-level finding), the
kind, and the concrete conflicting statements or missing outcome. Do not
rewrite specifications. Do not report a defect you cannot point to in the
provided text.

The context is paged. To read any page, answer only with
{"action": "context_page", "key": "<item key>", "page": <number>}; the runtime
returns that page and asks again.

Return exactly one JSON object:
{"sufficient": true | false,
 "findings": [{"task": 0,
               "kind": "contradiction | coverage | completeness | defect",
               "issue": "concrete conflicting statements or missing outcome"}]}

Use sufficient=true only when no finding above exists. Return JSON only.
"""


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _package_indices(
    value: Any, limit: int, label: str
) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SpecError(f"a work package {label} list must be a list")
    result: list[int] = []
    for item in value:
        if isinstance(item, bool):
            raise SpecError(
                f"a work package {label} index must be an integer"
            )
        if isinstance(item, str):
            text = item.strip()
            if re.fullmatch(r"[0-9]+", text):
                item = int(text)
        elif isinstance(item, float) and item.is_integer():
            item = int(item)
        if not isinstance(item, int):
            raise SpecError(
                f"a work package {label} index must be an integer"
            )
        if item < 0 or item >= limit:
            raise SpecError(
                f"work package {label} index {item} is out of range"
            )
        if item in result:
            raise SpecError(
                f"work package {label} index {item} is repeated"
            )
        result.append(item)
    return result


def _normalize_work_packages(
    raw: Any,
    requirements: Sequence[str],
    acceptance: Sequence[str],
) -> list[dict[str, Any]]:
    items = raw if isinstance(raw, list) and raw else [
        {
            "title": "All requirements",
            "requirements": list(range(len(requirements))),
            "acceptance": list(range(len(acceptance))),
        }
    ]
    packages: list[dict[str, Any]] = []
    seen_requirements: set[int] = set()
    seen_acceptance: set[int] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise SpecError(f"work package {index} must be an object")
        title = str(item.get("title") or "").strip()
        if not title:
            raise SpecError(f"work package {index} has no title")
        package_requirements = _package_indices(
            item.get("requirements"), len(requirements), "requirement"
        )
        package_acceptance = _package_indices(
            item.get("acceptance"), len(acceptance), "acceptance"
        )
        if not package_requirements and not package_acceptance:
            raise SpecError(f"work package {title!r} is empty")
        if len(package_acceptance) > MAX_WORK_PACKAGE_ACCEPTANCE:
            raise SpecError(
                f"work package {title!r} covers "
                f"{len(package_acceptance)} acceptance criteria; the limit "
                f"is {MAX_WORK_PACKAGE_ACCEPTANCE}; split it into cohesive "
                "packages"
            )
        for position in package_requirements:
            if position in seen_requirements:
                raise SpecError(
                    f"requirement {position} appears in more than one "
                    "work package"
                )
            seen_requirements.add(position)
        for position in package_acceptance:
            if position in seen_acceptance:
                raise SpecError(
                    f"acceptance criterion {position} appears in more than "
                    "one work package"
                )
            seen_acceptance.add(position)
        packages.append(
            {
                "title": title,
                "requirements": package_requirements,
                "acceptance": package_acceptance,
            }
        )
    missing_requirements = [
        position
        for position in range(len(requirements))
        if position not in seen_requirements
    ]
    missing_acceptance = [
        position
        for position in range(len(acceptance))
        if position not in seen_acceptance
    ]
    if missing_requirements:
        raise SpecError(
            "work packages omit requirements "
            + ", ".join(str(item) for item in missing_requirements)
        )
    if missing_acceptance:
        raise SpecError(
            "work packages omit acceptance criteria "
            + ", ".join(str(item) for item in missing_acceptance)
        )
    return packages


def _normalize_spec(
    data: Mapping[str, Any],
    intent: Mapping[str, Any],
) -> dict[str, Any]:
    requirements = _strings(data.get("requirements"))
    acceptance = _strings(data.get("acceptance"))
    if not requirements:
        raise SpecError("the specification has no requirements")
    if not acceptance:
        raise SpecError("the specification has no acceptance criteria")
    work_packages = _normalize_work_packages(
        data.get("work_packages"), requirements, acceptance
    )
    external_dependencies = [
        {
            "name": str(item.get("name") or "").strip(),
            "interface": str(item.get("interface") or "").strip(),
            "docs": str(item.get("docs") or "").strip(),
            "mode": str(item.get("mode") or "").strip(),
            "evidence": str(item.get("evidence") or "").strip(),
            "stub": str(item.get("stub") or "").strip(),
        }
        for item in (data.get("external_dependencies") or [])
        if isinstance(item, dict)
        and str(item.get("name") or "").strip()
    ]
    return {
        "title": str(intent.get("title") or "").strip(),
        "summary": str(intent.get("summary") or "").strip(),
        "repo_id": str(intent.get("repo_id") or "").strip(),
        "problem": str(data.get("problem") or "").strip(),
        "outcome": str(data.get("outcome") or "").strip(),
        "product_intent": str(
            data.get("product_intent") or ""
        ).strip(),
        "user_experience": str(
            data.get("user_experience") or ""
        ).strip(),
        "scope": _strings(data.get("scope")),
        "non_goals": _strings(data.get("non_goals")),
        "requirements": requirements,
        "acceptance": acceptance,
        "work_packages": work_packages,
        "constraints": _strings(data.get("constraints")),
        "assumptions": _strings(data.get("assumptions")),
        "external_dependencies": external_dependencies,
        "risks": _strings(data.get("risks")),
        "goals": _strings(data.get("goals"))
        or ([str(data.get("outcome") or "").strip()]
            if str(data.get("outcome") or "").strip()
            else []),
        "user_decisions": [
            {
                "decision": str(item.get("decision") or "").strip(),
                "source": str(item.get("source") or "").strip(),
            }
            for item in (data.get("user_decisions") or [])
            if isinstance(item, dict)
            and str(item.get("decision") or "").strip()
        ],
        "user_stories": _strings(data.get("user_stories")),
        "open_questions": _strings(data.get("open_questions")),
        "related_documents": _strings(data.get("related_documents")),
        "revision_history": _strings(data.get("revision_history")),
    }


def _context(
    layout: ProjectLayout, repo_id: str
) -> str:
    try:
        tree = execute_repo_action(
            layout,
            manifest_entries(layout),
            {"action": "list_files", "path": ".", "repo_id": repo_id},
        )
    except RepoActionError as exc:
        tree = f"(file tree unavailable: {exc})"
    return tree[:MAX_SPEC_CHARS]


def _looks_like_tool_markup(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "<｜｜dsml｜｜",
            "<|",
            "<tool_call",
            "<tool_result",
            "<function_call",
            "<parameter",
            "</invoke>",
            "<system_warning",
        )
    )


IMPLEMENTATION_PATTERNS = (
    re.compile(r"\bgit\b", re.IGNORECASE),
    re.compile(r"\b(?:curl|wget)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:pip|npm|yarn|pnpm|docker|ssh|scp|rsync)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bpython\s+-m\b", re.IGNORECASE),
    re.compile(r"\b(?:sh|bash|zsh)\s+-c\b", re.IGNORECASE),
    re.compile(r"```"),
    re.compile(r"(?:https?://|git@)\S+", re.IGNORECASE),
    re.compile(
        r"\b[\w.-]+(?:/[\w.-]+)+\.(?:md|py|sh|json|ya?ml|toml|txt|mjs|js|ts|cfg|ini)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b[\w-]+\.(?:md|py|sh|json|ya?ml|toml|txt|mjs|js|ts|cfg|ini)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:commit|commits|committed|worktree|done report)\b",
        re.IGNORECASE,
    ),
)

IMPLEMENTATION_FIELDS = (
    "problem",
    "outcome",
    "requirements",
    "acceptance",
    "constraints",
    "goals",
    "user_stories",
    "scope",
    "non_goals",
    "risks",
    "open_questions",
    "assumptions",
)


def implementation_problems(spec: Mapping[str, Any]) -> list[str]:
    """Functional text must not carry commands, files, code or runtime steps."""

    problems: list[str] = []
    for field in IMPLEMENTATION_FIELDS:
        value = spec.get(field)
        values = [value] if isinstance(value, str) else value or []
        for item in values:
            text = str(item).strip()
            if not text:
                continue
            for pattern in IMPLEMENTATION_PATTERNS:
                match = pattern.search(text)
                if match:
                    problems.append(
                        f"{field}: implementation detail "
                        f"{match.group(0)!r} in {text[:160]!r}"
                    )
                    break
    return problems


DOCUMENTATION_WORDS = re.compile(
    r"\b(?:readme|documentation|documents?|docs?|manual|guide|changelog)\b",
    re.IGNORECASE,
)
TEST_WORDS = re.compile(
    r"\b(?:tests?|guard|assertions?|assert)\b", re.IGNORECASE
)


def documentation_task(
    intent: Mapping[str, Any], spec: Mapping[str, Any]
) -> bool:
    """True when the task is a documentation change."""

    text = " ".join(
        str(item or "")
        for item in (
            intent.get("title"),
            intent.get("summary"),
            spec.get("problem"),
            spec.get("outcome"),
        )
    )
    return bool(DOCUMENTATION_WORDS.search(text))


def documentation_problems(
    intent: Mapping[str, Any], spec: Mapping[str, Any]
) -> list[str]:
    """Documentation is text: it is reviewed, never tested."""

    if not documentation_task(intent, spec):
        return []
    problems: list[str] = []
    for field in (
        "requirements",
        "acceptance",
        "constraints",
        "goals",
        "user_stories",
    ):
        value = spec.get(field)
        values = [value] if isinstance(value, str) else value or []
        for item in values:
            text = str(item).strip()
            if (
                text
                and DOCUMENTATION_WORDS.search(text)
                and TEST_WORDS.search(text)
            ):
                problems.append(
                    f"{field}: documentation is verified by review, not "
                    f"by a test: {text[:120]}"
                )
    return problems


def _looks_like_spec(data: Mapping[str, Any]) -> bool:
    """A candidate final answer must carry spec fields, not tool results."""

    if str(data.get("kind") or "").strip().lower() == "spec":
        return True
    return bool(SPEC_KEYS & set(data))


def _diagnostics(
    intent: Mapping[str, Any],
    attempts: int,
    research_paths: Sequence[str],
    retries: int,
    markup_retries: int,
    raw: str,
    last_observation: str,
    reason: str,
) -> str:
    title = str(intent.get("title") or "the task")
    research = ", ".join(research_paths[-8:]) or "none"
    observation = " ".join(
        (last_observation or "").strip().split()
    )[:400]
    return (
        f"{reason}; task: {title}; model calls: {attempts}; "
        f"research: {research}; answer retries: {retries}; "
        f"markup retries: {markup_retries}; "
        f"last observation: {observation or '—'}; "
        f"last model output: {raw[:1200] or '(empty)'}"
    )


def write_task_spec(
    settings: Any,
    layout: ProjectLayout,
    goal: str,
    notes: str,
    intent: Mapping[str, Any],
    client: ModelClient,
    log: Callable[[str], None] = print,
    review_issue: str = "",
    requested_changes: str = "",
    current_spec: str = "",
) -> dict[str, Any]:
    """Turn one planner intent into a formal, structured specification."""

    repo_id = str(intent.get("repo_id") or "").strip()
    decisions_path = layout.artifact("docs/program/decisions.md")
    try:
        decisions_text = decisions_path.read_text(encoding="utf-8")
    except OSError:
        decisions_text = "(no user-decision log yet)"
    repo_lines = "\n".join(
        f"- {item['id']}: {item.get('role') or 'application'}"
        for item in manifest_entries(layout)
    ) or "- (sole)"
    instructions = instruction_context(
        layout, [repo_id] if repo_id else None
    )
    messages = [
        ModelMessage("system", SPEC_SYSTEM_PROMPT),
        ModelMessage(
            "user",
            "Milestone goal:\n"
            f"{goal}\n\nPlan notes:\n{notes or '—'}\n\n"
            f"Task intent:\n{json.dumps(dict(intent), ensure_ascii=False)}\n\n"
            f"User decision log:\n{decisions_text}\n\n"
            f"Project repositories:\n{repo_lines}\n\n"
            + (
                f"Project and repository instructions:\n{instructions}\n\n"
                if instructions
                else ""
            )
            + f"Repository file tree:\n{_context(layout, repo_id)}\n\n"
            + (
                "The current specification is:\n"
                f"{current_spec}\n\n"
                if current_spec
                else ""
            )
            + (
                "The previous version was rejected for this concrete "
                f"defect:\n{review_issue}\n\n"
                if review_issue
                else ""
            )
            + (
                "The owner requires these changes to the specification:\n"
                f"{requested_changes}\n\n"
                "Apply only these changes. Keep every other requirement, "
                "acceptance criterion, constraint, check and test command "
                "exactly as it is: do not reword, reformulate, remove or add "
                "anything else, and do not change the task's nature or "
                "scope.\n\n"
                if requested_changes
                else ""
            )
            + "Write the formal specification now.",
        ),
    ]
    model = project_model_name(layout.control)
    parsed: dict[str, Any] | None = None
    retries = 0
    research_steps = 0
    budget_notice = False
    attempts = 0
    markup_retries = 0
    research_paths: list[str] = []
    last_observation = ""
    for _ in range(MAX_SPEC_STEPS + MAX_SPEC_RETRIES + 6):
        attempts += 1
        try:
            raw = client.complete(messages, model=model)
        except ModelError as exc:
            raise SpecError(
                f"the requirements writer failed on model call {attempts}: "
                f"{exc}; research: "
                f"{', '.join(research_paths[-8:]) or 'none'}"
            ) from exc
        objects = json_objects(raw)
        actions = [
            item
            for item in objects
            if str(item.get("action", "")) in RESEARCH_ACTIONS
        ]
        finals = [
            item
            for item in objects
            if str(item.get("action", "")) not in RESEARCH_ACTIONS
            and _looks_like_spec(item)
        ]
        observations: list[str] = []
        for data in actions:
            if research_steps >= MAX_SPEC_STEPS:
                break
            args = dict(data.get("action_args") or {})
            for key in ("path", "repo_id"):
                if key in data and key not in args:
                    args[key] = data[key]
            try:
                observation = execute_repo_action(
                    layout,
                    manifest_entries(layout),
                    {"action": str(data["action"]), **args},
                )
            except RepoActionError as exc:
                observation = f"error: {exc}"
            observations.append(observation)
            research_steps += 1
            research_paths.append(
                f"{data['action']}:{args.get('path') or ''}"
            )
        if observations:
            last_observation = observations[-1]
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Observations:\n"
                    + "\n\n".join(
                        item[:MAX_SPEC_CHARS] for item in observations
                    )
                    + "\n\nReturn another action or the final spec JSON.",
                )
            )
        unknown = [
            item
            for item in objects
            if str(item.get("action") or "").strip()
            and str(item.get("action")) not in RESEARCH_ACTIONS
            and not _looks_like_spec(item)
        ]
        if unknown and not finals:
            if markup_retries < MAX_SPEC_RETRIES:
                names = ", ".join(
                    sorted(
                        {
                            str(item.get("action") or "")
                            for item in unknown
                        }
                    )
                )
                messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        f"Unknown action(s): {names}. The only research "
                        "actions are list_files and read_file. Return one "
                        "of them or the final specification JSON.",
                    )
                )
                markup_retries += 1
                continue
        if finals:
            try:
                parsed = _normalize_spec(finals[-1], intent)
                implementation = implementation_problems(parsed)
                if implementation:
                    raise SpecError("; ".join(implementation[:5]))
                documentation = documentation_problems(intent, parsed)
                if documentation:
                    raise SpecError("; ".join(documentation[:5]))
                break
            except SpecError as exc:
                if retries >= MAX_SPEC_RETRIES:
                    keys = sorted(finals[-1].keys())
                    raise SpecError(
                        _diagnostics(
                            intent,
                            attempts,
                            research_paths,
                            retries,
                            markup_retries,
                            raw,
                            last_observation,
                            f"{exc}; model keys: {keys}",
                        )
                    ) from exc
                if not observations:
                    messages.append(ModelMessage("assistant", raw.strip()))
                messages.append(
                    ModelMessage(
                        "user",
                        f"The specification is invalid: {exc}. The document "
                        "describes functional requirements only: remove every "
                        "command, file path, code, tool or provider name, "
                        "environment variable, commit/git/worktree/done-report "
                        "step and other implementation detail from "
                        "requirements, acceptance, constraints, goals, user "
                        "stories, risks, open questions and assumptions. "
                        "A documentation task is text and is verified by "
                        "review; never require a test or guard that reads a "
                        "documentation file. Group every requirement and "
                        "acceptance criterion into cohesive work packages; "
                        "every index appears once and a package covers at "
                        "most four acceptance criteria. Work package indices "
                        "must be JSON integers, for example [0, 1]; never "
                        "strings, decimals or booleans. A respec issue is "
                        "binding: remove the option it rejected and keep "
                        "requirements and acceptance consistent. Return "
                        "a complete JSON specification without a test "
                        "command or an automated check.",
                    )
                )
                retries += 1
                continue
        if _looks_like_tool_markup(raw) and markup_retries < MAX_SPEC_RETRIES:
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return exactly one JSON specification object, not "
                    "tool-call markup, tool results or XML. Do not emit "
                    "<｜｜DSML｜｜>, <tool_call>, <tool_result>, "
                    "<invoke>/<parameter> or provider-specific calls.",
                )
            )
            markup_retries += 1
            continue
        if not actions:
            if retries >= MAX_SPEC_RETRIES:
                raise SpecError(
                    _diagnostics(
                        intent,
                        attempts,
                        research_paths,
                        retries,
                        markup_retries,
                        raw,
                        last_observation,
                        "the requirements writer did not return a "
                        "specification",
                    )
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Return a complete JSON specification with explicit "
                    "requirements and acceptance criteria.",
                )
            )
            retries += 1
            continue
        if research_steps >= MAX_SPEC_STEPS and not observations:
            if budget_notice:
                raise SpecError(
                    _diagnostics(
                        intent,
                        attempts,
                        research_paths,
                        retries,
                        markup_retries,
                        raw,
                        last_observation,
                        "the requirements writer exceeded the research "
                        "step limit",
                    )
                )
            messages.append(ModelMessage("assistant", raw.strip()))
            messages.append(
                ModelMessage(
                    "user",
                    "Research budget exhausted. Return the final spec JSON "
                    "now; do not read or list more files.",
                )
            )
            budget_notice = True
            continue
    if parsed is None:
        raise SpecError(
            _diagnostics(
                intent,
                attempts,
                research_paths,
                retries,
                markup_retries,
                raw,
                last_observation,
                "the requirements writer did not return a spec",
            )
        )
    return parsed


def _review_spec_text(spec: Mapping[str, Any]) -> str:
    """Every review-relevant field of one specification."""

    def values(key: str) -> list[str]:
        raw = spec.get(key) or []
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        return [
            str(item).strip()
            for item in raw
            if str(item).strip()
        ]

    def bullets(key: str) -> str:
        items = values(key)
        return "\n".join(f"- {item}" for item in items) or "- none"

    def dependencies() -> str:
        items = []
        for item in spec.get("external_dependencies") or []:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            items.append(
                f"- {name}: interface={item.get('interface') or '—'}; "
                f"docs={item.get('docs') or '—'}; "
                f"mode={item.get('mode') or '—'}; "
                f"evidence={item.get('evidence') or '—'}; "
                f"stub={item.get('stub') or '—'}"
            )
        return "\n".join(items) or "- none"

    def decisions() -> str:
        items = []
        for item in spec.get("user_decisions") or []:
            if not isinstance(item, Mapping):
                continue
            decision = str(item.get("decision") or "").strip()
            if not decision:
                continue
            items.append(
                f"- {decision} "
                f"(source: {item.get('source') or '—'})"
            )
        return "\n".join(items) or "- none"

    def packages() -> str:
        items = []
        for item in spec.get("work_packages") or []:
            if not isinstance(item, Mapping):
                continue
            items.append(
                f"- {item.get('title') or '—'}: "
                f"requirements={item.get('requirements') or []}; "
                f"acceptance={item.get('acceptance') or []}"
            )
        return "\n".join(items) or "- none"

    return "\n".join(
        [
            f"Title: {spec.get('title') or '—'}",
            f"Repository: {spec.get('repo_id') or '(sole)'}",
            f"Summary: {spec.get('summary') or '—'}",
            f"Problem: {spec.get('problem') or '—'}",
            f"Outcome: {spec.get('outcome') or '—'}",
            f"Product intent: {spec.get('product_intent') or '—'}",
            f"User experience: {spec.get('user_experience') or '—'}",
            "Scope:\n" + bullets("scope"),
            "Non-goals:\n" + bullets("non_goals"),
            "Requirements:\n" + bullets("requirements"),
            "Acceptance:\n" + bullets("acceptance"),
            "Constraints:\n" + bullets("constraints"),
            "Assumptions:\n" + bullets("assumptions"),
            "Goals:\n" + bullets("goals"),
            "User decisions:\n" + decisions(),
            "User stories:\n" + bullets("user_stories"),
            "Open questions:\n" + bullets("open_questions"),
            "Work packages:\n" + packages(),
            "External dependencies:\n" + dependencies(),
            "Risks:\n" + bullets("risks"),
            "Related documents:\n" + bullets("related_documents"),
            "Revision history:\n" + bullets("revision_history"),
        ]
    )


def review_release(
    layout: ProjectLayout,
    goal: str,
    notes: str,
    specs: Sequence[Mapping[str, Any]],
    client: ModelClient,
    log: Callable[[str], None] = print,
) -> ReleaseReview:
    """Judge the complete set of task specifications before coding."""

    items = [
        Item("goal", "the milestone goal", goal or "—"),
        Item("notes", "the plan notes", notes or "—"),
    ]
    decisions_path = layout.artifact("docs/program/decisions.md")
    try:
        decisions_text = decisions_path.read_text(encoding="utf-8")
    except OSError:
        decisions_text = "(no user-decision log yet)"
    items.append(
        Item("decisions", "recorded user decisions", decisions_text)
    )
    instructions = instruction_context(layout)
    if instructions:
        items.append(
            Item(
                "instructions",
                "project and repository instructions",
                instructions,
            )
        )
    repo_ids = sorted(
        {
            str(spec.get("repo_id") or "").strip()
            for spec in specs
            if str(spec.get("repo_id") or "").strip()
        }
    )
    for repo_id in repo_ids:
        items.append(
            Item(
                f"repository:{repo_id}",
                f"repository file tree: {repo_id}",
                _context(layout, repo_id),
            )
        )
    for index, spec in enumerate(specs):
        items.append(
            Item(
                f"spec:{index}",
                f"task {index}: {spec.get('title') or '—'}",
                _review_spec_text(spec),
            )
        )
    window = ContextWindow(items)
    messages = [
        ModelMessage("system", RELEASE_REVIEW_PROMPT),
        ModelMessage(
            "user",
            f"Milestone goal:\n{goal or '—'}\n\n"
            f"Plan notes:\n{notes or '—'}\n\n"
            + window.render()
            + "\n\nReturn the release review JSON now, or request a "
            "context page with " + CONTEXT_ACTION + ".",
        ),
    ]
    data: Any = None
    page_index: int | None = None
    for _ in range(MAX_REVIEW_PAGES):
        try:
            raw = client.complete(
                messages, model=project_model_name(layout.control)
            )
        except ModelError as exc:
            raise SpecError(f"the release review failed: {exc}") from exc
        objects = json_objects(raw)
        parsed = objects[-1] if objects else None
        if (
            isinstance(parsed, dict)
            and str(parsed.get("action") or "") == "context_page"
        ):
            key = str(parsed.get("key") or "").strip()
            try:
                page = int(parsed.get("page") or 1)
            except (TypeError, ValueError):
                page = 0
            try:
                text = window.read(key, page)
            except (KeyError, ValueError) as exc:
                text = f"cannot read that context: {exc}"
            messages.append(ModelMessage("assistant", raw))
            if page_index is not None:
                messages[page_index] = ModelMessage(
                    "user",
                    "[the previous context page was released; request it "
                    "again if you still need it]",
                )
            messages.append(
                ModelMessage(
                    "user",
                    text + "\n\nReturn the release review JSON now.",
                )
            )
            page_index = len(messages) - 1
            log(f"[review] context {key} page {page}")
            continue
        data = parsed
        break
    else:
        raise SpecError(
            "the release review kept requesting context without a verdict"
        )
    if not isinstance(data, dict) or not isinstance(
        data.get("sufficient"), bool
    ):
        keys = (
            [sorted(item.keys()) for item in objects if isinstance(item, dict)]
            if "objects" in locals()
            else []
        )
        raise SpecError(
            "the release review did not return a verdict; "
            f"model objects: {keys}; output: {str(raw)[:600]}"
        )
    findings = []
    for item in data.get("findings") or []:
        if not isinstance(item, dict):
            continue
        try:
            task = int(item.get("task", -1))
        except (TypeError, ValueError):
            task = -1
        issue = str(item.get("issue") or "").strip()
        if not issue:
            continue
        findings.append(
            {
                "task": task,
                "kind": str(item.get("kind") or "defect").strip()
                or "defect",
                "issue": issue,
            }
        )
    return ReleaseReview(bool(data["sufficient"]), findings)


def render_spec(
    spec: Mapping[str, Any],
    task_id: str,
    plan_id: str,
    repo_id: str,
) -> str:
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    problem = str(spec.get("problem") or "").strip()
    outcome = str(spec.get("outcome") or "").strip()
    overview = problem
    if outcome:
        overview += ("\n\n" if overview else "") + f"**Outcome:** {outcome}"
    values = {
        "kind": "Task Spec",
        "title": spec.get("title") or "",
        "project": "—",
        "task": f"`{task_id}`",
        "plan": f"`{plan_id}`",
        "repository": f"`{repo_id or '(sole)'}`",
        "status": "Specification",
        "version": "1.0.0",
        "created": created,
        "source": f"Plan `{plan_id}`",
        "author": "Forgel requirements writer",
        "overview": overview or "—",
        "product_intent": spec.get("product_intent") or "—",
        "user_experience": spec.get("user_experience") or "—",
        "goals": requirements_doc.bullets(spec.get("goals") or []),
        "non_goals": requirements_doc.bullets(spec.get("non_goals") or []),
        "user_decisions": requirements_doc.decisions_table(
            spec.get("user_decisions") or []
        ),
        "functional_requirements": requirements_doc.numbered(
            "FR", spec.get("requirements") or []
        ),
        "user_stories": requirements_doc.bullets(
            spec.get("user_stories") or []
        ),
        "acceptance": requirements_doc.numbered(
            "AC", spec.get("acceptance") or []
        ),
        "work_packages": requirements_doc.work_packages_text(
            spec.get("work_packages") or [],
            spec.get("requirements") or [],
            spec.get("acceptance") or [],
        ),
        "scope": requirements_doc.bullets(
            list(spec.get("scope") or [])
            + list(spec.get("non_goals") or [])
        ),
        "risks": requirements_doc.bullets(spec.get("risks") or []),
        "open_questions": requirements_doc.bullets(
            spec.get("open_questions") or [], "None."
        ),
        "assumptions": requirements_doc.bullets(
            spec.get("assumptions") or []
        ),
        "related_documents": requirements_doc.bullets(
            spec.get("related_documents")
            or ["`docs/program/decisions.md`"]
        ),
        "revision_history": requirements_doc.bullets(
            spec.get("revision_history")
            or ["1.0.0 — Initial specification."]
        ),
    }
    return requirements_doc.render(values)


def spec_path(task_id: str) -> str:
    return f"{SPEC_DIR}/{task_id}.md"


def document_path(task: Mapping[str, Any]) -> str:
    """The requirements document of a task: its own spec, or the default."""

    return str(task.get("spec") or spec_path(str(task["id"])))


def cancelled(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> bool:
    """True when the requirements document is marked cancelled."""

    try:
        text = layout.artifact(document_path(task)).read_text(
            encoding="utf-8"
        )
    except OSError:
        return False
    return text.lstrip().startswith(CANCEL_MARKER)


def mark_cancelled(
    layout: ProjectLayout, task: Mapping[str, Any]
) -> bool:
    """Put the cancellation note at the top of the requirements document.

    Returns False when the task has no requirements document yet.
    """

    path = layout.artifact(document_path(task))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if text.lstrip().startswith(CANCEL_MARKER):
        return True
    write_text(path, CANCEL_NOTE + "\n" + text)
    return True
