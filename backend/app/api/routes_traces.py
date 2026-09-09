from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.traces import Span, Trace
from app.schemas.traces import IngestPayload, SpanOut, TraceDetail, TraceListResponse

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.post("/ingest", status_code=201)
def ingest_trace(payload: IngestPayload, db: Session = Depends(get_db)):
    existing = db.execute(select(Trace).where(Trace.trace_id == payload.trace.trace_id)).scalar_one_or_none()
    if existing is not None:
        return {"trace_id": existing.trace_id, "status": "already_ingested"}

    trace = Trace(**payload.trace.model_dump())
    db.add(trace)
    for span_in in payload.spans:
        db.add(Span(trace_id=payload.trace.trace_id, **span_in.model_dump()))
    db.commit()
    return {"trace_id": trace.trace_id, "status": "ingested"}


@router.get("", response_model=TraceListResponse)
def list_traces(
    status: str | None = None,
    model_id: str | None = None,
    prompt_version_id: int | None = None,
    is_synthetic: bool | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Trace)
    count_stmt = select(func.count()).select_from(Trace)
    if status:
        stmt = stmt.where(Trace.status == status)
        count_stmt = count_stmt.where(Trace.status == status)
    if model_id:
        stmt = stmt.where(Trace.model_id == model_id)
        count_stmt = count_stmt.where(Trace.model_id == model_id)
    if prompt_version_id is not None:
        stmt = stmt.where(Trace.prompt_version_id == prompt_version_id)
        count_stmt = count_stmt.where(Trace.prompt_version_id == prompt_version_id)
    if is_synthetic is not None:
        stmt = stmt.where(Trace.is_synthetic == is_synthetic)
        count_stmt = count_stmt.where(Trace.is_synthetic == is_synthetic)

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(Trace.started_at.desc()).limit(limit).offset(offset)).scalars().all()
    return TraceListResponse(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{trace_id}", response_model=TraceDetail)
def get_trace(trace_id: str, db: Session = Depends(get_db)):
    trace = db.execute(select(Trace).where(Trace.trace_id == trace_id)).scalar_one_or_none()
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace


@router.get("/{trace_id}/spans", response_model=list[SpanOut])
def get_trace_spans(trace_id: str, db: Session = Depends(get_db)):
    spans = db.execute(select(Span).where(Span.trace_id == trace_id).order_by(Span.started_at)).scalars().all()
    return spans
