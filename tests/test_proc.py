from __future__ import annotations

import unittest

from forgel.proc import as_text, merge_output


class ProcOutputTest(unittest.TestCase):
    def test_str_parts_are_merged(self) -> None:
        self.assertEqual(merge_output("out", "err"), "outerr")

    def test_bytes_are_decoded(self) -> None:
        self.assertEqual(merge_output(b"out", b"err"), "outerr")

    def test_mixed_and_missing_parts_are_safe(self) -> None:
        self.assertEqual(merge_output(b"out", None), "out")
        self.assertEqual(merge_output(None, b"err"), "err")
        self.assertEqual(merge_output("out", b"err"), "outerr")
        self.assertEqual(merge_output(None, None), "")

    def test_invalid_bytes_are_replaced(self) -> None:
        self.assertEqual(as_text(b"a\xffb"), "a�b")


if __name__ == "__main__":
    unittest.main()
