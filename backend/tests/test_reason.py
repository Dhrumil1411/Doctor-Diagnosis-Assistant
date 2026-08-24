import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.services.llm import LLMClient, ReasonCache
import app.api.routes.reason as reason_module

GOOD_JSON = json.dumps(
    {
        "summary": "Adult with fever and productive cough.",
        "differentials": [
            {
                "rank": 1,
                "condition": "Community-acquired pneumonia",
                "likelihood": "moderate",
                "supporting_findings": ["fever", "cough"],
                "notes": "consider chest imaging",
            },
            {
                "rank": 2,
                "condition": "Acute bronchitis",
                "likelihood": "low",
                "supporting_findings": ["cough"],
            },
        ],
        "red_flags": ["shortness of breath at rest"],
        "suggested_next_steps": ["Chest X-ray", "CBC"],
        "questions_for_patient": ["Any night sweats?"],
    }
)

FENCED_JSON = f"```json\n{GOOD_JSON}\n```"


@pytest.fixture(autouse=True)
def _isolated_reason_cache():
    reason_module._cache._store.clear()
    yield
    reason_module._cache._store.clear()


def make_settings(monkeypatch, **overrides):
    from app.core.config import Settings

    base = dict(
        llm_provider_chain="groq,openrouter",
        groq_api_key="g-key",
        openrouter_api_key="o-key",
        groq_model="test-groq-model",
        openrouter_model="test-or-model",
    )
    base.update(overrides)
    s = Settings(**base)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    return s


def chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
        request=httpx.Request("POST", "https://example.test/chat/completions"),
    )


def seed_visit(client: TestClient, doctor_headers) -> str:
    pid = client.post(
        "/api/patients",
        json={"full_name": "Reason Ctx", "consent_given": True},
        headers=doctor_headers,
    ).json()["id"]
    vid = client.post(
        "/api/visits",
        json={"patient_id": pid, "visit_type": "new",
              "chief_complaint": "Fever and cough for 4 days"},
        headers=doctor_headers,
    ).json()["id"]
    client.put(
        f"/api/visits/{vid}/symptoms",
        json=[
            {"name": "fever", "status": "present"},
            {"name": "cough", "status": "present"},
            {"name": "vomiting", "status": "absent"},
        ],
        headers=doctor_headers,
    )
    return vid


def test_fallback_on_429(monkeypatch):
    make_settings(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        calls.append(host)
        if host == "api.groq.com":
            return httpx.Response(429, request=request)
        return chat_response(GOOD_JSON)

    client = LLMClient(make_settings(monkeypatch), transport=httpx.MockTransport(handler))
    parsed, provider = client.chat_json([{"role": "user", "content": "case"}])
    assert provider == "openrouter"
    assert parsed["differentials"][0]["condition"] == "Community-acquired pneumonia"
    assert [c.replace("api.", "").split(".")[0] for c in calls] == ["groq", "openrouter"]


def test_all_providers_fail_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    client = LLMClient(make_settings(monkeypatch), transport=httpx.MockTransport(handler))
    try:
        client.chat_json([{"role": "user", "content": "case"}])
        raise AssertionError("should have raised LLMError")
    except Exception as exc:
        assert type(exc).__name__ == "LLMError"
        assert "groq" in str(exc) and "openrouter" in str(exc)


def test_unparseable_json_triggers_fallback(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.groq.com":
            return chat_response("Sorry, I cannot help with that.")
        return chat_response(FENCED_JSON)

    client = LLMClient(make_settings(monkeypatch), transport=httpx.MockTransport(handler))
    parsed, provider = client.chat_json([{"role": "user", "content": "case"}])
    assert provider == "openrouter"
    assert parsed["summary"]


def test_no_keys_configured_clear_error(monkeypatch):
    settings = make_settings(monkeypatch, groq_api_key="", openrouter_api_key="")
    client = LLMClient(settings)
    try:
        client.chat_json([{"role": "user", "content": "case"}])
        raise AssertionError("should have raised")
    except Exception as exc:
        assert "No LLM providers configured" in str(exc)


def test_reason_endpoint_happy_path(client: TestClient, doctor_headers, monkeypatch):
    vid = seed_visit(client, doctor_headers)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-groq-model"
        assert "fever" in body["messages"][1]["content"]
        return chat_response(GOOD_JSON)

    monkeypatch.setattr(
        "app.api.routes.reason._get_reason_client",
        lambda: LLMClient(make_settings(monkeypatch), transport=httpx.MockTransport(handler)),
    )
    resp = client.post("/api/reason", json={"visit_id": vid}, headers=doctor_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cached"] is False
    assert body["provider"] == "groq"
    assert len(body["differentials"]) == 2
    assert body["differentials"][0]["rank"] == 1
    assert body["red_flags"]
    assert "final call" in body["disclaimer"]
    assert any(p["disease"] for p in body["classifier_predictions"])


def test_reason_cache_hit_skips_http(client: TestClient, doctor_headers, monkeypatch):
    vid = seed_visit(client, doctor_headers)
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        counter["n"] += 1
        return chat_response(GOOD_JSON)

    monkeypatch.setattr(
        "app.api.routes.reason._get_reason_client",
        lambda: LLMClient(make_settings(monkeypatch), transport=httpx.MockTransport(handler)),
    )
    first = client.post("/api/reason", json={"visit_id": vid}, headers=doctor_headers)
    assert first.json()["cached"] is False
    second = client.post("/api/reason", json={"visit_id": vid}, headers=doctor_headers)
    assert second.json()["cached"] is True
    assert second.status_code == 200
    assert counter["n"] == 1

    forced = client.post(
        "/api/reason", json={"visit_id": vid, "force_refresh": True},
        headers=doctor_headers,
    )
    assert forced.json()["cached"] is False
    assert counter["n"] == 2


def test_reason_validation_and_rbac(client: TestClient, doctor_headers, readonly_headers, monkeypatch):
    missing_visit = client.post(
        "/api/reason", json={"visit_id": str(uuid.uuid4())}, headers=doctor_headers
    )
    assert missing_visit.status_code == 404

    readonly_denied = client.post(
        "/api/reason", json={"visit_id": str(uuid.uuid4())}, headers=readonly_headers
    )
    assert readonly_denied.status_code == 403

    unauth = client.post("/api/reason", json={})
    assert unauth.status_code == 401


def test_reason_empty_symptoms_422(client: TestClient, doctor_headers, monkeypatch):
    pid = client.post(
        "/api/patients",
        json={"full_name": "No Symp", "consent_given": True},
        headers=doctor_headers,
    ).json()["id"]
    vid = client.post(
        "/api/visits", json={"patient_id": pid, "visit_type": "new"}, headers=doctor_headers
    ).json()["id"]
    resp = client.post("/api/reason", json={"visit_id": vid}, headers=doctor_headers)
    assert resp.status_code == 422


def test_reason_cache_key_changes_with_case():
    a = ReasonCache.make_key({"case": {"symptoms": ["fever"]}})
    b = ReasonCache.make_key({"case": {"symptoms": ["fever", "cough"]}})
    c = ReasonCache.make_key({"case": {"symptoms": ["fever"]}, "classifier": [1]})
    assert a != b and a != c
    assert a == ReasonCache.make_key({"case": {"symptoms": ["fever"]}})


def test_extract_json_variants():
    from app.services.llm import extract_json_object

    assert extract_json_object(GOOD_JSON)["summary"]
    assert extract_json_object(f"Sure! {FENCED_JSON} hope it helps")["summary"]
    assert extract_json_object('prefix {"a": 1} suffix') == {"a": 1}
    assert extract_json_object("no json here") is None
