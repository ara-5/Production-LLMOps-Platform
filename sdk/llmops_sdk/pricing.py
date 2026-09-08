"""Claude model pricing table (USD per 1M tokens) and cost calculation."""

from __future__ import annotations

# USD per 1,000,000 tokens. cache_read is charged at Anthropic's discounted
# cache-hit rate; cache_write (cache creation) is charged at a premium over
# the base input rate for the write turn.
PRICING_TABLE: dict[str, dict[str, float]] = {
    "claude-opus-5": {"input": 5.00, "output": 25.00, "cache_read": 0.50, "cache_write": 6.25},
    "claude-sonnet-5": {"input": 2.00, "output": 10.00, "cache_read": 0.20, "cache_write": 2.50},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25},
}

DEFAULT_PRICING = {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75}

_PER_MILLION = 1_000_000


def get_pricing(model_id: str) -> dict[str, float]:
    return PRICING_TABLE.get(model_id, DEFAULT_PRICING)


def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Compute the USD cost of a single LLM call from its token usage."""
    rates = get_pricing(model_id)
    cost = (
        input_tokens * rates["input"]
        + output_tokens * rates["output"]
        + cache_read_tokens * rates["cache_read"]
        + cache_creation_tokens * rates["cache_write"]
    ) / _PER_MILLION
    return round(cost, 8)
