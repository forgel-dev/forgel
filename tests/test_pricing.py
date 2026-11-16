from __future__ import annotations

import unittest

from forgel.pricing import token_cost


class PricingTest(unittest.TestCase):
    def test_cost_uses_per_million_rates(self) -> None:
        self.assertAlmostEqual(
            token_cost(1_000_000, 1_000_000, 0.28, 0.42), 0.70
        )
        self.assertAlmostEqual(
            token_cost(500_000, 250_000, 0.28, 0.42), 0.245
        )

    def test_missing_or_invalid_values_are_zero(self) -> None:
        self.assertEqual(token_cost(None, None), 0.0)
        self.assertEqual(token_cost("bad", 10), 0.0)
        self.assertEqual(token_cost(-5, -5), 0.0)


if __name__ == "__main__":
    unittest.main()
