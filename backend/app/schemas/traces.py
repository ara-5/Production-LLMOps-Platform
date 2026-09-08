from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpanIn(BaseModel):
    span_id: str
    parent_span_id: str | None = None
    name: str
    span_kind: str
    started_at: datetime
    ended_at: datetime | None = None
    latency_ms: int | None = None
    status: str = "ok"
    status_message: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    attributes: dict = {}


class TraceIn(BaseModel):
    trace_id: str
    name: str
    started_at: datetime
    ended_at: datetime | None = None
    latency_ms: int | None = None
    ttft_ms: int | None = None
    tokens_per_sec: float | None = None
    status: str = "ok"
    error_type: str | None = None
    retry_count: int = 0
    model_id: str | None = None
    prompt_version_id: int | None = None
    dataset_item_id: int | None = None
    session_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0
    is_synthetic: bool = False
    tags: dict = {}
    attributes: dict = {}


class IngestPayload(BaseModel):
    trace: TraceIn
    spans: list[SpanIn] = []


class SpanOut(SpanIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EvalScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    metric_name: str
    score: float
    passed: bool | None
    reasoning: str | None
    judge_model: str | None
    judge_trace_id: str | None
    created_at: datetime


class TraceListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    trace_id: str
    name: str
    started_at: datetime
    latency_ms: int | None
    ttft_ms: int | None
    status: str
    error_type: str | None
    model_id: str | None
    prompt_version_id: int | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    is_synthetic: bool


class TraceDetail(TraceListItem):
    ended_at: datetime | None
    tokens_per_sec: float | None
    retry_count: int
    dataset_item_id: int | None
    cache_read_tokens: int
    cache_creation_tokens: int
    tags: dict
    attributes: dict
    spans: list[SpanOut] = []
    eval_scores: list[EvalScoreOut] = []


class TraceListResponse(BaseModel):
    items: list[TraceListItem]
    total: int
    limit: int
    offset: int
