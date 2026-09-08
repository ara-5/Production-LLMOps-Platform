from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://llmops:llmops@localhost:5432/llmops"
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-5"
    judge_model: str = "claude-opus-5"
    backend_internal_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
