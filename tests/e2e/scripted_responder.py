#!/usr/bin/env python3
"""A bridge command that replays the scripted blog actions.

Used to test the subagent bridge itself without a real model:

    python tests/e2e/run_blog_e2e.py --mode bridge \
      --driver-command "python tests/e2e/scripted_responder.py" --strict
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.e2e.blog_actions import responses  # noqa: E402


def main() -> int:
    prompt = sys.stdin.read()
    previous = prompt.count("\nASSISTANT:")
    actions = responses()
    if previous < len(actions):
        print(actions[previous])
        return 0
    print(
        json.dumps(
            {
                "action": "fail",
                "reason": "scripted responder has no action left",
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
