"""Locale tables and lookup for human-facing strings.

Locale files live next to this module under ``locales/<code>.json``. The
product falls back to English for an unknown language or a missing key, so a
new locale never breaks the runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .language import LANGUAGES, detect as _detect, name as _name

DEFAULT = "en"
LOCALES_DIR = Path(__file__).with_name("locales")
_CACHE: dict[str, dict[str, str]] = {}


def _load(lang: str) -> dict[str, str]:
    code = str(lang or "").strip().lower()
    if code not in LANGUAGES:
        code = DEFAULT
    if code not in _CACHE:
        path = LOCALES_DIR / f"{code}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        _CACHE[code] = data if isinstance(data, dict) else {}
    return _CACHE[code]


def t(lang: str, text_key: str, **values: Any) -> str:
    table = _load(lang)
    template = table.get(text_key)
    if template is None:
        template = _load(DEFAULT).get(text_key, text_key)
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def has(lang: str, key: str) -> bool:
    return key in _load(lang) or key in _load(DEFAULT)


def detect(text: str, default: str = DEFAULT) -> str:
    return _detect(text, default)


def name(code: str) -> str:
    return _name(code)
