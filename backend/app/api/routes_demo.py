from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models.prompts import Prompt, PromptVersion
from app.schemas.demo import AskRequest, AskResponse, SourceOut
from app.services.trace_client import get_trace_client

router = APIRouter(prefix="/demo", tags=["demo"])

DEFAULT_PROMPT_NAME = "northwind-support-qa"


def _resolve_prompt_version(db: Session, prompt_version_id: int | None) -> PromptVersion:
    if prompt_version_id is not None:
        version = db.get(PromptVersion, prompt_version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="prompt version not found")
        return version

    version = (
        db.execute(
            select(PromptVersion)
            .join(Prompt, Prompt.id == PromptVersion.prompt_id)
            .where(Prompt.name == DEFAULT_PROMPT_NAME, PromptVersion.is_active.is_(True))
            .order_by(PromptVersion.version.desc())
        )
        .scalars()
        .first()
    )
    if version is None:
        raise HTTPException(
            status_code=400,
            detail=f"no active prompt version found for '{DEFAULT_PROMPT_NAME}' — run scripts/seed_data.py first",
        )
    return version


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from demo_app.rag_pipeline import answer_question  # local import: keeps demo_app decoupled from api package

    settings = get_settings()
    if not settings.anthropic_api_key and not settings.enable_ollama_fallback:
        raise HTTPException(
            status_code=503,
            detail="Neither ANTHROPIC_API_KEY nor ENABLE_OLLAMA_FALLBACK is configured — this endpoint needs at least one generation provider.",
        )
    prompt_version = _resolve_prompt_version(db, payload.prompt_version_id)
    model_id = payload.model_id or settings.default_model
    trace_client = get_trace_client()

    result = answer_question(
        question=payload.question,
        prompt_version=prompt_version,
        model_id=model_id,
        trace_client=trace_client,
        k=payload.k,
        on_complete=lambda ingest_payload: background_tasks.add_task(trace_client.ship_async_httpx, ingest_payload),
        ollama_fallback_enabled=settings.enable_ollama_fallback,
        ollama_model=settings.ollama_model,
        ollama_base_url=settings.ollama_base_url,
    )

    return AskResponse(
        answer=result.answer,
        sources=[SourceOut(**s) for s in result.sources],
        trace_id=result.trace_id,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
    )
