"""Shared test fixtures.

The product holds model work during DeepSeek peak hours, and an adopted
project's generated ``forgel.toml`` carries that default. A test that drives
model work through such a project would then fail inside a real peak window,
so fixtures pin the policy explicitly instead of following the wall clock.
"""

from __future__ import annotations

from pathlib import Path

from forgel import config_store
from forgel.layout import ProjectLayout


def pin_peak_always(workspace: str | Path) -> None:
    """Make a test project independent of the current peak window."""

    layout = ProjectLayout.detect(str(workspace))
    config_store.set_project_value(
        layout.control, "models.peak_policy", "always"
    )
