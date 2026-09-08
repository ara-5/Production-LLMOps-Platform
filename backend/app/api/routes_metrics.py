from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import aggregations

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/overview")
def overview(since: datetime | None = None, until: datetime | None = None, db: Session = Depends(get_db)):
    return aggregations.overview_metrics(db, since, until)


@router.get("/latency-timeseries")
def latency_timeseries(bucket: str = Query("1 hour"), since: datetime | None = None, db: Session = Depends(get_db)):
    return aggregations.latency_timeseries(db, bucket, since)


@router.get("/cost-timeseries")
def cost_timeseries(bucket: str = Query("1 day"), since: datetime | None = None, db: Session = Depends(get_db)):
    return aggregations.cost_timeseries(db, bucket, since)


@router.get("/cost-breakdown")
def cost_breakdown_route(
    group_by: str = Query("model_id", pattern="^(model_id|prompt_version_id)$"),
    since: datetime | None = None,
    db: Session = Depends(get_db),
):
    return aggregations.cost_breakdown(db, group_by, since)


@router.get("/errors")
def errors(since: datetime | None = None, limit: int = 50, db: Session = Depends(get_db)):
    return aggregations.recent_errors(db, since, limit)
