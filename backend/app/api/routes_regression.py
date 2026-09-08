from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models.regression import RegressionTestRun
from app.schemas.regression import RegressionRunCreate, RegressionRunOut
from app.services.regression.runner import run_regression_test
from app.services.trace_client import get_trace_client

router = APIRouter(prefix="/api/regression", tags=["regression"])


def _execute_run_in_background(run_id: int, limit: int | None) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        run_regression_test(run_id, db, get_trace_client(), settings.judge_model, limit)
    except Exception:
        pass  # status already flipped to "error" inside run_regression_test
    finally:
        db.close()


@router.post("/runs", response_model=RegressionRunOut, status_code=201)
def create_regression_run(payload: RegressionRunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run = RegressionTestRun(
        name=payload.name,
        dataset_version_id=payload.dataset_version_id,
        prompt_version_id=payload.prompt_version_id,
        model_id=payload.model_id,
        baseline_run_id=payload.baseline_run_id,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    background_tasks.add_task(_execute_run_in_background, run.id, payload.limit)
    return run


@router.get("/runs", response_model=list[RegressionRunOut])
def list_regression_runs(db: Session = Depends(get_db)):
    return db.execute(select(RegressionTestRun).order_by(RegressionTestRun.started_at.desc())).scalars().all()


@router.get("/runs/{run_id}", response_model=RegressionRunOut)
def get_regression_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(RegressionTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="regression run not found")
    return run


@router.post("/runs/{run_id}/set-baseline", response_model=RegressionRunOut)
def set_baseline(run_id: int, db: Session = Depends(get_db)):
    run = db.get(RegressionTestRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="regression run not found")
    db.execute(
        RegressionTestRun.__table__.update()
        .where(RegressionTestRun.dataset_version_id == run.dataset_version_id)
        .values(is_baseline=False)
    )
    run.is_baseline = True
    db.commit()
    db.refresh(run)
    return run
