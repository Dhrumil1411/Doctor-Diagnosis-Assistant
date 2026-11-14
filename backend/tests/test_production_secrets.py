import pytest
from app.core.config import Settings, get_settings


def test_production_fails_without_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-only-secret-change-me-0123456789abcdef0123456789abcdef")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="Production configuration error"):
        Settings()

    get_settings.cache_clear()


def test_production_fails_with_placeholder_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-to-a-long-random-string")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="Production configuration error"):
        Settings()

    get_settings.cache_clear()


def test_production_succeeds_with_strong_jwt_secret(monkeypatch):
    strong_secret = "9823f04b8a21d1e679a9502b48d61394bc57193a027e1f4092b781a5c68e14"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", strong_secret)
    get_settings.cache_clear()

    s = Settings()
    assert s.secret_key == strong_secret

    get_settings.cache_clear()


def test_development_allows_default_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    get_settings.cache_clear()

    s = Settings()
    assert "dev-only" in s.secret_key

    get_settings.cache_clear()
