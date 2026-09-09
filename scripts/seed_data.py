#!/usr/bin/env python
"""Backfill 14 days of synthetic traffic (traces/spans/eval_scores) plus a
prompt, a golden dataset, and one baseline regression run, so the dashboard
is populated immediately on `docker compose up`. Makes zero real API calls —
everything here is synthetic and free to run.

Usage:
    python scripts/seed_data.py [--reset] [--days 14] [--traces-per-day 120]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "sdk"))

from app.db import SessionLocal
from app.models.datasets import Dataset, DatasetItem, DatasetVersion
from app.models.evals import EvalScore
from app.models.prompts import Prompt, PromptVersion
from app.models.regression import RegressionTestRun
from app.models.traces import Span, Trace
from llmops_sdk.pricing import calculate_cost

random.seed(42)
np.random.seed(42)

MODEL_MIX = [("claude-sonnet-5", 0.60), ("claude-opus-5", 0.25), ("claude-haiku-4-5", 0.15)]
ERROR_TYPES = ["timeout", "rate_limit", "api_error", "connection_error"]

PROMPT_V1 = "Answer the question using only the CONTEXT below.\n\nCONTEXT:\n{context}\n\nQUESTION: {question}"
PROMPT_V2 = (
    "You are a helpful, precise support agent for Northwind Cloud. Using ONLY the CONTEXT below, "
    "answer the QUESTION concisely and cite specific numbers when present.\n\nCONTEXT:\n{context}\n\n"
    "QUESTION: {question}\nANSWER:"
)


def _weighted_model() -> str:
    names, weights = zip(*MODEL_MIX)
    return random.choices(names, weights=weights, k=1)[0]


def reset_seedable_tables(db) -> None:
    print("Resetting seedable tables...")
    db.execute(
        text(
            "TRUNCATE TABLE regression_test_items, regression_test_runs, eval_scores, spans, traces, "
            "dataset_items, dataset_versions, datasets, prompt_versions, prompts RESTART IDENTITY CASCADE"
        )
    )
    db.commit()


def seed_prompt(db) -> tuple[Prompt, PromptVersion, PromptVersion]:
    prompt = Prompt(name="northwind-support-qa")
    db.add(prompt)
    db.flush()
    v1 = PromptVersion(prompt_id=prompt.id, version=1, template=PROMPT_V1, commit_message="baseline")
    v2 = PromptVersion(prompt_id=prompt.id, version=2, template=PROMPT_V2, commit_message="improved wording + concision")
    db.add_all([v1, v2])
    db.commit()
    db.refresh(v1)
    db.refresh(v2)
    print(f"Seeded prompt '{prompt.name}' with versions {v1.version}, {v2.version}")
    return prompt, v1, v2


def seed_dataset(db) -> tuple[Dataset, DatasetVersion, list[DatasetItem]]:
    items_json = json.loads((ROOT / "seed" / "golden_qa_dataset.json").read_text(encoding="utf-8"))
    dataset = Dataset(name="northwind-golden-qa", description="Golden Q&A over the Northwind Cloud product corpus")
    db.add(dataset)
    db.flush()
    version = DatasetVersion(dataset_id=dataset.id, version=1, commit_message="initial 32 items")
    db.add(version)
    db.flush()
    items = []
    for raw in items_json:
        item = DatasetItem(dataset_version_id=version.id, **raw)
        db.add(item)
        items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    print(f"Seeded dataset '{dataset.name}' v{version.version} with {len(items)} items")
    return dataset, version, items


def _sample_eval_score(metric: str) -> tuple[float, bool]:
    """Realistic-looking score: skewed high with an occasional low tail."""
    if random.random() < 0.08:
        score = float(np.random.uniform(0.15, 0.55))
    else:
        score = float(np.clip(np.random.beta(a=8, b=1.5), 0, 1))
    passed = score >= 0.7
    return round(score, 4), passed


def backfill_traces(db, prompt_versions: list[PromptVersion], dataset_items: list[DatasetItem], days: int, traces_per_day: int) -> int:
    now = datetime.now(UTC)
    total = 0
    for day_offset in range(days, 0, -1):
        day_start = now - timedelta(days=day_offset)
        for _ in range(traces_per_day):
            model_id = _weighted_model()
            started_at = day_start + timedelta(seconds=random.uniform(0, 86400))
            latency_ms = int(np.random.lognormal(mean=7.0, sigma=0.4))
            latency_ms = max(150, min(latency_ms, 15000))
            ttft_ms = int(latency_ms * random.uniform(0.12, 0.35))
            is_error = random.random() < 0.05
            status = "error" if is_error else "ok"
            error_type = random.choice(ERROR_TYPES) if is_error else None

            input_tokens = random.randint(400, 3200)
            output_tokens = 0 if is_error else random.randint(80, 900)
            cache_read_tokens = random.choice([0, 0, 0, random.randint(200, 1500)])
            cost_usd = calculate_cost(model_id, input_tokens, output_tokens, cache_read_tokens)
            tokens_per_sec = round(output_tokens / max((latency_ms - ttft_ms) / 1000, 0.05), 2) if not is_error else None

            dataset_item = random.choice(dataset_items) if random.random() < 0.35 else None
            prompt_version = random.choice(prompt_versions)

            trace_id = str(uuid.uuid4())
            ended_at = started_at + timedelta(milliseconds=latency_ms)
            trace = Trace(
                trace_id=trace_id,
                name="rag.answer_question",
                started_at=started_at,
                ended_at=ended_at,
                latency_ms=latency_ms,
                ttft_ms=None if is_error else ttft_ms,
                tokens_per_sec=tokens_per_sec,
                status=status,
                error_type=error_type,
                retry_count=1 if error_type == "rate_limit" else 0,
                model_id=model_id,
                prompt_version_id=prompt_version.id,
                dataset_item_id=dataset_item.id if dataset_item else None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cost_usd=cost_usd,
                is_synthetic=True,
            )
            db.add(trace)

            retrieved_doc_ids = list(dataset_item.expected_retrieval_doc_ids) if dataset_item else []
            db.add(
                Span(
                    trace_id=trace_id,
                    span_id=str(uuid.uuid4()),
                    name="retrieve",
                    span_kind="retrieval",
                    started_at=started_at,
                    ended_at=started_at + timedelta(milliseconds=40),
                    latency_ms=40,
                    status="ok",
                    attributes={"llmops.retrieval.doc_ids": retrieved_doc_ids},
                )
            )
            db.add(
                Span(
                    trace_id=trace_id,
                    span_id=str(uuid.uuid4()),
                    name="llm.generate",
                    span_kind="llm",
                    started_at=started_at + timedelta(milliseconds=40),
                    ended_at=ended_at,
                    latency_ms=latency_ms - 40,
                    status=status,
                    status_message=f"{error_type} after retry" if error_type else None,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_read_tokens=cache_read_tokens,
                    cost_usd=cost_usd,
                    attributes={"gen_ai.request.model": model_id},
                )
            )

            if status == "ok" and random.random() < 0.55:
                for metric in ("hallucination", "faithfulness", "relevance"):
                    score, passed = _sample_eval_score(metric)
                    db.add(
                        EvalScore(
                            trace_id=trace_id,
                            metric_name=metric,
                            score=score,
                            passed=passed,
                            reasoning="synthetic seed data — not a real judge call",
                            judge_model="claude-opus-5",
                        )
                    )
                if dataset_item is not None:
                    for metric in ("precision_at_k", "recall_at_k", "mrr", "ndcg"):
                        score, passed = _sample_eval_score(metric)
                        db.add(EvalScore(trace_id=trace_id, metric_name=metric, score=score, passed=passed))

            total += 1
        db.commit()
        print(f"  seeded day -{day_offset}: {traces_per_day} traces")
    return total


def seed_baseline_regression_run(db, dataset_version: DatasetVersion, prompt_version: PromptVersion, model_id: str) -> RegressionTestRun:
    run = RegressionTestRun(
        name="baseline: v1 prompt on claude-sonnet-5",
        dataset_version_id=dataset_version.id,
        prompt_version_id=prompt_version.id,
        model_id=model_id,
        status="passed",
        is_baseline=True,
        summary={
            "item_count": 32,
            "metrics": {
                "hallucination": {"count": 32, "mean": 0.91, "p50": 0.94, "p95": 0.99},
                "faithfulness": {"count": 32, "mean": 0.89, "p50": 0.92, "p95": 0.98},
                "relevance": {"count": 32, "mean": 0.93, "p50": 0.95, "p95": 0.99},
                "precision_at_k": {"count": 32, "mean": 0.71, "p50": 0.80, "p95": 1.0},
                "recall_at_k": {"count": 32, "mean": 0.85, "p50": 1.0, "p95": 1.0},
                "mrr": {"count": 32, "mean": 0.88, "p50": 1.0, "p95": 1.0},
                "ndcg": {"count": 32, "mean": 0.86, "p50": 0.92, "p95": 1.0},
            },
            "latency_ms": {"count": 32, "mean": 1180.0, "p50": 1050.0, "p95": 2100.0},
            "cost_usd": {"count": 32, "mean": 0.0045, "p50": 0.0041, "p95": 0.0082},
            "note": "seeded baseline summary (synthetic) — run a real regression test via scripts/run_regression.py to replace it",
        },
        started_at=datetime.now(UTC) - timedelta(days=7),
        ended_at=datetime.now(UTC) - timedelta(days=7, minutes=-4),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    print(f"Seeded baseline regression run #{run.id} ({run.status})")
    return run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="truncate seedable tables before seeding")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--traces-per-day", type=int, default=120)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            reset_seedable_tables(db)
        else:
            existing = db.execute(text("SELECT count(*) FROM prompts")).scalar_one()
            if existing > 0:
                print("Prompts already exist — pass --reset to wipe and reseed. Exiting.")
                return

        _, v1, v2 = seed_prompt(db)
        _, dataset_version, items = seed_dataset(db)
        total = backfill_traces(db, [v1, v2], items, args.days, args.traces_per_day)
        seed_baseline_regression_run(db, dataset_version, v1, "claude-sonnet-5")
        print(f"\nDone. Seeded {total} synthetic traces across {args.days} days.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
