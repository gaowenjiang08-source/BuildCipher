"""Configuration management."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    zhipuai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    baidu_api_key: Optional[str] = None
    relay_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_model: str = "claude-3-opus-20240229"
    zhipuai_model: str = "glm-4"
    gemini_model: str = "gemini-1.5-pro"
    deepseek_model: str = "deepseek-chat"
    qwen_model: str = "qwen-plus"
    baidu_model: str = "ernie-4.0-turbo-8k"
    relay_model: str = "gpt-4o-mini"
    # Optional custom endpoints (proxy / self-hosted / gateway)
    openai_base_url: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    zhipuai_base_url: Optional[str] = None
    gemini_base_url: Optional[str] = None
    deepseek_base_url: Optional[str] = "https://api.deepseek.com"
    qwen_base_url: Optional[str] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    baidu_base_url: Optional[str] = None
    relay_base_url: Optional[str] = None
    embedding_model: str = "text-embedding-3-large"

    # Skill Routing (Enterprise)
    # Enable semantic routing (SentenceTransformers) in addition to keywords.
    # Default is False to avoid unexpected model downloads at runtime.
    skill_router_enable_embeddings: bool = False
    skill_router_embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    # Candidate will be considered only when cosine similarity >= min_similarity.
    skill_router_embedding_min_similarity: float = 0.35
    # Relative weight for semantic score when mixing with keyword score.
    skill_router_embedding_weight: float = 0.35
    # Redis cache TTL for `/api/v1/skills/route` responses (seconds).
    skill_route_cache_ttl: int = 1800

    # Database Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "crypto_knowledge"
    database_url: str = "postgresql://postgres:password@localhost:5432/buildtrust"

    # Redis Configuration
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_cache_ttl: int = 3600  # Default cache TTL in seconds

    # Application Settings
    debug: bool = True
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Generation Settings
    max_scheme_variants: int = 5
    default_timeout: int = 60
    enable_caching: bool = True
    same_run_retry_budget_default: int = 1

    # Security
    api_key_enabled: bool = False
    api_key: Optional[str] = None

    # BuildCipher localhost state. The BuildTrust name remains an accepted env alias.
    buildcipher_governance_database_path: str = Field(
        default=".cache/buildcipher/governance.sqlite3",
        validation_alias=AliasChoices(
            "BUILDCIPHER_GOVERNANCE_DATABASE_PATH",
            "BUILDTRUST_GOVERNANCE_DATABASE_PATH",
        ),
    )

    @property
    def buildtrust_governance_database_path(self) -> str:
        """Compatibility accessor for integrations authored before the runtime rename."""

        return self.buildcipher_governance_database_path

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env without validation errors


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
