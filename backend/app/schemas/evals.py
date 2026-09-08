from pydantic import BaseModel


class ScoreTraceRequest(BaseModel):
    metrics: list[str] = ["hallucination", "faithfulness", "relevance"]


class EvalScoreResult(BaseModel):
    metric_name: str
    score: float
    passed: bool | None
    reasoning: str | None


class ScoreTraceResponse(BaseModel):
    trace_id: str
    scores: list[EvalScoreResult]


class MetricSummary(BaseModel):
    metric_name: str
    count: int
    mean: float
    p50: float
    p95: float
    pass_rate: float | None


class EvalSummaryResponse(BaseModel):
    metrics: list[MetricSummary]
