"""Subprocess output helpers.

``subprocess.run(..., text=True)`` returns ``str`` on success, but a
``TimeoutExpired`` carries raw ``bytes`` even in text mode. Concatenating the
two raises TypeError; merge them through one place instead.
"""

from __future__ import annotations


def as_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None:
        return ""
    return str(value)


def merge_output(stdout: object, stderr: object) -> str:
    return as_text(stdout) + as_text(stderr)
