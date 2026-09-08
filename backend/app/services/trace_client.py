"""Factory for the SDK's TraceClient, configured to ship traces back into
this same backend's own ingest API (dogfooding the real ingest contract)."""

from functools import lru_cache

import anthropic
from llmops_sdk import TraceClient

from app.config import get_settings


@lru_cache
def get_trace_client() -> TraceClient:
    settings = get_settings()
    anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    return TraceClient(backend_url=settings.backend_internal_url, anthropic_client=anthropic_client)
