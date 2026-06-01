"""Application configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global DUALEXIS runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="DUALEXIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DUALEXIS"
    environment: str = Field(default="development", pattern=r"^(development|staging|production)$")
    debug: bool = False

    # Edge processing
    edge_buffer_ttl_seconds: int = Field(default=30, ge=1, le=300)
    max_concurrent_perception_streams: int = Field(default=4, ge=1, le=64)

    # Privacy defaults (strict by default)
    allow_persistent_media: bool = False
    allow_biometric_features: bool = False
    allow_identity_linking: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)

    # Reasoning (local LLM placeholder)
    reasoning_enabled: bool = True
    reasoning_model_path: str | None = None

    # Audit
    audit_enabled: bool = True
    audit_retention_days: int = Field(default=90, ge=1, le=3650)
