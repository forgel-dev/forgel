from __future__ import annotations

import unittest
from types import SimpleNamespace

from forgel.session_context import (
    MAX_STATE_CHARS,
    SessionState,
    budget_for,
    estimate_tokens,
    handoff_prompt,
    messages_tokens,
)


class EstimateTest(unittest.TestCase):
    def test_estimate_is_conservative_and_monotonic(self) -> None:
        self.assertGreaterEqual(estimate_tokens("a" * 300), 100)
        self.assertGreater(
            estimate_tokens("longer text"), estimate_tokens("short")
        )

    def test_messages_tokens_sums_content(self) -> None:
        messages = [
            SimpleNamespace(content="a" * 300),
            SimpleNamespace(content="b" * 300),
        ]
        self.assertGreaterEqual(messages_tokens(messages), 200)


class BudgetTest(unittest.TestCase):
    def test_small_window_reserves_a_quarter(self) -> None:
        budget = budget_for(4096)
        self.assertEqual(budget.reserve, 1024)
        self.assertEqual(budget.usable, 3072)
        self.assertEqual(budget.threshold, 2150)

    def test_large_window_reserves_the_cap(self) -> None:
        self.assertEqual(budget_for(131072).reserve, 8192)

    def test_compaction_threshold(self) -> None:
        budget = budget_for(4096)
        small = [SimpleNamespace(content="a" * 300)]
        large = [SimpleNamespace(content="a" * 9000)]
        self.assertFalse(budget.should_compact(small))
        self.assertTrue(budget.should_compact(large))


class SessionStateTest(unittest.TestCase):
    def test_state_markdown_carries_the_handoff(self) -> None:
        state = SessionState(
            task_id="t1",
            title="Add a page",
            session=2,
            requirements=["Add a page"],
            acceptance=["The page exists"],
            constraints=["stdlib only"],
            assumptions=["The page goes in main"],
            files_changed=["app.py"],
            actions=["write_file: app.py"],
            commands=[{"command": ["python", "-m", "unittest"], "exit_code": 0}],
            observations=["wrote app.py", "tests passed"],
        )
        text = state.to_markdown()
        self.assertIn("# Session State: Add a page", text)
        self.assertIn("- Session: 2", text)
        self.assertIn("Add a page", text)
        self.assertIn("The page goes in main", text)
        self.assertIn("write_file: app.py", text)
        self.assertIn("unittest", text)
        self.assertIn("exit 0", text)
        self.assertIn("tests passed", text)

    def test_state_is_bounded(self) -> None:
        state = SessionState(
            task_id="t1",
            title="Long",
            session=1,
            observations=["x" * 5000] * 10,
        )
        self.assertLessEqual(
            len(state.to_markdown()), MAX_STATE_CHARS + 40
        )

    def test_handoff_prompt_asks_to_continue(self) -> None:
        state = SessionState(task_id="t1", title="Task", session=1)
        prompt = handoff_prompt(state)
        self.assertIn("SESSION HANDOFF", prompt)
        self.assertIn("Continue", prompt)


if __name__ == "__main__":
    unittest.main()
