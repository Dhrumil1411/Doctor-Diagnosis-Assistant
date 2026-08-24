import uuid

from fastapi.testclient import TestClient

from app.services.classifier import get_classifier

CLASSIC_FUNGAL = ["itching", "skin_rash", "nodal_skin_eruptions"]


def test_direct_predict_ranked(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/predict", json={"symptoms": CLASSIC_FUNGAL}, headers=doctor_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_name"] == "logistic_regression"
    preds = body["predictions"]
    assert 0 < len(preds) <= 5
    confidences = [p["confidence"] for p in preds]
    assert confidences == sorted(confidences, reverse=True)
    assert all(0.0 <= c <= 1.0 for c in confidences)
    assert preds[0]["rank"] == 1
    assert body["unknown_symptoms"] == []


def test_unknown_symptoms_reported_not_fatal(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/predict",
        json={"symptoms": ["itching", "totally_made_up_symptom"]},
        headers=doctor_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["unknown_symptoms"] == ["totally_made_up_symptom"]
    assert "itching" in body["recognized_symptoms"]
    assert len(body["predictions"]) >= 1


def test_top_k_respected(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/predict", json={"symptoms": CLASSIC_FUNGAL, "top_k": 3},
        headers=doctor_headers,
    )
    assert len(resp.json()["predictions"]) == 3


def test_invalid_requests_rejected(client: TestClient, doctor_headers):
    both = client.post(
        "/api/predict",
        json={"symptoms": CLASSIC_FUNGAL, "visit_id": str(uuid.uuid4())},
        headers=doctor_headers,
    )
    assert both.status_code == 422

    neither = client.post("/api/predict", json={}, headers=doctor_headers)
    assert neither.status_code == 422

    empty = client.post(
        "/api/predict", json={"symptoms": []}, headers=doctor_headers
    )
    assert empty.status_code == 422


def test_predict_from_visit_uses_present_only(
    client: TestClient, doctor_headers
):
    pid = client.post(
        "/api/patients",
        json={"full_name": "Pred Ctx", "consent_given": True},
        headers=doctor_headers,
    ).json()["id"]
    vid = client.post(
        "/api/visits",
        json={"patient_id": pid, "visit_type": "new"},
        headers=doctor_headers,
    ).json()["id"]
    client.put(
        f"/api/visits/{vid}/symptoms",
        json=[
            {"name": "continuous_sneezing", "status": "present"},
            {"name": "watering_from_eyes", "status": "present"},
            {"name": "chest_pain", "status": "absent"},
            {"name": "fatigue", "status": "unsure"},
        ],
        headers=doctor_headers,
    )
    resp = client.post("/api/predict", json={"visit_id": vid}, headers=doctor_headers)
    assert resp.status_code == 200
    recognized = resp.json()["recognized_symptoms"]
    assert set(recognized) == {"continuous_sneezing", "watering_from_eyes"}


def test_predict_visit_without_present_symptoms(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients",
        json={"full_name": "Empty Visit", "consent_given": True},
        headers=doctor_headers,
    ).json()["id"]
    vid = client.post(
        "/api/visits",
        json={"patient_id": pid, "visit_type": "follow_up"},
        headers=doctor_headers,
    ).json()["id"]
    resp = client.post("/api/predict", json={"visit_id": vid}, headers=doctor_headers)
    assert resp.status_code == 422


def test_predict_unknown_visit_404(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/predict", json={"visit_id": str(uuid.uuid4())}, headers=doctor_headers
    )
    assert resp.status_code == 404


def test_predict_rbac(client: TestClient, readonly_headers):
    denied = client.post(
        "/api/predict", json={"symptoms": CLASSIC_FUNGAL}, headers=readonly_headers
    )
    assert denied.status_code == 403
    unauth = client.post("/api/predict", json={"symptoms": CLASSIC_FUNGAL})
    assert unauth.status_code == 401


def test_diabetes_case_ranks_diabetes_top(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/predict",
        json={
            "symptoms": [
                "increased_appetite",
                "polyuria",
                "excessive_thirst",
                "weight_loss",
                "blurred_and_distorted_vision",
            ]
        },
        headers=doctor_headers,
    )
    assert resp.status_code == 200
    preds = resp.json()["predictions"]
    classifier = get_classifier()
    assert all(s in classifier.known_symptom_ids() for s in CLASSIC_FUNGAL)
    assert any("diabetes" in p["disease"].lower() for p in preds)
