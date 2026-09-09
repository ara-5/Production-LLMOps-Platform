import json
import types
from unittest.mock import MagicMock

import pytest
from llmops_sdk.client import TraceClient
from llmops_sdk.pricing import calculate_cost, get_pricing


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


def test_ollama_models_are_free_regardless_of_token_count():
    rates = get_pricing("ollama:llama3.2:3b")
    assert rates == {"input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0}
    cost = calculate_cost("ollama:llama3.2:3b", input_tokens=50_000, output_tokens=50_000)
    assert cost == 0.0


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


class _FakeOllamaResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self._lines)


class _FakeOllamaStreamCM:
    def __init__(self, response: "_FakeOllamaResponse"):
        self._response = response

    def __enter__(self):
        return self._response

    def __exit__(self, *a):
        return False


class _FakeOllamaHttp:
    """Stands in for httpx.Client for TraceClient.ollama_http in tests."""

    def __init__(self, lines: list[str]):
        self._lines = lines
        self.calls: list[tuple] = []

    def stream(self, method, url, json=None):
        self.calls.append((method, url, json))
        return _FakeOllamaStreamCM(_FakeOllamaResponse(self._lines))


def _ollama_ndjson_lines() -> list[str]:
    return [
        json.dumps({"message": {"content": "Hel"}, "done": False}),
        json.dumps({"message": {"content": "lo"}, "done": False}),
        json.dumps(
            {
                "model": "llama3.2:3b",
                "message": {"content": ""},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 3,
            }
        ),
    ]


def test_llm_call_ollama_provider_parses_ndjson_stream_and_is_free():
    fake_anthropic = MagicMock()
    trace_client = TraceClient(backend_url="http://unused", anthropic_client=fake_anthropic, ship=False)
    trace_client.ollama_http = _FakeOllamaHttp(_ollama_ndjson_lines())

    with trace_client.trace("unit-test-ollama") as trace:
        result = trace.llm_call(
            model="ollama:llama3.2:3b",
            provider="ollama",
            base_url="http://localhost:11434",
            messages=[{"role": "user", "content": "hi"}],
        )

    assert result.text == "Hello"
    assert result.provider == "ollama"
    assert result.input_tokens == 10
    assert result.output_tokens == 3
    assert result.cost_usd == 0.0
    assert trace_client.ollama_http.calls[0][1] == "http://localhost:11434/api/chat"


def test_ollama_requires_base_url():
    fake_anthropic = MagicMock()
    trace_client = TraceClient(backend_url="http://unused", anthropic_client=fake_anthropic, ship=False)

    with trace_client.trace("unit-test-ollama-no-url") as trace, pytest.raises(ValueError, match="base_url"):
        trace.llm_call(model="ollama:llama3.2:3b", provider="ollama", messages=[{"role": "user", "content": "hi"}])


def test_fallback_to_ollama_attributes_trace_to_the_span_that_succeeded():
    """After a failed Claude call followed by a successful Ollama call in the
    same trace, model_id/ttft/tokens_per_sec must come from the Ollama span
    (the one that actually produced the answer), not the failed Claude one —
    this is the _primary_llm_span() behavior the Ollama fallback depends on."""
    fake_anthropic = MagicMock()
    fake_anthropic.messages.stream.side_effect = RuntimeError("no credentials configured")
    trace_client = TraceClient(backend_url="http://unused", anthropic_client=fake_anthropic, ship=False)
    trace_client.ollama_http = _FakeOllamaHttp(_ollama_ndjson_lines())

    shipped = []
    with trace_client.trace("unit-test-fallback", on_complete=shipped.append) as trace:
        with pytest.raises(RuntimeError):
            trace.llm_call(model="claude-sonnet-5", messages=[{"role": "user", "content": "hi"}])

        result = trace.llm_call(
            model="ollama:llama3.2:3b",
            provider="ollama",
            base_url="http://localhost:11434",
            messages=[{"role": "user", "content": "hi"}],
        )
        # mirrors what demo_app.rag_pipeline.answer_question does on a
        # successful fallback: the pipeline recovered, so the trace as a
        # whole succeeded even though its first attempt failed.
        trace.status = "ok"
        trace.error_type = None
        trace.tags["fallback_used"] = True

    assert result.provider == "ollama"
    payload = shipped[0]
    assert payload["trace"]["status"] == "ok"
    assert payload["trace"]["model_id"] == "ollama:llama3.2:3b"
    assert payload["trace"]["tags"]["fallback_used"] is True
    assert len(payload["spans"]) == 2
    assert payload["spans"][0]["status"] == "error"
    assert payload["spans"][1]["status"] == "ok"
