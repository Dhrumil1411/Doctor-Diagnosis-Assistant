"""End-to-end integration tests using curated clinical cases and Synthea synthetic data.

Validates the full CDS lifecycle through the API stack:
Patient Intake -> Encounter / HPI / Vitals -> ML Prediction -> Lab Attachments ->
LLM Differential Reasoning -> Doctor Review & Feedback Loop -> Audit Trail.
"""

import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.e2e.curated_cases import load_curated_cases
from app.e2e.synthea_loader import load_synthea_cases
import app.api.routes.reason as reason_module


def _mock_llm_response(differentials, red_flags=None, steps=None):
    return {
        "summary": "Clinical evaluation based on patient presentation and examination.",
        "differentials": differentials or [
            {
                "rank": 1,
                "condition": "Primary Consideration",
                "likelihood": "high",
                "supporting_findings": ["Presenting symptoms"],
                "opposing_findings": [],
                "notes": "Correlate with diagnostic workup.",
            }
        ],
        "red_flags": red_flags or [],
        "suggested_next_steps": steps or ["CBC", "BMP", "Clinical observation"],
        "questions_for_patient": ["Any travel or sick contacts?"],
    }


@pytest.fixture(autouse=True)
def _clear_cache():
    reason_module._cache._store.clear()
    yield
    reason_module._cache._store.clear()


def test_e2e_curated_clinical_cases(client: TestClient, doctor_headers, monkeypatch):
    """Execute complete end-to-end clinical workflow for all curated cases."""
    cases = load_curated_cases()
    assert len(cases) >= 5

    for case in cases:
        # 1. Create Patient with unique MRN
        patient_payload = dict(case["patient"])
        if patient_payload.get("mrn"):
            patient_payload["mrn"] = f"{patient_payload['mrn']}-{uuid.uuid4().hex[:6]}"
        p_resp = client.post("/api/patients", json=patient_payload, headers=doctor_headers)
        assert p_resp.status_code == 201, f"Failed to create patient: {p_resp.text}"
        patient_id = p_resp.json()["id"]

        # Sub-resources: Medical History, Medications, Allergies
        for h in case.get("medical_history", []):
            client.post(f"/api/patients/{patient_id}/history", json=h, headers=doctor_headers)
        for m in case.get("medications", []):
            client.post(f"/api/patients/{patient_id}/medications", json=m, headers=doctor_headers)
        for a in case.get("allergies", []):
            client.post(f"/api/patients/{patient_id}/allergies", json=a, headers=doctor_headers)

        # 2. Create Visit
        visit_payload = dict(case["visit"])
        visit_payload["patient_id"] = patient_id
        v_resp = client.post("/api/visits", json=visit_payload, headers=doctor_headers)
        assert v_resp.status_code == 201, f"Failed to create visit: {v_resp.text}"
        visit_id = v_resp.json()["id"]

        # Vitals & Social History
        if "vitals" in case:
            vit_resp = client.put(f"/api/visits/{visit_id}/vitals", json=case["vitals"], headers=doctor_headers)
            assert vit_resp.status_code == 200, f"Vitals failed: {vit_resp.text}"

        if "social_history" in case:
            soc_resp = client.put(f"/api/visits/{visit_id}/social-history", json=case["social_history"], headers=doctor_headers)
            assert soc_resp.status_code == 200, f"Social history failed: {soc_resp.text}"

        # Symptoms
        symptom_payloads = [
            {"name": s["name"], "status": s.get("status", "present"), "severity": s.get("severity", 5), "duration": s.get("duration", "1 week")}
            for s in case.get("symptoms", [])
        ]
        sym_resp = client.put(f"/api/visits/{visit_id}/symptoms", json=symptom_payloads, headers=doctor_headers)
        assert sym_resp.status_code == 200, f"Symptoms failed: {sym_resp.text}"
        assert len(sym_resp.json()) == len(symptom_payloads)

        # 3. Classifier Prediction
        pred_resp = client.post("/api/predict", json={"visit_id": visit_id, "top_k": 5}, headers=doctor_headers)
        assert pred_resp.status_code == 200, f"Prediction failed: {pred_resp.text}"
        pred_data = pred_resp.json()
        assert "predictions" in pred_data
        assert len(pred_data["predictions"]) > 0
        top_pred = pred_data["predictions"][0]["disease"]

        # If case has expected diseases, check if top ML predictions match or overlap
        expected_diseases = case.get("expected_diseases", [])
        if expected_diseases:
            top_3_diseases = [p["disease"].strip().lower() for p in pred_data["predictions"][:3]]
            # At least one expected disease is in top predictions
            assert any(exp.strip().lower() in top_3_diseases for exp in expected_diseases), (
                f"Expected one of {expected_diseases} in top 3 predictions {top_3_diseases}"
            )

        # 4. Attach Labs
        for lab in case.get("labs", []):
            lab_resp = client.post(f"/api/visits/{visit_id}/labs", data=lab, headers=doctor_headers)
            assert lab_resp.status_code == 201, f"Lab upload failed: {lab_resp.text}"

        # 5. LLM Differential Reasoning (with mocked response generator for test suite)
        mock_diffs = [
            {
                "rank": i + 1,
                "condition": d,
                "likelihood": "high" if i == 0 else "moderate",
                "supporting_findings": [s["name"] for s in case["symptoms"][:2]],
                "notes": f"Clinical findings support {d}",
            }
            for i, d in enumerate(expected_diseases or [top_pred])
        ]
        red_flags = ["Immediate emergency intervention required"] if case.get("is_emergency") else []
        mock_body = _mock_llm_response(mock_diffs, red_flags=red_flags)

        class MockLLM:
            def chat_json(self, messages):
                return mock_body, "mock-groq"

        monkeypatch.setattr("app.api.routes.reason._get_reason_client", lambda: MockLLM())

        reason_resp = client.post("/api/reason", json={"visit_id": visit_id}, headers=doctor_headers)
        assert reason_resp.status_code == 200, f"Reason failed: {reason_resp.text}"
        reason_data = reason_resp.json()
        assert len(reason_data["differentials"]) >= 1
        if case.get("is_emergency"):
            assert len(reason_data["red_flags"]) >= 1

        # 6. Doctor Feedback Loop (Accept / Edit)
        doc_decision = case.get("doctor_decision", "accepted")
        diag_payload = {
            "doctor_decision": doc_decision,
            "disease_label": top_pred,
            "edited_label": case.get("doctor_override_diagnosis"),
            "reasoning": case.get("doctor_notes", "Reviewed and confirmed by attending physician."),
            "suggested_next_steps": ", ".join(reason_data.get("suggested_next_steps", [])),
        }
        diag_resp = client.post(f"/api/visits/{visit_id}/diagnosis", json=diag_payload, headers=doctor_headers)
        assert diag_resp.status_code == 200, f"Diagnosis save failed: {diag_resp.text}"
        diag_saved = diag_resp.json()
        assert diag_saved["doctor_decision"] == doc_decision

        # 7. Verify full visit detail retrieval
        visit_detail_resp = client.get(f"/api/visits/{visit_id}", headers=doctor_headers)
        assert visit_detail_resp.status_code == 200
        detail = visit_detail_resp.json()
        assert detail["patient_id"] == patient_id
        assert len(detail["symptoms"]) == len(symptom_payloads)
        assert len(detail["labs"]) == len(case.get("labs", []))


