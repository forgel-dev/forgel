from __future__ import annotations

import unittest
from types import SimpleNamespace

from forgel.chat import _wants_runtime


def _result(operation: str) -> SimpleNamespace:
    return SimpleNamespace(
        kind="action",
        actions=[
            {
                "action": "runtime",
                "action_args": {"operation": operation},
            }
        ],
    )


class RuntimeDrainTest(unittest.TestCase):
    def test_a_runtime_retry_continues_the_runtime(self) -> None:
        for operation in (
            "task_retry",
            "task_restart",
            "drive",
            "task_process",
        ):
            with self.subTest(operation=operation):
                self.assertTrue(_wants_runtime(_result(operation)))

    def test_a_runtime_respec_does_not_start_work(self) -> None:
        self.assertFalse(_wants_runtime(_result("task_respec")))

    def test_a_runtime_cancel_does_not_continue(self) -> None:
        self.assertFalse(_wants_runtime(_result("task_cancel")))
        self.assertFalse(_wants_runtime(_result("set_limit")))


if __name__ == "__main__":
    unittest.main()
