from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://llmops:llmops@localhost:5432/llmops"
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-5"
    judge_model: str = "claude-opus-5"
    backend_internal_url: str = "http://localhost:8000"

    # Local Ollama fallback: if Claude is unreachable (no API key, rate
    # limited, network error) the demo RAG app can fall back to a local
    # Ollama model so the pipeline still produces an answer. Off by default
    # in judge/regression paths — LLM-as-judge quality depends on using a
    # strong frontier model, so those endpoints still require a real key.
    enable_ollama_fallback: bool = False
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.2:3b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
