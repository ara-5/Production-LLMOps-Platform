"""Factory for the SDK's TraceClient, configured to ship traces back into
this same backend's own ingest API (dogfooding the real ingest contract)."""

from functools import lru_cache

import anthropic
from fastapi import HTTPException
from llmops_sdk import TraceClient

from app.config import get_settings


@lru_cache
def get_trace_client() -> TraceClient:
    settings = get_settings()
    anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    return TraceClient(backend_url=settings.backend_internal_url, anthropic_client=anthropic_client)


def require_anthropic_key() -> None:
    """Fail fast with a clean 503 instead of letting a missing API key
    surface as an unhandled 500 deep inside the Anthropic SDK."""
    if not get_settings().anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY is not configured on the backend — this endpoint makes real Claude API calls.",
        )