def test_e2e_synthea_loader_and_simulation(client: TestClient, doctor_headers, monkeypatch):
    """Verify Synthea loader reads CSVs and can execute an end-to-end visit."""
    cases = load_synthea_cases(limit=3)
    if not cases:
        pytest.skip("Synthea CSV dataset not found at expected location.")

    assert len(cases) >= 1
    case = cases[0]

    # Create Patient with unique MRN
    patient_payload = dict(case["patient"])
    if patient_payload.get("mrn"):
        patient_payload["mrn"] = f"{patient_payload['mrn']}-{uuid.uuid4().hex[:6]}"
    p_resp = client.post("/api/patients", json=patient_payload, headers=doctor_headers)
    assert p_resp.status_code == 201
    patient_id = p_resp.json()["id"]

    # Create Visit
    visit_payload = dict(case["visit"])
    visit_payload["patient_id"] = patient_id
    v_resp = client.post("/api/visits", json=visit_payload, headers=doctor_headers)
    assert v_resp.status_code == 201
    visit_id = v_resp.json()["id"]

    # Vitals
    if case.get("vitals"):
        vit_resp = client.put(f"/api/visits/{visit_id}/vitals", json=case["vitals"], headers=doctor_headers)
        assert vit_resp.status_code == 200

    # Symptoms
    symptom_payloads = [
        {"name": s, "status": "present", "severity": 6, "duration": "1 week"}
        for s in case.get("symptoms", [])
    ]
    sym_resp = client.put(f"/api/visits/{visit_id}/symptoms", json=symptom_payloads, headers=doctor_headers)
    assert sym_resp.status_code == 200

    # ML Predict
    pred_resp = client.post("/api/predict", json={"visit_id": visit_id}, headers=doctor_headers)
    assert pred_resp.status_code == 200
    assert len(pred_resp.json()["predictions"]) > 0

    # LLM Reasoning Mock
    mock_body = _mock_llm_response([
        {"rank": 1, "condition": "Simulated Condition", "likelihood": "moderate", "supporting_findings": case["symptoms"][:2]}
    ])

    class MockLLM:
        def chat_json(self, messages):
            return mock_body, "mock-groq"

    monkeypatch.setattr("app.api.routes.reason._get_reason_client", lambda: MockLLM())

    reason_resp = client.post("/api/reason", json={"visit_id": visit_id}, headers=doctor_headers)
    assert reason_resp.status_code == 200
    assert len(reason_resp.json()["differentials"]) == 1

    # Diagnosis save
    diag_resp = client.post(
        f"/api/visits/{visit_id}/diagnosis",
        json={
            "doctor_decision": "accepted",
            "disease_label": "Simulated Condition",
            "reasoning": "Synthea simulation case confirmed.",
        },
        headers=doctor_headers
    )
    assert diag_resp.status_code == 200
