# Production LLMOps Platform

A self-hosted LLM observability, evaluation, and regression-testing platform for Claude-powered applications — the kind of system a team running an LLM feature in production needs in 2026/2027: full request tracing, cost/latency/token accounting, LLM-as-judge quality scoring, retrieval-quality metrics, prompt/model version tracking, and a CI-style regression gate for prompt changes.

It ships as a working system, not a slide deck: a real instrumentation SDK, a FastAPI backend with a Postgres schema modeled on OpenTelemetry's GenAI semantic conventions, an LLM-as-judge evaluation engine using structured outputs, a regression-testing workflow with statistical baseline comparison, an instrumented demo RAG application, and a React dashboard — all wired together and runnable with `docker compose up`.

## What it demonstrates

| Requirement | Where |
|---|---|
| **Latency** (incl. TTFT, tokens/sec, p50/p95/p99) | Captured per-call in [`sdk/llmops_sdk/client.py`](sdk/llmops_sdk/client.py) via streaming; aggregated in [`/api/metrics/*`](backend/app/services/aggregations.py) |
| **Token usage** (input/output/cache read/cache write) | Recorded on every trace & span; surfaced on the Overview and Costs pages |
| **Cost** | Computed from a real per-model pricing table in [`sdk/llmops_sdk/pricing.py`](sdk/llmops_sdk/pricing.py), including prompt-cache discount/premium rates |
| **Hallucination** | LLM-as-judge (Claude Opus 5, structured JSON output) in [`judges.py`](backend/app/services/eval_engine/judges.py) |
| **Faithfulness** | LLM-as-judge groundedness scoring against retrieved context |
| **Relevance** | LLM-as-judge answer-relevance scoring |
| **Retrieval quality** | Deterministic precision@k / recall@k / MRR / NDCG in [`retrieval_metrics.py`](backend/app/services/eval_engine/retrieval_metrics.py) |
| **Failed requests** | First-class `status` / `error_type` / `retry_count` columns on every trace, classified by exception type (timeout / rate limit / API error / connection error) |
| **Prompt versions** | Append-only prompt registry with diffing and rollback ([`routes_prompts.py`](backend/app/api/routes_prompts.py)) |
| **Model versions** | Every trace records the exact `model_id` used; regression tests compare across model/prompt combinations |
| **Evaluation datasets** | Versioned golden Q&A datasets with expected answers + expected retrieval doc IDs |
| **Regression testing** | Run a dataset against a prompt/model version, score it, and compare to a stored baseline with per-metric pass/fail thresholds — a CLI exit code makes it usable as a CI gate ([`scripts/run_regression.py`](scripts/run_regression.py)) |

## Architecture

```mermaid
flowchart LR
    subgraph Demo["Instrumented demo app"]
        RAG["RAG pipeline\n(TF-IDF retrieval + Claude)"]
    end

    subgraph SDK["llmops_sdk"]
        TC["TraceClient\n(trace/span capture, cost calc)"]
    end

    subgraph Backend["FastAPI backend"]
        Ingest["/api/traces/ingest"]
        Query["Query & aggregation APIs"]
        EvalEngine["Eval engine\n(LLM judges + retrieval metrics)"]
        Regression["Regression runner"]
    end

    DB[("Postgres\ntraces · spans · prompts\ndatasets · eval_scores\nregression runs")]

    UI["React dashboard"]

    Claude["Claude API\n(Opus 5 / Sonnet 5 / Haiku 4.5)"]

    RAG -->|"llm_call()"| TC
    TC -->|"streams calls"| Claude
    TC -->|"POST trace+spans"| Ingest
    Ingest --> DB
    Query --> DB
    EvalEngine -->|"judge calls via TraceClient"| Claude
    EvalEngine --> DB
    Regression --> EvalEngine
    Regression --> DB
    UI -->|"REST"| Query
    UI -->|"REST"| EvalEngine
    UI -->|"REST"| Regression
```

