from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-only-secret-change-me-0123456789abcdef0123456789abcdef"
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg://dda:dda@localhost:5432/dda"


@lru_cache
def get_settings() -> Settings:
    return Settings()
