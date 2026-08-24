import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient


def patient_payload(**overrides) -> dict:
    base = {
        "full_name": "Anita Desai",
        "mrn": f"MRN-{uuid.uuid4().hex[:8]}",
        "date_of_birth": "1985-03-14",
        "sex": "female",
        "weight_kg": 62.5,
        "height_cm": 164.0,
        "occupation": "Teacher",
        "phone": "+91-90000-00000",
        "email": "anita@example.com",
        "consent_given": True,
    }
    base.update(overrides)
    return base


def visit_payload(patient_id: str, **overrides) -> dict:
    base = {
        "patient_id": patient_id,
        "visit_type": "new",
        "chief_complaint": "Fever and dry cough for 3 days",
        "complaint_duration": "3 days",
        "severity_score": 6,
        "progression": "worsening",
        "hpi_onset": "gradual",
        "hpi_location": "chest and throat",
        "working_notes": "Suspicious of lower respiratory involvement.",
    }
    base.update(overrides)
    return base


def test_create_and_get_patient(client: TestClient, doctor_headers):
    resp = client.post("/api/patients", json=patient_payload(), headers=doctor_headers)
    assert resp.status_code == 201
    body = resp.json()
    pid = body["id"]
    assert body["sex"] == "female"
    assert body["created_at"]

    got = client.get(f"/api/patients/{pid}", headers=doctor_headers).json()
    assert got["id"] == pid
    assert got["allergies"] == []
    assert got["medications"] == []


def test_create_patient_rejects_future_dob(client: TestClient, doctor_headers):
    future = (date.today() + timedelta(days=30)).isoformat()
    resp = client.post(
        "/api/patients", json=patient_payload(date_of_birth=future), headers=doctor_headers
    )
    assert resp.status_code == 422


def test_duplicate_mrn_conflict(client: TestClient, doctor_headers):
    payload = patient_payload()
    assert client.post("/api/patients", json=payload, headers=doctor_headers).status_code == 201
    dup = client.post("/api/patients", json=payload, headers=doctor_headers)
    assert dup.status_code == 409


