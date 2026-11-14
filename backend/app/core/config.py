import os
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-only-secret-change-me-0123456789abcdef0123456789abcdef"
    jwt_secret: str | None = None
    access_token_expire_minutes: int = 480
    database_url: str = "postgresql+psycopg://dda:dda@localhost:5432/dda"
    model_artifacts_dir: Path = REPO_ROOT / "ml" / "artifacts"

    llm_provider_chain: str = "groq,openrouter"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-lightning:free"
    llm_timeout_seconds: float = 60.0
    llm_max_tokens: int = 1500
    reason_cache_size: int = 500

    # Rate Limiting (SlowAPI)
    rate_limit_predict: str = "60/minute"
    rate_limit_reason: str = "30/minute"
    rate_limit_note_extract: str = "30/minute"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("sqlite:///"):
            path_part = v[len("sqlite:///"):]
            p = Path(path_part)
            if not p.is_absolute():
                resolved = (REPO_ROOT / p).resolve()
                return f"sqlite:///{resolved.as_posix()}"
            elif not p.exists() and "dda.db" in path_part:
                fallback_db = (REPO_ROOT / "backend" / "dda.db").resolve()
                if fallback_db.exists():
                    return f"sqlite:///{fallback_db.as_posix()}"
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        # Allow JWT_SECRET to configure secret_key
        raw_jwt_secret = self.jwt_secret or os.getenv("JWT_SECRET")
        if raw_jwt_secret:
            self.secret_key = raw_jwt_secret

        placeholder_secrets = {
            "",
            "dev-only-secret-change-me-0123456789abcdef0123456789abcdef",
            "change-me-to-a-long-random-string",
            "change-this-in-production-please-use-a-strong-secret",
            "secret",
            "dev-secret",
            "changeme",
        }

        if self.app_env.lower() == "production":
            sec = (self.secret_key or "").strip()
            if (
                not sec
                or sec in placeholder_secrets
                or "change-me" in sec.lower()
                or "dev-only" in sec.lower()
            ):
                raise ValueError(
                    "Production configuration error: JWT_SECRET (or SECRET_KEY) is missing or set to an insecure default placeholder. "
                    "Set a secure, random secret (at least 32 characters) for production."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
