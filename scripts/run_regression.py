#!/usr/bin/env python
"""CLI entry point for running a regression test — the "CI gate for prompts".

Runs a dataset against a given prompt version + model, scores every item
with the eval engine (LLM-as-judge + retrieval metrics), and if a baseline
run is given, compares against it and exits non-zero on regression. Makes
real Anthropic API calls (one RAG answer + up to 3 judge calls per dataset
item) — requires ANTHROPIC_API_KEY. Use --limit for a cheap smoke run first.

Usage:
    python scripts/run_regression.py --dataset-version-id 1 --prompt-version-id 2 \
        --model claude-sonnet-5 --baseline-run-id 1 --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "sdk"))

from app.config import get_settings
from app.db import SessionLocal
from app.models.regression import RegressionTestRun
from app.services.regression.runner import run_regression_test
from app.services.trace_client import get_trace_client


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-version-id", type=int, required=True)
    parser.add_argument("--prompt-version-id", type=int, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--baseline-run-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None, help="only score the first N dataset items (cost control)")
    parser.add_argument("--name", type=str, default="cli regression run")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.anthropic_api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set. This script makes real Claude API calls.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        run = RegressionTestRun(
            name=args.name,
            dataset_version_id=args.dataset_version_id,
            prompt_version_id=args.prompt_version_id,
            model_id=args.model,
            baseline_run_id=args.baseline_run_id,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        print(f"Running regression test #{run.id} ({args.name})...")
        run = run_regression_test(run.id, db, get_trace_client(), settings.judge_model, args.limit)

        print(f"\nStatus: {run.status.upper()}")
        print(f"Items scored: {run.summary.get('item_count', 0)}")
        for metric, stats in run.summary.get("metrics", {}).items():
            print(f"  {metric:<16} mean={stats['mean']:.4f}  p50={stats['p50']:.4f}  p95={stats['p95']:.4f}")

        comparison = run.summary.get("comparison")
        if comparison:
            print("\nBaseline comparison:")
            for c in comparison["comparisons"]:
                mark = "PASS" if c["passed"] else "FAIL"
                print(f"  [{mark}] {c['metric_name']:<16} baseline={c['baseline']:.4f}  current={c['current']:.4f}  delta={c['delta']:+.4f}  threshold={c['threshold']:+.4f}")

        return 0 if run.status == "passed" else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
