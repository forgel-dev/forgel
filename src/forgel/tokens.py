"""Token counting for the context budget.

A real tokenizer is optional: when ``tiktoken`` is installed
(``pip install 'forgel[tokens]'``, included in the Docker image), prompts are
counted with the closest available BPE encoding. Without it, a conservative
heuristic is used (~3 characters per token), which overestimates rather than
overflows.

No encoding is an exact match for every provider. The budget only needs to be
safe; the provider's own usage numbers remain the source of truth for billing.
Set ``FORGEL_TOKENIZER=heuristic`` to force the dependency-free path.
"""

from __future__ import annotations

import math
import os
from typing import Any

FALLBACK_CHARS_PER_TOKEN = 3.0
DEFAULT_ENCODING = "cl100k_base"
_ENCODERS: dict[str, Any] = {}
_UNAVAILABLE = object()


def _force_heuristic() -> bool:
    return os.environ.get("FORGEL_TOKENIZER", "auto").strip().lower() == (
        "heuristic"
    )


def _encoder(model: str = "") -> Any:
    if _force_heuristic():
        return None
    key = model or DEFAULT_ENCODING
    if key in _ENCODERS:
        cached = _ENCODERS[key]
        return None if cached is _UNAVAILABLE else cached
    try:
        import tiktoken
    except ImportError:
        _ENCODERS[key] = _UNAVAILABLE
        return None
    try:
        encoding = tiktoken.encoding_for_model(model) if model else None
    except Exception:
        encoding = None
    if encoding is None:
        try:
            encoding = tiktoken.get_encoding(DEFAULT_ENCODING)
        except Exception:
            _ENCODERS[key] = _UNAVAILABLE
            return None
    _ENCODERS[key] = encoding
    return encoding


def heuristic_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / FALLBACK_CHARS_PER_TOKEN))


def count_tokens(text: str, model: str = "") -> int:
    """Count tokens with a real encoder when possible, else conservatively."""

    if not text:
        return 0
    encoding = _encoder(model)
    if encoding is None:
        return heuristic_tokens(text)
    try:
        return max(1, len(encoding.encode(text, disallowed_special=())))
    except Exception:
        return heuristic_tokens(text)


def tokenizer_name(model: str = "") -> str:
    encoding = _encoder(model)
    if encoding is None:
        return f"heuristic ({FALLBACK_CHARS_PER_TOKEN:g} chars/token)"
    name = getattr(encoding, "name", DEFAULT_ENCODING)
    return f"tiktoken:{name}"
