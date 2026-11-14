from __future__ import annotations

import unittest

from forgel.model_profiles import (
    DEEPSEEK,
    GENERIC,
    default_profile,
    profile_for,
)


class ProfileTest(unittest.TestCase):
    def test_deepseek_models_match_the_family(self) -> None:
        for model in ("deepseek-flash", "deepseek-chat", "DeepSeek-V3"):
            with self.subTest(model=model):
                self.assertIs(profile_for(model), DEEPSEEK)

    def test_an_empty_model_uses_the_default_profile(self) -> None:
        self.assertIs(profile_for(""), DEEPSEEK)
        self.assertIs(default_profile(), DEEPSEEK)

    def test_another_family_gets_the_generic_profile(self) -> None:
        self.assertIs(profile_for("gpt-4o"), GENERIC)
        self.assertIs(profile_for("qwen3-coder"), GENERIC)

    def test_defaults_live_in_the_profile(self) -> None:
        self.assertEqual(DEEPSEEK.default_model, "deepseek-flash")
        self.assertEqual(DEEPSEEK.context_window, 1_000_000)
        self.assertEqual(DEEPSEEK.peak_windows, "1-4,6-10")
        self.assertEqual(DEEPSEEK.peak_policy, "off_peak")
        self.assertEqual(DEEPSEEK.tokenizer_encoding, "cl100k_base")
        self.assertEqual(GENERIC.peak_policy, "always")


if __name__ == "__main__":
    unittest.main()
