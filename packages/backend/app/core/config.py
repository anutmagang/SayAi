from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="SayAi", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    secret_key: str = Field(validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )

    database_url: str = Field(validation_alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    qdrant_url: str | None = Field(default=None, validation_alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, validation_alias="QDRANT_API_KEY")

    cors_origins: str = Field(default="*", validation_alias="CORS_ORIGINS")

    default_llm_model: str = Field(default="gpt-4o-mini", validation_alias="DEFAULT_LLM_MODEL")
    agent_max_steps: int = Field(default=12, validation_alias="AGENT_MAX_STEPS")
    chat_max_tool_rounds: int = Field(default=2, validation_alias="CHAT_MAX_TOOL_ROUNDS")
    session_context_max_messages: int = Field(
        default=40,
        validation_alias="SESSION_CONTEXT_MAX_MESSAGES",
    )
    session_redis_ttl_seconds: int = Field(
        default=60 * 60 * 24 * 7,
        validation_alias="SESSION_REDIS_TTL_SECONDS",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=1536, validation_alias="EMBEDDING_DIMENSIONS")
    rag_chunk_size: int = Field(default=1200, validation_alias="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, validation_alias="RAG_CHUNK_OVERLAP")
    rag_default_top_k: int = Field(default=5, validation_alias="RAG_DEFAULT_TOP_K")

    skill_tool_timeout_seconds: float = Field(
        default=30.0,
        validation_alias="SKILL_TOOL_TIMEOUT_SECONDS",
    )
    skill_http_host_allowlist: str | None = Field(
        default=None,
        validation_alias="SKILL_HTTP_HOST_ALLOWLIST",
    )
    skill_packs_extra_dirs: str | None = Field(
        default=None,
        validation_alias="SKILL_PACKS_EXTRA_DIRS",
    )

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def empty_qdrant_key_none(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
