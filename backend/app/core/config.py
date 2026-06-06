from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "LegalEasier Backend"
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    debug: bool = Field(default=False, validation_alias="DEBUG")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/legaleasier",
        validation_alias="DATABASE_URL",
    )
    firebase_credentials_path: str = Field(default="", validation_alias="FIREBASE_CREDENTIALS_PATH")
    firebase_web_api_key: str = Field(default="", validation_alias="FIREBASE_WEB_API_KEY")
    claude_api_key: str = Field(default="", validation_alias="CLAUDE_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    secret_key: str = Field(default="change-me", validation_alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", validation_alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    nlp_service_url: AnyHttpUrl = Field(default="http://localhost:8001", validation_alias="NLP_SERVICE_URL")
    storage_root: str = Field(default="storage", validation_alias="STORAGE_ROOT")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, bool) or value is None:
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
