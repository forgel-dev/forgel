#!/usr/bin/env python3
"""Fulfil Forgel bridge requests with an external model command.

The command reads a prompt on stdin and prints the model answer on stdout.
Example:

    python tests/e2e/subagent_driver.py \
      --bridge-dir /tmp/forgel-e2e/model-bridge \
      --command "your-llm-cli --print"

The bridge is how a local run uses subagents instead of a paid provider API.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path


def prompt_from_request(request: dict) -> str:
    parts: list[str] = []
    for message in request.get("messages", []):
        role = str(message.get("role", "user")).upper()
        parts.append(f"{role}:\n{message.get('content', '')}")
    return "\n\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bridge-dir", type=Path, required=True)
    parser.add_argument(
        "--command",
        required=True,
        help="Command that reads the prompt on stdin and prints the answer",
    )
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args()

    command = shlex.split(args.command)
    if not command:
        print("error: empty command", file=sys.stderr)
        return 2
    bridge = args.bridge_dir
    bridge.mkdir(parents=True, exist_ok=True)
    print(f"bridge driver watching {bridge}", file=sys.stderr)
    handled = 0
    while True:
        for request_path in sorted(bridge.glob("*.request.json")):
            request_id = request_path.name[: -len(".request.json")]
            response_path = bridge / f"{request_id}.response.json"
            error_path = bridge / f"{request_id}.error.json"
            if response_path.exists() or error_path.exists():
                continue
            try:
                request = json.loads(
                    request_path.read_text(encoding="utf-8")
                )
                prompt = prompt_from_request(request)
                completed = subprocess.run(
                    command,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout,
                    check=False,
                )
                if completed.returncode != 0:
                    error_path.write_text(
                        json.dumps(
                            {
                                "error": completed.stderr.strip()
                                or f"command exited {completed.returncode}"
                            }
                        ),
                        encoding="utf-8",
                    )
                elif not completed.stdout.strip():
                    error_path.write_text(
                        json.dumps({"error": "command returned an empty answer"}),
                        encoding="utf-8",
                    )
                else:
                    response_path.write_text(
                        json.dumps({"content": completed.stdout.strip()}),
                        encoding="utf-8",
                    )
                handled += 1
                print(
                    f"handled {request_id} ({handled})", file=sys.stderr
                )
            except Exception as exc:  # noqa: BLE001 - report to the bridge
                try:
                    error_path.write_text(
                        json.dumps({"error": str(exc)}), encoding="utf-8"
                    )
                except OSError:
                    pass
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
