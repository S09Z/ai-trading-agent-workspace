from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "alphaops"
    postgres_user: str = "alphaops"
    postgres_password: str

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "alphaops_memory"

    # ── Redis / Celery ─────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    @computed_field
    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @computed_field
    @property
    def celery_result_backend(self) -> str:
        return self.redis_url

    # ── Claude / Anthropic ─────────────────────────────────────────────────────
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # ── NewsAPI ────────────────────────────────────────────────────────────────
    news_api_key: str = ""  # optional — falls back to RSS feeds

    # ── Agent schedule intervals (seconds) ────────────────────────────────────
    news_poll_interval: int = 300   # 5 min
    market_poll_interval: int = 60  # 1 min
    risk_poll_interval: int = 900   # 15 min

    # ── Market watchlist ───────────────────────────────────────────────────────
    watchlist: list[str] = Field(
        default=["AAPL", "TSLA", "NVDA", "MSFT", "SPY", "QQQ", "AMZN", "META"]
    )

    # ── Embeddings (sentence-transformers, runs locally — no API key needed) ──
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ── Local LLM (Ollama) ────────────────────────────────────────────────────
    use_local_llm: bool = False           # set True to use Ollama instead of Claude
    local_model: str = "qwen3:latest"     # any model pulled via `ollama pull`
    ollama_url: str = "http://localhost:11434"

    # ── Discord ────────────────────────────────────────────────────────────────
    discord_bot_token: str = ""
    discord_digest_channel_id: str = ""
    discord_bot_channel_id: str = ""

    # ── FastAPI ────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
