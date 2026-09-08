import types
from unittest.mock import MagicMock

import pytest

from llmops_sdk.client import TraceClient
from llmops_sdk.pricing import calculate_cost


def test_calculate_cost_basic():
    cost = calculate_cost("claude-sonnet-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(12.0)


def test_calculate_cost_with_cache():
    cost = calculate_cost(
        "claude-opus-5",
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=1_000_000,
        cache_creation_tokens=1_000_000,
    )
    assert cost == pytest.approx(0.50 + 6.25)


def test_calculate_cost_unknown_model_uses_default():
    cost = calculate_cost("some-future-model", input_tokens=1_000_000, output_tokens=0)
    assert cost == pytest.approx(3.00)


class _FakeUsage:
    def __init__(self):
        self.input_tokens = 120
        self.output_tokens = 45
        self.cache_read_input_tokens = 0
        self.cache_creation_input_tokens = 0


class _FakeTextBlock:
    type = "text"
    text = "hello world"


class _FakeMessage:
    def __init__(self):
        self.usage = _FakeUsage()
        self.content = [_FakeTextBlock()]
        self.model = "claude-sonnet-5"
        self.stop_reason = "end_turn"


class _FakeStream:
    def __init__(self):
        self._events = [types.SimpleNamespace(type="content_block_delta")]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self._events)

    def get_final_message(self):
        return _FakeMessage()


def test_llm_call_records_usage_and_ships_trace():
    fake_anthropic = MagicMock()
    fake_anthropic.messages.stream.return_value = _FakeStream()

    shipped = []
    trace_client = TraceClient(backend_url="http://unused", anthropic_client=fake_anthropic, ship=False)

    with trace_client.trace("unit-test-trace", on_complete=shipped.append) as trace:
        result = trace.llm_call(model="claude-sonnet-5", messages=[{"role": "user", "content": "hi"}])

    assert result.input_tokens == 120
    assert result.output_tokens == 45
    assert result.text == "hello world"
    assert result.cost_usd > 0

    assert len(shipped) == 1
    payload = shipped[0]
    assert payload["trace"]["status"] == "ok"
    assert payload["trace"]["model_id"] == "claude-sonnet-5"
    assert payload["trace"]["input_tokens"] == 120
    assert len(payload["spans"]) == 1
    assert payload["spans"][0]["span_kind"] == "llm"
