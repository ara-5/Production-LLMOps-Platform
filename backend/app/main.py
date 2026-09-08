from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_annotations,
    routes_datasets,
    routes_demo,
    routes_evals,
    routes_metrics,
    routes_prompts,
    routes_regression,
    routes_traces,
)

app = FastAPI(title="Production LLMOps Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(routes_traces.router)
app.include_router(routes_metrics.router)
app.include_router(routes_prompts.router)
app.include_router(routes_datasets.router)
app.include_router(routes_evals.router)
app.include_router(routes_regression.router)
app.include_router(routes_annotations.router)
app.include_router(routes_demo.router)
