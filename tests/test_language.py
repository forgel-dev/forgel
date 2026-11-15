from __future__ import annotations

import unittest

from forgel.language import detect, name


class LanguageTest(unittest.TestCase):
    def test_russian_request_selects_russian(self) -> None:
        self.assertEqual(detect("Продолжаем"), "ru")
        self.assertEqual(detect("ok, давай"), "ru")

    def test_english_request_selects_english(self) -> None:
        self.assertEqual(detect("continue"), "en")
        self.assertEqual(detect("accept"), "en")

    def test_text_without_letters_keeps_the_default(self) -> None:
        self.assertEqual(detect("123", "ru"), "ru")
        self.assertEqual(detect("123", "en"), "en")
        self.assertEqual(detect("M1", "ru"), "en")

    def test_names(self) -> None:
        self.assertEqual(name("ru"), "Russian")
        self.assertEqual(name("en"), "English")
        self.assertEqual(name(""), "English")


if __name__ == "__main__":
    unittest.main()
