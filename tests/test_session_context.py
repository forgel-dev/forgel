from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from forgel.session_context import (
    SessionState,
    budget_for,
    handoff_prompt,
    messages_tokens,
)
from forgel.tokens import count_tokens, heuristic_tokens


class EstimateTest(unittest.TestCase):
    def test_estimate_is_conservative_and_monotonic(self) -> None:
        self.assertGreaterEqual(heuristic_tokens("a" * 300), 100)
        self.assertGreater(
            heuristic_tokens("longer text"), heuristic_tokens("short")
        )

    def test_messages_tokens_sums_content(self) -> None:
        messages = [
            SimpleNamespace(content="a" * 300),
            SimpleNamespace(content="b" * 300),
        ]
        with patch(
            "forgel.session_context.count_tokens",
            side_effect=lambda text, model="": heuristic_tokens(text),
        ):
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
        with patch(
            "forgel.session_context.count_tokens",
            side_effect=lambda text, model="": heuristic_tokens(text),
        ):
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
            next_step="Fix the failing check",
            last_test_outcome="failed: python -m unittest (exit 1)",
            failing_check="python -m unittest",
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
        self.assertIn("## Last Test Outcome", text)
        self.assertIn("## Failing Check", text)
        self.assertIn("## Next Step", text)
        self.assertIn("Fix the failing check", text)
        self.assertIn("failed: python -m unittest (exit 1)", text)

    def test_state_is_bounded(self) -> None:
        state = SessionState(
            task_id="t1",
            title="Long",
            session=1,
            observations=["x" * 5000] * 10,
        )
        text = state.to_markdown(max_tokens=300)
        self.assertLessEqual(count_tokens(text), 500)
        self.assertNotIn("x" * 5000, text)

    def test_handoff_prompt_asks_to_continue(self) -> None:
        state = SessionState(task_id="t1", title="Task", session=1)
        prompt = handoff_prompt(state)
        self.assertIn("SESSION HANDOFF", prompt)
        self.assertIn("Continue", prompt)


if __name__ == "__main__":
    unittest.main()
