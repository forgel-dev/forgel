"""Context budgeting and session handoff.

The runtime, not the model, owns the context window. A long task is split
into sessions: when the estimated prompt size approaches the budget, the run
writes durable state to a file and starts a new session from that state plus
the task. The model never has to guess token counts, warn about them or ask a
human: it simply continues from the handoff.

The estimate is deliberately conservative (about three characters per token)
and dependency-free. A real tokenizer belongs to the model plugin later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from .tokens import count_tokens

DEFAULT_WINDOW = 1_000_000
MAX_RESERVE = 8_192
COMPACT_AT = 0.7
KEEP_RECENT = 3
MAX_STATE_CHARS = 60_000
MAX_OBSERVATION_CHARS = 20_000


def estimate_tokens(text: str, model: str = "") -> int:
    return count_tokens(text, model)


def messages_tokens(messages: Sequence[Any], model: str = "") -> int:
    return sum(
        count_tokens(str(getattr(message, "content", message)), model) + 4
        for message in messages
    )


@dataclass(frozen=True)
class ContextBudget:
    """A window, an output reserve and the compaction threshold."""

    window: int = DEFAULT_WINDOW
    reserve: int = MAX_RESERVE
    compact_at: float = COMPACT_AT

    @property
    def usable(self) -> int:
        return max(2_048, self.window - self.reserve)

    @property
    def threshold(self) -> int:
        return int(self.usable * self.compact_at)

    def usage(self, messages: Sequence[Any], model: str = "") -> int:
        return messages_tokens(messages, model)

    def should_compact(
        self, messages: Sequence[Any], model: str = ""
    ) -> bool:
        return self.usage(messages, model) >= self.threshold


def budget_for(window: int) -> ContextBudget:
    """A budget with an output reserve proportional to the window."""

    reserve = min(MAX_RESERVE, max(1_024, window // 4))
    return ContextBudget(window=window, reserve=reserve)


@dataclass
class SessionState:
    """Durable state handed from one session to the next."""

    task_id: str
    title: str
    session: int
    requirements: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    status: str = "in progress"
    next_step: str = ""

    def to_markdown(self) -> str:
        def bullets(values: Sequence[str], empty: str = "none") -> str:
            return "\n".join(f"- {item}" for item in values) or f"- {empty}"

        command_lines = (
            "\n".join(
                f"- `{item.get('command')}` -> exit {item.get('exit_code')}"
                for item in self.commands
            )
            or "- none"
        )
        observation_lines = (
            "\n".join(
                f"- {item[:MAX_OBSERVATION_CHARS]}"
                for item in self.observations[-KEEP_RECENT:]
            )
            or "- none"
        )
        text = f"""# Session State: {self.title}

- Task: `{self.task_id}`
- Session: {self.session}
- Status: {self.status}

## Goal

Implement the task requirements in the repository, run the final test and
commit. Continue from this state; do not repeat finished work.

## Requirements

{bullets(self.requirements)}

## Acceptance Criteria

{bullets(self.acceptance)}

## Constraints

{bullets(self.constraints)}

## Assumptions

{bullets(self.assumptions)}

## Files Changed

{bullets(self.files_changed)}

## Actions

{bullets(self.actions)}

## Commands

{command_lines}

## Recent Observations

{observation_lines}

## Next Step

{self.next_step or 'Continue the task from the requirements and the current repository state.'}
"""
        if len(text) > MAX_STATE_CHARS:
            text = text[:MAX_STATE_CHARS] + "\n\n... [state truncated]\n"
        return text


def handoff_prompt(state: SessionState) -> str:
    """The user message that starts a new session."""

    return (
        "SESSION HANDOFF. A previous session of this task ran out of context. "
        "Continue from the durable state below; the repository on disk is the "
        "source of truth. Do not repeat work already reported as done.\n\n"
        + state.to_markdown()
        + "\n\nContinue with one JSON action."
    )
