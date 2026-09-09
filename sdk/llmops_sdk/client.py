"""Instrumentation SDK: wraps LLM calls (Anthropic Claude, with an optional
local Ollama fallback) inside traces/spans and ships them to the platform's
ingest API.

Usage:

    trace_client = TraceClient(backend_url="http://localhost:8000")
    with trace_client.trace("rag.answer_question", prompt_version_id=3) as trace:
        with trace.span("retrieve", kind="retrieval") as span:
            chunks = retriever.retrieve(question)
            span.set_attributes(**{"llmops.retrieval.doc_ids": [c.doc_id for c in chunks]})
        result = trace.llm_call(model="claude-sonnet-5", messages=[...])

        # Or, to call a local Ollama model instead of Claude (e.g. as a
        # resilience fallback when Claude is unavailable):
        result = trace.llm_call(
            model="ollama:llama3.2:3b", provider="ollama",
            base_url="http://localhost:11434", messages=[...],
        )
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import anthropic
import httpx

from . import otel_attrs as attrs
from .pricing import OLLAMA_MODEL_PREFIX, calculate_cost


def _now_ms() -> float:
    return time.perf_counter() * 1000


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _classify_error(exc: BaseException, provider: str = "anthropic") -> str:
    if provider == "ollama":
        if isinstance(exc, httpx.ConnectError):
            return "connection_error"
        if isinstance(exc, httpx.TimeoutException):
            return "timeout"
        if isinstance(exc, httpx.HTTPStatusError):
            return "api_error"
        return "other"
    if isinstance(exc, anthropic.APITimeoutError):
        return "timeout"
    if isinstance(exc, anthropic.RateLimitError):
        return "rate_limit"
    if isinstance(exc, anthropic.APIStatusError):
        return "api_error"
    if isinstance(exc, anthropic.APIConnectionError):
        return "connection_error"
    return "other"


@dataclass
class LLMCallResult:
    message: Any
    text: str
    ttft_ms: int
    latency_ms: int
    tokens_per_sec: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    stop_reason: str | None = None
    provider: str = "anthropic"


@dataclass
class _SpanRecord:
    span_id: str
    name: str
    span_kind: str
    started_at: float
    parent_span_id: str | None = None
    ended_at: float | None = None
    latency_ms: int | None = None
    status: str = "ok"
    status_message: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    attributes: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_kind": self.span_kind,
            "started_at": _iso(self.started_at),
            "ended_at": _iso(self.ended_at) if self.ended_at else None,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "status_message": self.status_message,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cost_usd": self.cost_usd,
            "attributes": self.attributes,
        }


class SpanContext:
    def __init__(self, record: _SpanRecord):
        self._record = record

    def set_attributes(self, **kwargs: Any) -> None:
        self._record.attributes.update(kwargs)

    def set_error(self, message: str) -> None:
        self._record.status = "error"
        self._record.status_message = message

    def set_usage(
        self,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        self._record.input_tokens = input_tokens
        self._record.output_tokens = output_tokens
        self._record.cache_read_tokens = cache_read_tokens
        self._record.cache_creation_tokens = cache_creation_tokens
        self._record.cost_usd = cost_usd


class TraceContext:
    def __init__(
        self,
        trace_client: TraceClient,
        name: str,
        prompt_version_id: int | None,
        dataset_item_id: int | None,
        tags: dict | None,
    ):
        self.trace_client = trace_client
        self.trace_id = str(uuid.uuid4())
        self.name = name
        self.prompt_version_id = prompt_version_id
        self.dataset_item_id = dataset_item_id
        self.tags = tags or {}
        self.started_at = time.time()
        self.ended_at: float | None = None
        self.status = "ok"
        self.error_type: str | None = None
        self.retry_count = 0
        self.spans: list[_SpanRecord] = []
        self._span_stack: list[str] = []

    @contextmanager
    def span(self, name: str, kind: str = "tool") -> Iterator[SpanContext]:
        record = _SpanRecord(
            span_id=str(uuid.uuid4()),
            name=name,
            span_kind=kind,
            started_at=time.time(),
            parent_span_id=self._span_stack[-1] if self._span_stack else None,
        )
        self._span_stack.append(record.span_id)
        self.spans.append(record)
        ctx = SpanContext(record)
        try:
            yield ctx
        except Exception as exc:
            record.status = "error"
            record.status_message = str(exc)
            raise
        finally:
            record.ended_at = time.time()
            record.latency_ms = int((record.ended_at - record.started_at) * 1000)
            self._span_stack.pop()

    def _call_anthropic(
        self,
        *,
        model: str,
        messages: list[dict],
        system: str | None,
        max_tokens: int,
        thinking: dict | None,
        output_config: dict | None,
        extra_kwargs: dict,
    ) -> tuple[Any, str, int, int, int, int, str | None, str, float | None, float]:
        request_kwargs: dict[str, Any] = dict(model=model, max_tokens=max_tokens, messages=messages, **extra_kwargs)
        if system is not None:
            request_kwargs["system"] = system
        if thinking is not None:
            request_kwargs["thinking"] = thinking
        if output_config is not None:
            request_kwargs["output_config"] = output_config

        t_first_token: float | None = None
        with self.trace_client.anthropic.messages.stream(**request_kwargs) as stream:
            for event in stream:
                if t_first_token is None and event.type == "content_block_delta":
                    t_first_token = _now_ms()
            message = stream.get_final_message()
        t_end = _now_ms()

        usage = message.usage
        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0
        cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
        text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")

        return (
            message, text, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
            message.stop_reason, message.model, t_first_token, t_end,
        )

    def _call_ollama(
        self,
        *,
        base_url: str,
        model: str,
        messages: list[dict],
        system: str | None,
        max_tokens: int,
    ) -> tuple[Any, str, int, int, int, int, str | None, str, float | None, float]:
        ollama_model = model.removeprefix(OLLAMA_MODEL_PREFIX)
        payload_messages = list(messages)
        if system is not None:
            payload_messages = [{"role": "system", "content": system}] + payload_messages

        body = {
            "model": ollama_model,
            "messages": payload_messages,
            "stream": True,
            "options": {"num_predict": max_tokens},
        }

        t_first_token: float | None = None
        text_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        stop_reason = "stop"
        response_model = ollama_model
        final_chunk: dict = {}

        with self.trace_client.ollama_http.stream("POST", f"{base_url.rstrip('/')}/api/chat", json=body) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    if t_first_token is None:
                        t_first_token = _now_ms()
                    text_parts.append(content)
                if chunk.get("done"):
                    final_chunk = chunk
        t_end = _now_ms()

        input_tokens = final_chunk.get("prompt_eval_count", 0) or 0
        output_tokens = final_chunk.get("eval_count", 0) or 0
        stop_reason = final_chunk.get("done_reason", stop_reason)
        response_model = final_chunk.get("model", response_model)
        text = "".join(text_parts)

        return (final_chunk, text, input_tokens, output_tokens, 0, 0, stop_reason, response_model, t_first_token, t_end)

    def llm_call(
        self,
        *,
        model: str,
        messages: list[dict],
        system: str | None = None,
        max_tokens: int = 16000,
        thinking: dict | None = None,
        output_config: dict | None = None,
        provider: str = "anthropic",
        base_url: str | None = None,
        span_kind: str = "llm",
        span_name: str = "llm.generate",
        **kwargs: Any,
    ) -> LLMCallResult:
        if provider not in ("anthropic", "ollama"):
            raise ValueError(f"unknown provider {provider!r} — expected 'anthropic' or 'ollama'")
        if provider == "ollama" and not base_url:
            raise ValueError("base_url is required when provider='ollama'")

        with self.span(span_name, kind=span_kind) as span:
            span.set_attributes(**{
                attrs.GEN_AI_SYSTEM: attrs.OLLAMA_SYSTEM if provider == "ollama" else attrs.ANTHROPIC_SYSTEM,
                attrs.GEN_AI_OPERATION_NAME: "chat",
                attrs.GEN_AI_REQUEST_MODEL: model,
                attrs.GEN_AI_REQUEST_MAX_TOKENS: max_tokens,
            })
            if thinking:
                span.set_attributes(**{attrs.LLMOPS_THINKING_TYPE: thinking.get("type")})

            t0 = _now_ms()
            try:
                if provider == "ollama":
                    (raw, text, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
                     stop_reason, response_model, t_first_token, t_end) = self._call_ollama(
                        base_url=base_url, model=model, messages=messages, system=system, max_tokens=max_tokens
                    )
                else:
                    (raw, text, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens,
                     stop_reason, response_model, t_first_token, t_end) = self._call_anthropic(
                        model=model, messages=messages, system=system, max_tokens=max_tokens,
                        thinking=thinking, output_config=output_config, extra_kwargs=kwargs,
                    )
            except Exception as exc:
                span.set_error(str(exc))
                self.status = "error"
                self.error_type = _classify_error(exc, provider)
                raise

            cost_usd = calculate_cost(model, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens)
            ttft_ms = int((t_first_token or t_end) - t0)
            latency_ms = int(t_end - t0)
            gen_ms = max(t_end - (t_first_token or t0), 1.0)
            tokens_per_sec = output_tokens / (gen_ms / 1000.0)

            span.set_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cost_usd=cost_usd,
            )
            span.set_attributes(**{
                attrs.GEN_AI_RESPONSE_MODEL: response_model,
                attrs.GEN_AI_RESPONSE_FINISH_REASONS: [stop_reason],
                attrs.GEN_AI_USAGE_INPUT_TOKENS: input_tokens,
                attrs.GEN_AI_USAGE_OUTPUT_TOKENS: output_tokens,
                attrs.LLMOPS_USAGE_CACHE_READ_TOKENS: cache_read_tokens,
                attrs.LLMOPS_USAGE_CACHE_CREATION_TOKENS: cache_creation_tokens,
                attrs.LLMOPS_COST_USD: cost_usd,
                attrs.LLMOPS_TTFT_MS: ttft_ms,
                attrs.LLMOPS_TOKENS_PER_SEC: round(tokens_per_sec, 2),
            })

            return LLMCallResult(
                message=raw,
                text=text,
                ttft_ms=ttft_ms,
                latency_ms=latency_ms,
                tokens_per_sec=round(tokens_per_sec, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cost_usd=cost_usd,
                stop_reason=stop_reason,
                provider=provider,
            )

    def _primary_llm_span(self) -> _SpanRecord | None:
        """The span that actually produced the result shown to the user —
        the last successful llm/judge call, so a failed-then-fallback
        sequence attributes model_id/ttft/tokens_per_sec to the call that
        won, not the one that failed first."""
        candidates = [s for s in self.spans if s.span_kind in ("llm", "judge")]
        for s in reversed(candidates):
            if s.status == "ok":
                return s
        return candidates[-1] if candidates else None

    def to_payload(self) -> dict:
        primary = self._primary_llm_span()
        input_tokens = sum(s.input_tokens for s in self.spans)
        output_tokens = sum(s.output_tokens for s in self.spans)
        cache_read_tokens = sum(s.cache_read_tokens for s in self.spans)
        cache_creation_tokens = sum(s.cache_creation_tokens for s in self.spans)
        cost_usd = sum(s.cost_usd for s in self.spans)
        latency_ms = int(((self.ended_at or time.time()) - self.started_at) * 1000)
        return {
            "trace": {
                "trace_id": self.trace_id,
                "name": self.name,
                "started_at": _iso(self.started_at),
                "ended_at": _iso(self.ended_at) if self.ended_at else None,
                "latency_ms": latency_ms,
                "ttft_ms": primary.attributes.get(attrs.LLMOPS_TTFT_MS) if primary else None,
                "tokens_per_sec": primary.attributes.get(attrs.LLMOPS_TOKENS_PER_SEC) if primary else None,
                "status": self.status,
                "error_type": self.error_type,
                "retry_count": self.retry_count,
                "model_id": primary.attributes.get(attrs.GEN_AI_REQUEST_MODEL) if primary else None,
                "prompt_version_id": self.prompt_version_id,
                "dataset_item_id": self.dataset_item_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cost_usd": cost_usd,
                "is_synthetic": False,
                "tags": self.tags,
                "attributes": {},
            },
            "spans": [s.to_payload() for s in self.spans],
        }


class TraceClient:
    """Entry point for instrumenting LLM calls and shipping traces."""

    def __init__(
        self,
        backend_url: str,
        anthropic_client: anthropic.Anthropic | None = None,
        ship: bool = True,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.anthropic = anthropic_client or anthropic.Anthropic()
        self.ship = ship
        self._http = httpx.Client(timeout=10.0)
        self.ollama_http = httpx.Client(timeout=120.0)

    @contextmanager
    def trace(
        self,
        name: str,
        *,
        prompt_version_id: int | None = None,
        dataset_item_id: int | None = None,
        tags: dict | None = None,
        on_complete=None,
    ) -> Iterator[TraceContext]:
        ctx = TraceContext(self, name, prompt_version_id, dataset_item_id, tags)
        try:
            yield ctx
        except Exception as exc:
            if ctx.status == "ok":
                ctx.status = "error"
                ctx.error_type = _classify_error(exc)
            raise
        finally:
            ctx.ended_at = time.time()
            payload = ctx.to_payload()
            if on_complete is not None:
                on_complete(payload)
            elif self.ship:
                self._ship_sync(payload)

    def _ship_sync(self, payload: dict) -> None:
        try:
            self._http.post(f"{self.backend_url}/api/traces/ingest", json=payload)
        except httpx.HTTPError:
            pass

    def ship_async_httpx(self, payload: dict) -> None:
        """Ship without raising — used from FastAPI BackgroundTasks."""
        self._ship_sync(payload)
