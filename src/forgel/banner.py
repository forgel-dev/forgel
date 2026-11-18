"""Startup banner for the interactive console.

The banner is brand, not data: it appears only when Forgel opens a real
terminal. Piped output, tests and scripted commands keep the plain text
contract and never see it.
"""

from __future__ import annotations

BANNER = """\
█████  █████  ████   █████  █████  ██
██     ██ ██  ██ ██  ██     ██     ██
████   ██ ██  ████   ██ ██  ████   ██
██     ██ ██  ██ ██  ██ ██  ██     ██
██     █████  ██ ██  █████  █████  █████

  Brief in. Product out. Your cloud."""
