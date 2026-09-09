#!/usr/bin/env python
"""Fire real questions at the running backend's /demo/ask endpoint, producing
genuine (non-synthetic) traces with real latency/TTFT/tokens/cost. Requires
the backend to be running and ANTHROPIC_API_KEY to be set server-side.

Usage:
    python scripts/generate_live_traffic.py --n 3 [--with-eval] [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--base-url", type=str, default="http://localhost:8000")
    parser.add_argument("--with-eval", action="store_true", help="also trigger LLM-judge scoring on each new trace")
    args = parser.parse_args()

    questions = json.loads((ROOT / "seed" / "golden_qa_dataset.json").read_text(encoding="utf-8"))
    sample = random.sample(questions, k=min(args.n, len(questions)))

    client = httpx.Client(timeout=60.0)
    for i, item in enumerate(sample, start=1):
        print(f"[{i}/{len(sample)}] {item['question']}")
        resp = client.post(f"{args.base_url}/demo/ask", json={"question": item["question"]})
        resp.raise_for_status()
        body = resp.json()
        print(f"    trace_id={body['trace_id']}  latency_ms={body['latency_ms']}  cost_usd={body['cost_usd']:.6f}")
        print(f"    answer: {body['answer'][:160]}...")

        if args.with_eval:
            eval_resp = client.post(f"{args.base_url}/api/evals/score-trace/{body['trace_id']}", json={})
            eval_resp.raise_for_status()
            for s in eval_resp.json()["scores"]:
                print(f"    eval[{s['metric_name']}] = {s['score']:.3f} (passed={s['passed']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
