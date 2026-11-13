"""Deterministic stage sequence for the M0 pipeline.

The orchestrator is a state machine, not a free-running agent loop. Each stage
has one successor; resumption starts from the last checkpoint.
"""

from __future__ import annotations

STAGES: tuple[str, ...] = (
    "intake",
    "jurisdiction",
    "recipe",
    "architecture",
    "repo_plan",
    "feature_plan",
    "spec",
    "spec_review",
    "dev",
    "review",
    "qa",
    "acceptance",
    "audit",
    "approval",
    "done",
)

_INDEX = {stage: index for index, stage in enumerate(STAGES)}


def validate_stage(stage: str) -> None:
    if stage not in _INDEX:
        raise ValueError(f"Unknown stage: {stage}")


def next_stage(stage: str) -> str:
    """Return the stage after ``stage``. ``done`` is terminal."""

    validate_stage(stage)
    index = _INDEX[stage]
    if index == len(STAGES) - 1:
        return stage
    return STAGES[index + 1]


def stages_from(stage: str) -> tuple[str, ...]:
    """Return ``stage`` and every stage after it."""

    validate_stage(stage)
    return STAGES[_INDEX[stage] :]
