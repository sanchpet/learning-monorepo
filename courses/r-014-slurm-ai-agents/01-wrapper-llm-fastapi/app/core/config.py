"""Typed application configuration.

Step 2: settings are read from environment variables / `.env` and validated on
first access. A missing required key fails at startup (fail-fast) instead of
blowing up in the middle of a request.
"""

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_file is for local runs; in the container values come from the environment.
    # extra="ignore" — unrelated env vars must not break validation.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Intent LLM Wrapper"
    app_version: str = "0.1.0"
    app_env: str = "local"

    # Required field with no default: if the env var is missing, Pydantic raises
    # ValidationError. SecretStr keeps the value out of logs and repr.
    openrouter_api_key: SecretStr = Field(
        description="OpenRouter key, taken from the OPENROUTER_API_KEY environment variable.",
    )
    openrouter_base_url: AnyHttpUrl = Field(default="https://openrouter.ai/api/v1")
    openrouter_model: str = "openai/gpt-4o-mini"

    request_timeout_seconds: float = 60.0

    @field_validator("openrouter_api_key")
    @classmethod
    def _key_not_blank(cls, value: SecretStr) -> SecretStr:
        # An empty string (OPENROUTER_API_KEY=) technically "exists" but is a clear
        # misconfiguration — catch it at startup too.
        if not value.get_secret_value().strip():
            raise ValueError("OPENROUTER_API_KEY is set but empty")
        return value


@lru_cache
def get_settings() -> Settings:
    # lru_cache: settings are read and validated once per process.
    return Settings()  # type: ignore[call-arg]  # values come from the environment
