"""Token-cost accounting for recorded model usage.

Prices are USD per one million tokens. The defaults come from the model
profile; a project can override them with `FORGEL_MODEL_INPUT_PRICE` and
`FORGEL_MODEL_OUTPUT_PRICE`. The result is recorded on the ledger event, so a
cost report can be checked without a second source of truth.
"""

from __future__ import annotations

DEFAULT_INPUT_PRICE = 0.28
DEFAULT_OUTPUT_PRICE = 0.42


def token_cost(
    input_tokens: object,
    output_tokens: object,
    input_price: object = DEFAULT_INPUT_PRICE,
    output_price: object = DEFAULT_OUTPUT_PRICE,
) -> float:
    try:
        inputs = max(0, int(input_tokens or 0))
        outputs = max(0, int(output_tokens or 0))
        in_rate = max(0.0, float(input_price or 0.0))
        out_rate = max(0.0, float(output_price or 0.0))
    except (TypeError, ValueError):
        return 0.0
    return (inputs * in_rate + outputs * out_rate) / 1_000_000
