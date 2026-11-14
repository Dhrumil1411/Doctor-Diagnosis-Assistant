from fastapi.testclient import TestClient


def test_health_endpoint_public(client: TestClient):
    # No Authorization header provided
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "up"
    assert "app_env" in data