Every LLM call — including judge calls — flows through the same `TraceClient`, so judge cost and latency show up in the same observability data as the application traffic they're grading. The demo app, the eval engine, and the regression runner are all just callers of that one instrumentation path; nothing is mocked or faked in the pipeline itself.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0, Alembic, Postgres (JSONB for span attributes + first-class indexed columns for what actually gets queried/aggregated)
- **Instrumentation SDK:** a standalone Python package (`sdk/llmops_sdk`) wrapping the official `anthropic` SDK's streaming Messages API
- **Eval engine:** structured-output LLM-as-judge (`output_config.format`) + pure deterministic retrieval metrics
- **Frontend:** React + TypeScript + Vite, `@tanstack/react-query`, Recharts, a validated CVD-safe dark-mode color system
- **Demo app:** a TF-IDF-retrieval RAG assistant over a fixed 32-document knowledge base for a fictional company ("Northwind Cloud"), so retrieval-quality metrics have real ground truth to score against
- **Infra:** Docker Compose (Postgres + backend + frontend); no message queue — eval/regression jobs run via FastAPI `BackgroundTasks`, which is enough at demo dataset sizes

## Quickstart

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY if you want to exercise live endpoints
# (the dashboard itself is fully populated from synthetic seed data with no key)

docker compose up -d --build
docker compose exec backend python /app/scripts/seed_data.py --reset
```

Open the dashboard at **http://localhost:5173** — 14 days of realistic synthetic traffic (traces, evals, a baseline regression run) will already be there. The API is at **http://localhost:8000** (interactive docs at `/docs`).

### Exercising the live paths (requires `ANTHROPIC_API_KEY`)

```bash
# Ask the demo RAG app a real question — produces a genuine (non-synthetic) trace
python scripts/generate_live_traffic.py --n 3 --with-eval --base-url http://localhost:8000

# Run a real regression test (RAG answer + up to 3 judge calls per dataset item)
python scripts/run_regression.py --dataset-version-id 1 --prompt-version-id 1 \
    --model claude-sonnet-5 --baseline-run-id 1 --limit 5
```

`run_regression.py` exits `0` on pass and `1` on regression, so it drops straight into a CI pipeline as a gate on prompt/model changes.

## Local development (without Docker)

```bash
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate on macOS/Linux
pip install -r backend/requirements.txt
pip install -e ./sdk

docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg://llmops:llmops@localhost:5432/llmops
cd backend && alembic upgrade head && cd ..

uvicorn app.main:app --app-dir backend --reload   # http://localhost:8000

cd frontend && npm install && npm run dev          # http://localhost:5173
```

## Tests

```bash
pip install -r backend/requirements.txt pytest
DATABASE_URL=postgresql+psycopg://llmops:llmops@localhost:5432/llmops \
    pytest backend/tests sdk/tests -v
```

31 tests covering: cost calculation against the pricing table (including cache read/write rates), retrieval-quality metrics against hand-computed fixtures, regression baseline-comparison threshold logic, the SDK's trace/span capture against a mocked Anthropic stream, and the traces ingest/query API end-to-end against a real Postgres instance. `.github/workflows/ci.yml` runs the same suite plus a frontend type-check/build against a Postgres service container — it's set to manual trigger (`workflow_dispatch`) rather than running on every push, so it's there to run on demand from the Actions tab without consuming CI minutes automatically.

## Project layout

```
backend/        FastAPI app: models, API routes, eval engine, regression runner, migrations, tests
sdk/            llmops_sdk — the instrumentation SDK (pricing + TraceClient), installable standalone
demo_app/       The instrumented RAG demo application (TF-IDF retriever + fixed corpus)
frontend/       React + TypeScript dashboard
scripts/        seed_data.py, generate_live_traffic.py, run_regression.py (CLI)
seed/           Golden Q&A dataset used for evaluation and regression testing
```

## Design notes

- **Trace/span schema follows OpenTelemetry's GenAI semantic conventions** (`gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.*`, ...) where they exist, with `llmops.*` extension attributes for fields not yet standardized (cost, TTFT, retrieval doc IDs, thinking/effort). This is the direction the industry has converged on for LLM observability — building on top of it rather than a bespoke schema means the data model would plug into a real OTel collector with minimal translation.
- **Prompt and dataset registries are append-only.** Rollback creates a new version pointing at old content rather than mutating history, so a trace's `prompt_version_id` always resolves to the exact template that produced it.
- **Judge calls are traced like any other LLM call.** They're not a side channel — they go through the same `TraceClient`, so "how much do evals cost" is answerable from the same data as "how much does the product cost."
- **Regression testing treats prompt/model changes like code changes**: run the golden dataset, score it, diff against a baseline on a per-metric threshold, fail the build if quality or latency regressed beyond it. This is the "eval-driven development" pattern, expressed as a CLI with a real exit code rather than a dashboard you have to remember to check.

## License

MIT — see [LICENSE](LICENSE).
