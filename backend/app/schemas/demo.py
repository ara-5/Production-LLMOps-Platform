from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    prompt_version_id: int | None = None
    model_id: str | None = None
    k: int = 5


class SourceOut(BaseModel):
    doc_id: str
    title: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    trace_id: str
    latency_ms: int
    cost_usd: float