def test_patch_patient(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    resp = client.patch(
        f"/api/patients/{pid}", json={"weight_kg": 64.0}, headers=doctor_headers
    )
    assert resp.status_code == 200
    assert float(resp.json()["weight_kg"]) == 64.0


def test_list_patients_search(client: TestClient, doctor_headers):
    marker = uuid.uuid4().hex[:8]
    client.post(
        "/api/patients", json=patient_payload(full_name=f"Zeta {marker}"),
        headers=doctor_headers,
    )
    resp = client.get("/api/patients", params={"q": marker}, headers=doctor_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_allergy_lifecycle(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    created = client.post(
        f"/api/patients/{pid}/allergies",
        json={"allergen": "Penicillin", "type": "drug", "reaction": "hives", "severity": "moderate"},
        headers=doctor_headers,
    )
    assert created.status_code == 201
    aid = created.json()["id"]

    updated = client.patch(
        f"/api/patients/{pid}/allergies/{aid}",
        json={"severity": "severe"},
        headers=doctor_headers,
    )
    assert updated.json()["severity"] == "severe"

    detail = client.get(f"/api/patients/{pid}", headers=doctor_headers).json()
    assert [a["allergen"] for a in detail["allergies"]] == ["Penicillin"]

    deleted = client.delete(
        f"/api/patients/{pid}/allergies/{aid}", headers=doctor_headers
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/patients/{pid}/allergies", headers=doctor_headers).json() == []


def test_allergy_of_other_patient_404(client: TestClient, doctor_headers):
    p1 = client.post("/api/patients", json=patient_payload(), headers=doctor_headers).json()["id"]
    p2 = client.post("/api/patients", json=patient_payload(), headers=doctor_headers).json()["id"]
    aid = client.post(
        f"/api/patients/{p1}/allergies",
        json={"allergen": "Pollen", "type": "environmental"},
        headers=doctor_headers,
    ).json()["id"]
    resp = client.patch(
        f"/api/patients/{p2}/allergies/{aid}", json={"severity": "mild"},
        headers=doctor_headers,
    )
    assert resp.status_code == 404


def test_history_and_medication_endpoints(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    hist = client.post(
        f"/api/patients/{pid}/history",
        json={"category": "chronic_condition", "name": "Hypertension", "onset_year": 2019},
        headers=doctor_headers,
    )
    assert hist.status_code == 201
    med = client.post(
        f"/api/patients/{pid}/medications",
        json={"name": "Amlodipine", "dose": "5 mg", "frequency": "once daily", "is_active": True},
        headers=doctor_headers,
    )
    assert med.status_code == 201
    detail = client.get(f"/api/patients/{pid}", headers=doctor_headers).json()
    assert detail["history"][0]["name"] == "Hypertension"
    assert detail["medications"][0]["dose"] == "5 mg"


def test_visit_crud_flow(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    created = client.post("/api/visits", json=visit_payload(pid), headers=doctor_headers)
    assert created.status_code == 201
    vid = created.json()["id"]

    patched = client.patch(
        f"/api/visits/{vid}",
        json={"hpi_radiation": "to left arm", "severity_score": 7},
        headers=doctor_headers,
    )
    assert patched.json()["severity_score"] == 7

    listed = client.get(
        f"/api/patients/{pid}/visits", headers=doctor_headers
    ).json()
    assert [v["id"] for v in listed] == [vid]

    bad_patient = visit_payload(str(uuid.uuid4()))
    missing = client.post("/api/visits", json=bad_patient, headers=doctor_headers)
    assert missing.status_code == 404

    bad_severity = visit_payload(pid, severity_score=11)
    invalid = client.post("/api/visits", json=bad_severity, headers=doctor_headers)
    assert invalid.status_code == 422


def test_symptoms_replace_semantics(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    vid = client.post("/api/visits", json=visit_payload(pid), headers=doctor_headers).json()["id"]

    first = client.put(
        f"/api/visits/{vid}/symptoms",
        json=[
            {"name": "fever", "status": "present", "severity": 6, "duration": "3 days"},
            {"name": "cough", "code": "s15", "status": "present"},
            {"name": "chest_pain", "status": "absent"},
        ],
        headers=doctor_headers,
    )
    assert first.status_code == 200
    assert len(first.json()) == 3

    second = client.put(
        f"/api/visits/{vid}/symptoms",
        json=[{"name": "fatigue", "status": "unsure"}],
        headers=doctor_headers,
    )
    assert second.status_code == 200
    detail = client.get(f"/api/visits/{vid}", headers=doctor_headers).json()
    assert [s["name"] for s in detail["symptoms"]] == ["fatigue"]


def test_vitals_upsert_and_validation(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    vid = client.post("/api/visits", json=visit_payload(pid), headers=doctor_headers).json()["id"]

    first = client.put(
        f"/api/visits/{vid}/vitals",
        json={"temperature_c": 38.4, "systolic_bp": 118, "diastolic_bp": 76, "spo2": 97.0},
        headers=doctor_headers,
    )
    assert first.status_code == 200

    second = client.put(
        f"/api/visits/{vid}/vitals", json={"heart_rate": 92}, headers=doctor_headers
    )
    assert second.status_code == 200
    detail = client.get(f"/api/visits/{vid}", headers=doctor_headers).json()
    assert detail["vitals"]["temperature_c"] == 38.4
    assert detail["vitals"]["heart_rate"] == 92

    bad = client.put(
        f"/api/visits/{vid}/vitals",
        json={"systolic_bp": 90, "diastolic_bp": 120},
        headers=doctor_headers,
    )
    assert bad.status_code == 422


def test_social_history_upsert(client: TestClient, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    vid = client.post("/api/visits", json=visit_payload(pid), headers=doctor_headers).json()["id"]

    first = client.put(
        f"/api/visits/{vid}/social-history",
        json={"smoking_status": "current", "pack_years": 10, "alcohol_use": "occasional",
              "travel_history": "Returned from coastal region 2 weeks ago"},
        headers=doctor_headers,
    )
    assert first.status_code == 200
    second = client.put(
        f"/api/visits/{vid}/social-history", json={"pack_years": 12}, headers=doctor_headers
    )
    assert second.json()["pack_years"] == 12
    assert second.json()["alcohol_use"] == "occasional"

    detail = client.get(f"/api/visits/{vid}", headers=doctor_headers).json()
    assert detail["social_history"]["smoking_status"] == "current"


def test_read_only_can_read_not_write(client: TestClient, readonly_headers, doctor_headers):
    pid = client.post(
        "/api/patients", json=patient_payload(), headers=doctor_headers
    ).json()["id"]
    assert client.get(f"/api/patients/{pid}", headers=readonly_headers).status_code == 200
    denied_create = client.post(
        "/api/patients", json=patient_payload(), headers=readonly_headers
    )
    assert denied_create.status_code == 403
    denied_patch = client.patch(
        f"/api/patients/{pid}", json={"weight_kg": 70}, headers=readonly_headers
    )
    assert denied_patch.status_code == 403


def test_unauthenticated_access_denied(client: TestClient):
    assert client.get("/api/patients").status_code == 401
    assert client.post("/api/visits", json={}).status_code == 401
