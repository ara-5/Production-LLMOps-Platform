from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.evals import EvalScore
from app.schemas.evals import (
    EvalScoreResult,
    EvalSummaryResponse,
    MetricSummary,
    ScoreTraceRequest,
    ScoreTraceResponse,
)
from app.schemas.traces import EvalScoreOut
from app.services.eval_engine.runner import evaluate_trace
from app.services.stats_utils import summarize as _summarize
from app.services.trace_client import get_trace_client, require_anthropic_key

router = APIRouter(prefix="/api/evals", tags=["evals"])


@router.post("/score-trace/{trace_id}", response_model=ScoreTraceResponse)
def score_trace(trace_id: str, payload: ScoreTraceRequest, db: Session = Depends(get_db)):
    require_anthropic_key()
    settings = get_settings()
    try:
        scores = evaluate_trace(trace_id, db, get_trace_client(), settings.judge_model, payload.metrics)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScoreTraceResponse(
        trace_id=trace_id,
        scores=[EvalScoreResult(metric_name=s.metric_name, score=float(s.score), passed=s.passed) for s in scores],
    )


@router.get("/scores", response_model=list[EvalScoreOut])
def list_scores(trace_id: str, db: Session = Depends(get_db)):
    return db.execute(select(EvalScore).where(EvalScore.trace_id == trace_id)).scalars().all()


@router.get("/summary", response_model=EvalSummaryResponse)
def eval_summary(db: Session = Depends(get_db)):
    rows = db.execute(select(EvalScore.metric_name, EvalScore.score, EvalScore.passed)).all()
    grouped: dict[str, list] = {}
    for metric_name, score, passed in rows:
        grouped.setdefault(metric_name, []).append((float(score), passed))

    metrics = []
    for metric_name, values in grouped.items():
        scores = [v[0] for v in values]
        pass_flags = [v[1] for v in values if v[1] is not None]
        stats = _summarize(scores)
        metrics.append(
            MetricSummary(
                metric_name=metric_name,
                count=stats["count"],
                mean=stats["mean"],
                p50=stats["p50"],
                p95=stats["p95"],
                pass_rate=(sum(1 for p in pass_flags if p) / len(pass_flags)) if pass_flags else None,
            )
        )
    return EvalSummaryResponse(metrics=metrics)
