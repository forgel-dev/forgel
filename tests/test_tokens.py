from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from forgel.tokens import count_tokens, heuristic_tokens, tokenizer_name


class TokenTest(unittest.TestCase):
    def test_heuristic_is_conservative(self) -> None:
        self.assertGreaterEqual(heuristic_tokens("a" * 300), 100)
        self.assertEqual(heuristic_tokens(""), 1)

    def test_count_is_positive(self) -> None:
        self.assertGreaterEqual(count_tokens("hello world"), 1)
        self.assertEqual(count_tokens(""), 0)

    def test_heuristic_can_be_forced(self) -> None:
        with patch.dict(
            os.environ, {"FORGEL_TOKENIZER": "heuristic"}, clear=False
        ):
            self.assertTrue(tokenizer_name().startswith("heuristic"))
            self.assertEqual(count_tokens("a" * 300), 100)

    def test_name_reflects_the_available_backend(self) -> None:
        with patch.dict(
            os.environ, {"FORGEL_TOKENIZER": "auto"}, clear=False
        ):
            name = tokenizer_name()
        self.assertTrue(name.startswith(("heuristic", "tiktoken")))


if __name__ == "__main__":
    unittest.main()
