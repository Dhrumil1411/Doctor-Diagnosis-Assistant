import json
import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.services.note_extractor import extract_clinical_note

MOCK_EXTRACTED_JSON = json.dumps({
    "summary": "58-year-old male with acute retrosternal chest pain radiating to left arm.",
    "demographics": {
        "full_name": "John Doe",
        "age_years": 58,
        "sex": "male",
        "weight_kg": 85.5,
        "height_cm": 175.0,
        "occupation": "Accountant"
    },
    "visit_info": {
        "chief_complaint": "Crushing chest pain radiating to left arm",
        "complaint_duration": "2 hours",
        "severity_score": 8,
        "progression": "worsening"
    },
    "hpi": {
        "hpi_onset": "acute sudden onset",
        "hpi_location": "substernal",
        "hpi_character": "crushing pressure",
        "hpi_aggravating_factors": "exertion",
        "hpi_relieving_factors": "none",
        "hpi_radiation": "left arm and jaw",
        "hpi_timing": "constant"
    },
    "vitals": {
        "temperature_c": 37.1,
        "systolic_bp": 155,
        "diastolic_bp": 95,
        "heart_rate": 102,
        "respiratory_rate": 22,
        "spo2": 95.0,
        "blood_glucose_mg_dl": 140.0,
        "pain_score": 8
    },
    "symptoms_present": ["sharp chest pain", "shortness of breath", "sweating", "nausea"],
    "symptoms_absent": ["cough", "fever", "vomiting"],
    "medical_history": [
        {
            "category": "cardiovascular",
            "name": "Essential Hypertension",
            "details": "Well-controlled",
            "onset_year": 2018,
            "resolved": False
        },
        {
            "category": "endocrine",
            "name": "Type 2 Diabetes Mellitus",
            "details": "HbA1c 7.2%",
            "onset_year": 2020,
            "resolved": False
        }
    ],
    "medications": [
        {
            "name": "Lisinopril",
            "dose": "20 mg",
            "frequency": "once daily",
            "is_active": True,
            "notes": "morning"
        }
    ],
    "allergies": [
        {
            "allergen": "Penicillin",
            "type": "medication",
            "reaction": "anaphylaxis",
            "severity": "severe",
            "notes": "childhood"
        }
    ],
    "social_history": {
        "smoking_status": "current",
        "pack_years": 25.0,
        "alcohol_use": "none"
    },
    "physical_exam": {
        "pallor": "none",
        "edema": "none",
        "cyanosis": "none",
        "extra_notes": "diaphoretic, anxious"
    }
})


def make_test_settings(monkeypatch, **overrides):
    base = dict(
        llm_provider_chain="groq",
        groq_api_key="g-key",
        groq_model="test-groq-model",
    )
    base.update(overrides)
    s = Settings(**base)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    return s


def test_extract_clinical_note_mock_llm(monkeypatch):
    settings = make_test_settings(monkeypatch)

    def mock_chat_json(self, messages):
        return json.loads(MOCK_EXTRACTED_JSON), "groq"

    from app.services.llm import LLMClient
    monkeypatch.setattr(LLMClient, "chat_json", mock_chat_json)

    raw_note = "58 yo male with crushing chest pain radiating to left arm and diaphoresis."
    result = extract_clinical_note(raw_note, settings)

    assert result.demographics.age_years == 58
    assert result.demographics.sex == "male"
    assert result.vitals.systolic_bp == 155
    assert result.vitals.heart_rate == 102
    assert len(result.symptoms_present) >= 3
    # Check HPO mapping
    chest_pain_sym = next(s for s in result.symptoms_present if "chest" in s.name.lower() or s.canonical_id == "sharp_chest_pain")
    assert chest_pain_sym.hpo_id == "HP:0001681" or chest_pain_sym.canonical_id == "sharp_chest_pain"
    assert len(result.medical_history) == 2
    assert len(result.medications) == 1
    assert result.medications[0].name == "Lisinopril"
    assert len(result.allergies) == 1
    assert result.allergies[0].allergen == "Penicillin"


def test_extract_clinical_note_heuristic_fallback():
    settings = Settings(llm_provider_chain="")  # No LLM configured

    raw_note = "65 yo male presenting with BP 140/90, HR 88, SpO2 96%, denies cough, has fever and fatigue."
    result = extract_clinical_note(raw_note, settings)

    assert result.demographics.age_years == 65
    assert result.demographics.sex == "male"
    assert result.vitals.systolic_bp == 140
    assert result.vitals.diastolic_bp == 90
    assert result.vitals.heart_rate == 88
    assert result.vitals.spo2 == 96.0


def test_extract_note_api_endpoint(client: TestClient, doctor_headers, monkeypatch):
    make_test_settings(monkeypatch)

    def mock_chat_json(self, messages):
        return json.loads(MOCK_EXTRACTED_JSON), "groq"

    from app.services.llm import LLMClient
    monkeypatch.setattr(LLMClient, "chat_json", mock_chat_json)

    resp = client.post(
        "/api/clinical-notes/extract",
        json={"raw_note": "58 yo male with crushing substernal chest pain."},
        headers=doctor_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["demographics"]["age_years"] == 58
    assert data["visit_info"]["severity_score"] == 8
    assert len(data["symptoms_present"]) > 0


def test_extract_note_api_validation(client: TestClient, doctor_headers):
    resp = client.post(
        "/api/clinical-notes/extract",
        json={"raw_note": "hi"},
        headers=doctor_headers,
    )
    assert resp.status_code == 422
