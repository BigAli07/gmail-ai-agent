from __future__ import annotations

from pathlib import Path

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gmail_account_email: EmailStr
    digest_recipient_email: EmailStr
    gmail_credentials_file: Path = Path("credentials.json")
    gmail_token_file: Path = Path("token.json")
    database_path: Path = Path("gmail_agent.sqlite3")
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    classification_confidence_threshold: float = Field(default=0.75, ge=0, le=1)
    dry_run: bool = True
    log_level: str = "INFO"
    lock_file: Path = Path("gmail_agent.lock")
    gmail_lookback_days: int = Field(default=2, ge=1, le=30)
    max_messages_per_run: int = Field(default=200, ge=1, le=500)

    @field_validator("gmail_account_email", "digest_recipient_email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value
