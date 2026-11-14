"""Model-family profiles.

Defaults that belong to one model family live here, not in the core: the
default model, context window, tokenizer encoding, peak-hour schedule and the
label used in messages. The core asks for a profile and stays neutral.

DeepSeek is the first profile and the current default. A future model plugin
can expose the same fields from its manifest; the interface is deliberately
small and declarative.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    id: str
    display: str
    default_model: str
    models: tuple[str, ...]
    context_window: int
    tokenizer_encoding: str
    peak_windows: str
    peak_policy: str
    notes: str = ""

    def matches(self, model: str) -> bool:
        name = model.strip().lower()
        if not name:
            return True
        return any(
            name == item or name.startswith(f"{item}-")
            for item in self.models
        )


DEEPSEEK = ModelProfile(
    id="deepseek",
    display="DeepSeek",
    default_model="deepseek-flash",
    models=("deepseek",),
    context_window=1_000_000,
    tokenizer_encoding="cl100k_base",
    # Published DeepSeek schedule: weekdays, UTC; peak costs 2x off-peak.
    peak_windows="1-4,6-10",
    peak_policy="off_peak",
    notes=(
        "DeepSeek peak hours are 01:00-04:00 and 06:00-10:00 UTC on "
        "weekdays; weekends are off-peak."
    ),
)

GENERIC = ModelProfile(
    id="generic",
    display="Model",
    default_model="deepseek-flash",
    models=(),
    context_window=1_000_000,
    tokenizer_encoding="cl100k_base",
    peak_windows="",
    peak_policy="always",
    notes="No provider-specific schedule is known; peak gating is off.",
)

PROFILES: tuple[ModelProfile, ...] = (DEEPSEEK, GENERIC)


def default_profile() -> ModelProfile:
    return DEEPSEEK


def profile_for(model: str = "") -> ModelProfile:
    """The profile matching a model id; DeepSeek is the default family."""

    for profile in PROFILES:
        if profile.models and profile.matches(model):
            return profile
    if not model.strip():
        return DEEPSEEK
    return GENERIC
