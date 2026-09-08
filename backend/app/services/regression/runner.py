from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from llmops_sdk import TraceClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.datasets import DatasetItem
from app.models.prompts import PromptVersion
from app.models.regression import RegressionTestItem, RegressionTestRun
from app.models.traces import Trace
from app.services.eval_engine.runner import evaluate_dataset_item
from app.services.regression.stats import compare_to_baseline
from app.services.stats_utils import summarize as _summarize


def run_regression_test(
    run_id: int,
    db: Session,
    trace_client: TraceClient,
    judge_model: str,
    limit: int | None = None,
) -> RegressionTestRun:
    run = db.get(RegressionTestRun, run_id)
    if run is None:
        raise ValueError(f"regression run {run_id} not found")

    prompt_version = db.get(PromptVersion, run.prompt_version_id)
    items = (
        db.execute(select(DatasetItem).where(DatasetItem.dataset_version_id == run.dataset_version_id))
        .scalars()
        .all()
    )
    if limit:
        items = items[:limit]

    scores_by_metric: dict[str, list[float]] = defaultdict(list)
    latencies: list[float] = []
    costs: list[float] = []

    try:
        for item in items:
            trace_id, scores = evaluate_dataset_item(
                item, prompt_version, run.model_id, trace_client, db, judge_model
            )
            db.add(RegressionTestItem(regression_test_run_id=run.id, dataset_item_id=item.id, trace_id=trace_id))
            trace = db.execute(select(Trace).where(Trace.trace_id == trace_id)).scalar_one()
            if trace.latency_ms is not None:
                latencies.append(float(trace.latency_ms))
            costs.append(float(trace.cost_usd))
            for s in scores:
                scores_by_metric[s.metric_name].append(float(s.score))
        db.commit()

        per_metric_summary = {name: _summarize(values) for name, values in scores_by_metric.items()}
        latency_summary = _summarize(latencies)
        cost_summary = _summarize(costs)

        current_flat = {name: s["mean"] for name, s in per_metric_summary.items()}
        current_flat["latency_p95_ms"] = latency_summary["p95"]
        current_flat["cost_usd_mean"] = cost_summary["mean"]

        summary: dict = {
            "item_count": len(items),
            "metrics": per_metric_summary,
            "latency_ms": latency_summary,
            "cost_usd": cost_summary,
        }

        if run.baseline_run_id is not None:
            baseline_run = db.get(RegressionTestRun, run.baseline_run_id)
            baseline_flat = {name: s["mean"] for name, s in (baseline_run.summary.get("metrics", {})).items()}
            baseline_flat["latency_p95_ms"] = baseline_run.summary.get("latency_ms", {}).get("p95", 0.0)
            baseline_flat["cost_usd_mean"] = baseline_run.summary.get("cost_usd", {}).get("mean", 0.0)

            result = compare_to_baseline(current_flat, baseline_flat)
            summary["comparison"] = result.to_dict()
            run.status = "passed" if result.passed else "failed"
        else:
            run.status = "passed"

        run.summary = summary
        run.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
    except Exception:
        run.status = "error"
        run.ended_at = datetime.now(timezone.utc)
        db.commit()
        raise
