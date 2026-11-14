from fastapi.testclient import TestClient
from app.main import create_app


def test_cors_allowed_origin(client: TestClient):
    # Default allowed origin: http://localhost:5173
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_disallowed_origin(client: TestClient):
    # Untrusted origin should not receive allow-origin header matching the untrusted origin
    response = client.get("/health", headers={"Origin": "http://malicious-site.example.com"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") != "http://malicious-site.example.com"


def test_cors_configurable_via_settings(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("CORS_ORIGINS", "https://demo.example.com, https://app.example.com")
    get_settings.cache_clear()

    custom_app = create_app()
    with TestClient(custom_app) as custom_client:
        resp = custom_client.get("/health", headers={"Origin": "https://demo.example.com"})
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "https://demo.example.com"

        resp_blocked = custom_client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert resp_blocked.headers.get("access-control-allow-origin") != "http://localhost:5173"

    get_settings.cache_clear()
