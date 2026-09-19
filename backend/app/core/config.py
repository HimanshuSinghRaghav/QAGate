"""Single source of truth for runtime configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://qa:qa@localhost:5433/qa_gate"

    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-sonnet-4.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_enabled: bool = True
    llm_timeout_seconds: int = 45

    confidence_threshold: float = 0.80
    human_sample_rate: float = 0.05
    deterministic_sampling: bool = True

    estimated_words_per_second: float = 2.6

    @property
    def llm_available(self) -> bool:
        return self.llm_enabled and bool(self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
