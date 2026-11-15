"""User-facing language selection.

Forgel answers in the language of the user's request. The product currently
ships human-facing strings for English and Russian; a request in another
script falls back to English. Model-generated answers are free to use any
language, so only the fixed runtime text needs a translation table.
"""

from __future__ import annotations

LANGUAGES = ("en", "ru")
NAMES = {"en": "English", "ru": "Russian"}
CYRILLIC = range(0x0400, 0x0500)


def detect(text: str, default: str = "en") -> str:
    """Return the language of ``text`` from its script.

    Cyrillic wins when it is at least as common as Latin letters; this keeps
    short mixed phrases such as "ok, давай" Russian. Text without letters
    keeps the current default.
    """

    cyrillic = 0
    latin = 0
    for char in str(text or ""):
        if ord(char) in CYRILLIC:
            cyrillic += 1
        elif char.isascii() and char.isalpha():
            latin += 1
    if cyrillic == 0 and latin == 0:
        return default
    return "ru" if cyrillic >= latin else "en"


def name(code: str, default: str = "English") -> str:
    return NAMES.get(str(code or "").strip().lower(), default)
