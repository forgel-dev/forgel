"""Paged context windows for every model turn.

A prompt is a window over a larger set of artifacts: the task record, its
specification, reports, the diff, the environment, the instructions, the
history. When an artifact does not fit, it is split into pages; the prompt
carries the manifest and as many first pages as fit, and the model asks for
any page it needs with a ``context_page`` action. Nothing is silently
truncated: the model always sees how much exists and can scroll to it.

The same mechanism serves every role that receives a context: the chat agent,
the controlling agent, the reviewer, the specification writer and the session
handoff. A role that supports actions handles ``context_page`` exactly like
its other read actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PAGE_CHARS = 8_000

CONTEXT_ACTION = (
    '{"action": "context_page", "key": "<item key>", "page": <number>}'
)


@dataclass(frozen=True)
class Item:
    """One named artifact in the window."""

    key: str
    title: str
    text: str

    @property
    def pages(self) -> int:
        if not self.text:
            return 1
        return max(1, (len(self.text) + PAGE_CHARS - 1) // PAGE_CHARS)


def page_text(text: str, page: int, size: int = PAGE_CHARS) -> str:
    """One 1-based page of ``text``; an out-of-range page is an error."""

    if page < 1:
        raise ValueError("a page number starts at 1")
    total = max(1, (len(text) + size - 1) // size) if text else 1
    if page > total:
        raise ValueError(f"page {page} is outside 1..{total}")
    start = (page - 1) * size
    return text[start : start + size]


class ContextWindow:
    """A paged view over named artifacts."""

    def __init__(self, items: Iterable[Item]) -> None:
        self._items: dict[str, Item] = {}
        for item in items:
            self._items[item.key] = item

    def keys(self) -> list[str]:
        return list(self._items)

    def manifest(self) -> str:
        lines = [
            "Paged context. Every item is available in full; nothing is "
            "truncated.",
        ]
        for key, item in self._items.items():
            lines.append(
                f"- {key} ({item.title}): {len(item.text)} chars, "
                f"{item.pages} page(s)"
            )
        lines.append(
            "Read any page with " + CONTEXT_ACTION + "."
        )
        return "\n".join(lines)

    def render(self, budget: int = 60_000) -> str:
        """The first pages that fit, plus the manifest of everything."""

        parts = [self.manifest(), ""]
        used = 0
        for key, item in self._items.items():
            header = f"### {key} — {item.title} (page 1/{item.pages})"
            first = page_text(item.text, 1) if item.text else "(empty)"
            block = f"{header}\n{first}"
            if item.pages > 1:
                block += (
                    f"\n[page 1 of {item.pages}; read more with "
                    + CONTEXT_ACTION.replace("<item key>", key)
                    + "]"
                )
            if used + len(block) > budget and used > 0:
                parts.append(
                    f"### {key} — {item.title}: not shown yet "
                    f"({item.pages} page(s)); read page 1 with "
                    + CONTEXT_ACTION.replace("<item key>", key)
                )
                continue
            parts.append(block)
            used += len(block)
        return "\n\n".join(parts)

    def read(self, key: str, page: int) -> str:
        item = self._items.get(key)
        if item is None:
            raise KeyError(
                f"unknown context {key!r}; known: "
                + ", ".join(self._items)
            )
        text = page_text(item.text, page)
        return (
            f"### {key} — {item.title} (page {page}/{item.pages})\n{text}"
        )

    def has(self, key: str) -> bool:
        return key in self._items
