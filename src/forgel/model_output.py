"""Parse a model response into the JSON objects it contains.

A model may emit one object, several concatenated objects, or a JSON array in
one message. Slicing from the first ``{`` to the last ``}`` fails on a batch
and hides the real model output; callers use this parser instead.
"""

from __future__ import annotations

import json
from typing import Any

TOOL_MARKUP_MARKERS = (
    "<｜｜dsml｜｜",
    "<|",
    "<tool_call",
    "<tool_result",
    "<function_call",
    "<parameter",
    "</invoke>",
    "<system_warning",
)


def looks_like_tool_markup(text: str) -> bool:
    """True when a reply is provider tool-call markup, not the JSON asked for."""

    lowered = text.lower()
    return any(marker in lowered for marker in TOOL_MARKUP_MARKERS)


def _prepare(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()
    return text


def json_objects(raw: str) -> list[dict[str, Any]]:
    """All JSON objects in ``raw``, in order; arrays are flattened."""

    text = _prepare(raw)
    decoder = json.JSONDecoder()
    objects: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        start = -1
        for position in range(index, len(text)):
            if text[position] in "{[":
                start = position
                break
        if start < 0:
            break
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        index = end
        if isinstance(value, dict):
            objects.append(value)
        elif isinstance(value, list):
            objects.extend(
                item for item in value if isinstance(item, dict)
            )
    return objects


def first_object(raw: str) -> dict[str, Any] | None:
    objects = json_objects(raw)
    return objects[0] if objects else None


def last_object(raw: str) -> dict[str, Any] | None:
    objects = json_objects(raw)
    return objects[-1] if objects else None
