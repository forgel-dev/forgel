from __future__ import annotations

import unittest

from forgel.context_window import (
    CONTEXT_ACTION,
    PAGE_CHARS,
    ContextWindow,
    Item,
    page_text,
)


class ContextWindowTest(unittest.TestCase):
    def test_a_large_item_is_paged_not_truncated(self) -> None:
        text = "x" * (PAGE_CHARS * 2 + 10)
        window = ContextWindow([Item("big", "a big artifact", text)])

        rendered = window.render(budget=10_000)

        self.assertIn("3 page(s)", rendered)
        self.assertIn("page 1/3", rendered)
        self.assertIn(
            CONTEXT_ACTION.replace("<item key>", "big"), rendered
        )
        third = window.read("big", 3)
        self.assertIn("page 3/3", third)
        self.assertTrue(third.endswith("x" * 10))

    def test_the_manifest_lists_every_item_under_a_tight_budget(self) -> None:
        window = ContextWindow(
            [
                Item("one", "first", "a" * 20_000),
                Item("two", "second", "b" * 20_000),
            ]
        )

        rendered = window.render(budget=9_000)

        self.assertIn("- one (first): 20000 chars, 3 page(s)", rendered)
        self.assertIn("- two (second): 20000 chars, 3 page(s)", rendered)
        self.assertIn("not shown yet", rendered)

    def test_an_unknown_item_or_page_is_an_error(self) -> None:
        window = ContextWindow([Item("one", "first", "a")])
        with self.assertRaises(KeyError):
            window.read("missing", 1)
        with self.assertRaises(ValueError):
            window.read("one", 2)

    def test_page_text_is_one_based(self) -> None:
        self.assertEqual(page_text("abcdef", 1, size=2), "ab")
        self.assertEqual(page_text("abcdef", 3, size=2), "ef")
        with self.assertRaises(ValueError):
            page_text("abcdef", 0, size=2)


if __name__ == "__main__":
    unittest.main()
