import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


def test_predict_rate_limit_429(client: TestClient, doctor_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_predict", "2/minute")
    limiter.reset()

    payload = {"symptoms": ["fever", "cough"], "top_k": 3}

    # Request 1: OK
    res1 = client.post("/api/predict", json=payload, headers=doctor_headers)
    assert res1.status_code == 200

    # Request 2: OK
    res2 = client.post("/api/predict", json=payload, headers=doctor_headers)
    assert res2.status_code == 200

    # Request 3: 429 Too Many Requests
    res3 = client.post("/api/predict", json=payload, headers=doctor_headers)
    assert res3.status_code == 429
    assert "Too Many Requests" in res3.text or res3.status_code == 429


def test_note_extractor_rate_limit_429(client: TestClient, doctor_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_note_extract", "1/minute")
    limiter.reset()

    payload = {"raw_note": "Patient presents with headache and mild fever for 2 days."}

    # Request 1: OK
    res1 = client.post("/api/clinical-notes/extract", json=payload, headers=doctor_headers)
    assert res1.status_code == 200

    # Request 2: 429 Too Many Requests
    res2 = client.post("/api/clinical-notes/extract", json=payload, headers=doctor_headers)
    assert res2.status_code == 429


def test_reason_rate_limit_429(client: TestClient, doctor_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_reason", "1/minute")
    limiter.reset()

    # Create patient & visit with present symptoms
    p_resp = client.post(
        "/api/patients",
        json={"full_name": "Rate Limit Test Patient", "date_of_birth": "1990-01-01"},
        headers=doctor_headers,
    )
    assert p_resp.status_code == 201
    patient_id = p_resp.json()["id"]

    v_resp = client.post(
        "/api/visits",
        json={"patient_id": patient_id, "visit_type": "new", "chief_complaint": "Persistent cough"},
        headers=doctor_headers,
    )
    assert v_resp.status_code == 201
    visit_id = v_resp.json()["id"]

    # Add symptoms
    client.put(
        f"/api/visits/{visit_id}/symptoms",
        json=[{"name": "cough", "status": "present"}],
        headers=doctor_headers,
    )

    # Mock LLM reasoning response
    mock_reason = (
        {
            "summary": "Patient presenting with cough.",
            "differentials": [
                {
                    "rank": 1,
                    "condition": "Acute Bronchitis",
                    "likelihood": "high",
                    "supporting_findings": ["cough"],
                    "notes": "Common presentation",
                }
            ],
            "red_flags": [],
            "suggested_next_steps": ["Chest X-Ray"],
            "questions_for_patient": ["How long has it lasted?"],
        },
        "groq",
    )
    from app.services.llm import LLMClient
    monkeypatch.setattr(LLMClient, "chat_json", lambda self, msgs: mock_reason)

    # Request 1: OK
    res1 = client.post("/api/reason", json={"visit_id": visit_id}, headers=doctor_headers)
    assert res1.status_code == 200

    # Request 2: 429 Too Many Requests
    res2 = client.post("/api/reason", json={"visit_id": visit_id}, headers=doctor_headers)
    assert res2.status_code == 429


def test_get_real_client_ip_unit():
    from starlette.datastructures import Headers
    from app.core.limiter import get_real_client_ip

    class DummyRequest:
        def __init__(self, headers: dict, client_host: str = "127.0.0.1"):
            self.headers = Headers(headers)
            self.client = type("Client", (), {"host": client_host})()

    # When X-Forwarded-For is present with multiple IPs
    req1 = DummyRequest({"x-forwarded-for": "203.0.113.195, 70.41.3.18, 150.172.238.178"})
    assert get_real_client_ip(req1) == "203.0.113.195"

    # When X-Forwarded-For is present with single IP
    req2 = DummyRequest({"x-forwarded-for": "198.51.100.42"})
    assert get_real_client_ip(req2) == "198.51.100.42"

    # When X-Forwarded-For is absent, falls back to remote address
    req3 = DummyRequest({}, client_host="10.0.0.5")
    assert get_real_client_ip(req3) == "10.0.0.5"


def test_rate_limit_uses_x_forwarded_for(client: TestClient, doctor_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_predict", "1/minute")
    limiter.reset()

    payload = {"symptoms": ["headache"], "top_k": 2}

    headers_ip1 = {**doctor_headers, "X-Forwarded-For": "198.51.100.10, 10.0.0.1"}
    headers_ip2 = {**doctor_headers, "X-Forwarded-For": "198.51.100.20, 10.0.0.1"}

    # IP1 Request 1: OK
    res1 = client.post("/api/predict", json=payload, headers=headers_ip1)
    assert res1.status_code == 200

    # IP1 Request 2: Rate limited (429)
    res2 = client.post("/api/predict", json=payload, headers=headers_ip1)
    assert res2.status_code == 429

    # IP2 Request 1: OK (different client IP is not rate limited)
    res3 = client.post("/api/predict", json=payload, headers=headers_ip2)
    assert res3.status_code == 200

