import pytest
from app.services.cost import calculate_cost, get_pricing


def test_get_pricing_known_model():
    rates = get_pricing("claude-opus-5")
    assert rates["input"] == 5.00
    assert rates["output"] == 25.00


def test_calculate_cost_matches_manual_math():
    # 250k input tokens + 10k output tokens on Sonnet 5 ($2/$10 per 1M)
    cost = calculate_cost("claude-sonnet-5", input_tokens=250_000, output_tokens=10_000)
    expected = (250_000 * 2.00 + 10_000 * 10.00) / 1_000_000
    assert cost == pytest.approx(expected)


def test_calculate_cost_zero_tokens():
    assert calculate_cost("claude-haiku-4-5", input_tokens=0, output_tokens=0) == 0.0
