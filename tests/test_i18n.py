from __future__ import annotations

import unittest

from forgel import i18n


class LocalizationTest(unittest.TestCase):
    def test_locale_files_have_the_same_keys(self) -> None:
        self.assertEqual(set(i18n._load("en")), set(i18n._load("ru")))

    def test_russian_and_english_lookup(self) -> None:
        self.assertEqual(i18n.t("ru", "done"), "готово")
        self.assertEqual(i18n.t("en", "done"), "done")
        self.assertIn(
            "Операция не выполнена",
            i18n.t("ru", "failure_default", error="boom"),
        )
        self.assertIn(
            "could not be completed",
            i18n.t("en", "failure_default", error="boom"),
        )

    def test_unknown_language_and_missing_key_fall_back(self) -> None:
        self.assertEqual(i18n.t("de", "done"), "done")
        self.assertEqual(i18n.t("ru", "missing.key"), "missing.key")


if __name__ == "__main__":
    unittest.main()
