"""Clinical Note and Consultation Transcript NLP Extractor Service.

Parses unstructured clinical notes, doctor-patient dialogues, and SOAP narratives into
standardized clinical data models mapped to canonical feature IDs and Human Phenotype Ontology (HPO) codes.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import Settings
from app.models.allergies import AllergyType
from app.models.medical_history import HistoryCategory
from app.schemas.clinical import AllergyCreate, HistoryEntryCreate, MedicationCreate
from app.schemas.note_extractor import (
    ExtractedClinicalCase,
    ExtractedDemographics,
    ExtractedExamFindings,
    ExtractedHpi,
    ExtractedSocialHistory,
    ExtractedSymptomItem,
    ExtractedVisitInfo,
    ExtractedVitals,
)
from app.services.classifier import get_classifier
from app.services.llm import LLMClient, LLMError
from app.services.symptom_mapper import get_symptom_mapper

logger = logging.getLogger("uvicorn.error")

NOTE_EXTRACTION_SYSTEM_PROMPT = """You are an expert clinical information extraction engine.
Given an unstructured doctor's clinical note, SOAP examination note, or doctor-patient consultation dialogue transcript,
extract all clinical entities into a structured JSON schema.

Strict Schema Rules:
1. "summary": Concise 1-2 sentence clinical summary of the presentation.
2. "demographics":
   - "full_name": string or null
   - "age_years": integer or null
   - "sex": "male" | "female" | "other" | "unknown"
   - "weight_kg": float or null
   - "height_cm": float or null
   - "occupation": string or null
3. "visit_info":
   - "chief_complaint": string (primary presenting reason for visit)
   - "complaint_duration": string (e.g. "3 days", "2 hours", "1 week") or null
   - "severity_score": integer (1 to 10 scale based on note context) or null
   - "progression": "improving" | "stable" | "worsening" | "fluctuating" | null
4. "hpi":
   - "hpi_onset": string (e.g. "sudden acute onset", "gradual onset over 2 days") or null
   - "hpi_location": string (e.g. "substernal chest", "right lower quadrant") or null
   - "hpi_character": string (e.g. "crushing pressure", "burning", "sharp stabbing") or null
   - "hpi_aggravating_factors": string (e.g. "exertion, deep breathing") or null
   - "hpi_relieving_factors": string (e.g. "rest, sublingual nitroglycerin") or null
   - "hpi_radiation": string (e.g. "radiates to left arm and jaw") or null
   - "hpi_timing": string (e.g. "constant", "intermittent attacks") or null
5. "vitals":
   - "temperature_c": float or null (e.g. 38.5)
   - "systolic_bp": integer or null (e.g. 130)
   - "diastolic_bp": integer or null (e.g. 85)
   - "heart_rate": integer or null (e.g. 98)
   - "respiratory_rate": integer or null (e.g. 20)
   - "spo2": float or null (e.g. 96.0)
   - "blood_glucose_mg_dl": float or null
   - "pain_score": integer (0 to 10) or null
6. "symptoms_present": List of symptom names/phrases explicitly experienced by the patient (e.g. ["sharp chest pain", "shortness of breath", "sweating", "nausea", "fever"]).
7. "symptoms_absent": List of pertinent negative symptoms explicitly denied (e.g. ["cough", "vomiting", "dizziness"]).
8. "medical_history": List of objects with:
   - "category": "general"|"cardiovascular"|"respiratory"|"gastrointestinal"|"neurological"|"endocrine"|"renal"|"oncological"|"psychiatric"|"surgical"|"family"|"other"
   - "name": string (e.g. "Essential Hypertension", "Type 2 Diabetes Mellitus", "Coronary Artery Disease")
   - "details": string or null
   - "onset_year": integer or null
   - "resolved": boolean (default false)
9. "medications": List of objects with:
   - "name": string (e.g. "Metformin", "Lisinopril", "Aspirin")
   - "dose": string or null (e.g. "500 mg", "10 mg")
   - "frequency": string or null (e.g. "twice daily", "once daily")
   - "is_active": boolean (default true)
10. "allergies": List of objects with:
    - "allergen": string (e.g. "Penicillin", "Sulfa drugs", "Peanuts")
    - "type": "medication" | "food" | "environmental" | "other"
    - "reaction": string or null (e.g. "anaphylaxis", "hives", "maculopapular rash")
    - "severity": "mild" | "moderate" | "severe" or null
11. "social_history":
    - "smoking_status": "never" | "former" | "current" | "unknown"
    - "pack_years": float or null
    - "alcohol_use": string or null
    - "recreational_drug_use": string or null
    - "diet": string or null
    - "exercise": string or null
12. "physical_exam":
    - "pallor": "absent" | "present" | null
    - "edema": "absent" | "present" | null
    - "cyanosis": "absent" | "present" | null
    - "clubbing": "absent" | "present" | null
    - "lymphadenopathy": "absent" | "present" | null
    - "dehydration": "absent" | "present" | null
    - "extra_notes": string or null (physical findings, heart sounds, lung auscultation, etc.)

Output strictly valid JSON with no conversational text or markdown around it."""


def _heuristic_fallback_extraction(raw_note: str) -> ExtractedClinicalCase:
    """Fast regex and keyword fallback extractor when LLM is offline or unconfigured."""
    text_lower = raw_note.lower()
    
    # Check age
    age_match = re.search(r"\b(\d{1,3})\s*(?:yo|y/o|year[s]?\s*old|yr[s]?\s*old)\b", text_lower)
    age = int(age_match.group(1)) if age_match else None
    
    # Check sex
    sex = "unknown"
    if re.search(r"\b(male|man|gentleman|boy|he|his)\b", text_lower):
        sex = "male"
    elif re.search(r"\b(female|woman|lady|girl|she|her)\b", text_lower):
        sex = "female"

    # Check vitals
    vitals = ExtractedVitals()
    bp_match = re.search(r"\b(?:bp|blood pressure)[:\s]*(\d{2,3})/(\d{2,3})\b", text_lower)
    if bp_match:
        vitals.systolic_bp = int(bp_match.group(1))
        vitals.diastolic_bp = int(bp_match.group(2))
    
    hr_match = re.search(r"\b(?:hr|pulse|heart rate)[:\s]*(\d{2,3})\b", text_lower)
    if hr_match:
        vitals.heart_rate = int(hr_match.group(1))

    spo2_match = re.search(r"\b(?:spo2|o2 sat|oxygen)[:\s]*(\d{2,3})%?\b", text_lower)
    if spo2_match:
        vitals.spo2 = float(spo2_match.group(1))

    temp_match = re.search(r"\b(?:temp|temperature)[:\s]*(\d{2,3}(?:\.\d)?)\s*(?:c|f)?\b", text_lower)
    if temp_match:
        t_val = float(temp_match.group(1))
        if t_val > 90:  # Fahrenheit
            t_val = round((t_val - 32) * 5 / 9, 1)
        vitals.temperature_c = t_val

    # Find common symptom keywords
    mapper = get_symptom_mapper()
    classifier = get_classifier()
    known = set(classifier.feature_names) if classifier else None

    present_symptoms: list[ExtractedSymptomItem] = []
    # Search for canonical or registered symptoms in text
    for token in re.split(r"[,;.\n]+", text_lower):
        token_clean = token.strip()
        if not token_clean or len(token_clean) < 3:
            continue
        # Check if contains negative words
        is_neg = bool(re.search(r"\b(no|denies|denied|without|negative for)\b", token_clean))
        resolved = mapper.resolve_symptom(token_clean, known)
        if resolved.get("feature_id"):
            item = ExtractedSymptomItem(
                name=resolved["hpo_label"] or resolved["feature_id"].replace("_", " "),
                canonical_id=resolved["feature_id"],
                hpo_id=resolved.get("hpo_id"),
                hpo_label=resolved.get("hpo_label"),
                category=resolved.get("category"),
                status="absent" if is_neg else "present",
            )
            if not is_neg:
                if not any(s.canonical_id == item.canonical_id for s in present_symptoms):
                    present_symptoms.append(item)

    return ExtractedClinicalCase(
        summary=f"Clinical note parsed for {sex} patient" + (f", age {age}" if age else ""),
        demographics=ExtractedDemographics(age_years=age, sex=sex),
        visit_info=ExtractedVisitInfo(chief_complaint=raw_note[:120].strip()),
        vitals=vitals,
        symptoms_present=present_symptoms,
        working_notes=raw_note,
    )


def extract_clinical_note(raw_note: str, settings: Settings) -> ExtractedClinicalCase:
    """Extract structured clinical case data from raw notes using LLM + SymptomMapper."""
    if not raw_note or len(raw_note.strip()) < 5:
        raise ValueError("Clinical note text is too short to extract meaningful clinical entities.")

    client = LLMClient(settings)
    mapper = get_symptom_mapper()
    classifier = get_classifier()
    known_features = set(classifier.feature_names) if classifier else None

    messages = [
        {"role": "system", "content": NOTE_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Extract structured clinical entities from this clinical note:\n\n{raw_note}"},
    ]

    extracted_dict: dict[str, Any] | None = None
    try:
        extracted_dict, _ = client.chat_json(messages)
    except LLMError as exc:
        logger.warning("LLM note extraction failed (%s), using fallback heuristic parser", exc)
        return _heuristic_fallback_extraction(raw_note)

    if not extracted_dict or not isinstance(extracted_dict, dict):
        return _heuristic_fallback_extraction(raw_note)

    # 1. Parse demographics
    demo_data = extracted_dict.get("demographics", {})
    demographics = ExtractedDemographics(
        full_name=demo_data.get("full_name"),
        age_years=demo_data.get("age_years"),
        date_of_birth=demo_data.get("date_of_birth"),
        sex=demo_data.get("sex", "unknown"),
        weight_kg=demo_data.get("weight_kg"),
        height_cm=demo_data.get("height_cm"),
        occupation=demo_data.get("occupation"),
    )

    # 2. Parse visit info
    visit_data = extracted_dict.get("visit_info", {})
    visit_info = ExtractedVisitInfo(
        chief_complaint=visit_data.get("chief_complaint"),
        complaint_duration=visit_data.get("complaint_duration"),
        severity_score=visit_data.get("severity_score"),
        progression=visit_data.get("progression"),
    )

    # 3. Parse HPI
    hpi_data = extracted_dict.get("hpi", {})
    hpi = ExtractedHpi(
        hpi_onset=hpi_data.get("hpi_onset"),
        hpi_location=hpi_data.get("hpi_location"),
        hpi_character=hpi_data.get("hpi_character"),
        hpi_aggravating_factors=hpi_data.get("hpi_aggravating_factors"),
        hpi_relieving_factors=hpi_data.get("hpi_relieving_factors"),
        hpi_radiation=hpi_data.get("hpi_radiation"),
        hpi_timing=hpi_data.get("hpi_timing"),
    )

    # 4. Parse Vitals
    vitals_data = extracted_dict.get("vitals", {})
    vitals = ExtractedVitals(
        temperature_c=vitals_data.get("temperature_c"),
        systolic_bp=vitals_data.get("systolic_bp"),
        diastolic_bp=vitals_data.get("diastolic_bp"),
        heart_rate=vitals_data.get("heart_rate"),
        respiratory_rate=vitals_data.get("respiratory_rate"),
        spo2=vitals_data.get("spo2"),
        blood_glucose_mg_dl=vitals_data.get("blood_glucose_mg_dl"),
        pain_score=vitals_data.get("pain_score"),
    )

    # 5. Normalize Symptoms (Present & Absent) using SymptomMapper
    raw_present = extracted_dict.get("symptoms_present", [])
    raw_absent = extracted_dict.get("symptoms_absent", [])

    symptoms_present: list[ExtractedSymptomItem] = []
    seen_present_features = set()

    for item in raw_present:
        term_str = item if isinstance(item, str) else item.get("name", str(item))
        resolved = mapper.resolve_symptom(term_str, known_features)
        feat_id = resolved.get("feature_id")
        hpo_id = resolved.get("hpo_id")
        hpo_label = resolved.get("hpo_label") or term_str
        category = resolved.get("category", "General")

        # Avoid duplicates
        key = feat_id or hpo_label.lower()
        if key not in seen_present_features:
            seen_present_features.add(key)
            symptoms_present.append(
                ExtractedSymptomItem(
                    name=hpo_label,
                    canonical_id=feat_id,
                    hpo_id=hpo_id,
                    hpo_label=hpo_label,
                    category=category,
                    status="present",
                )
            )

    symptoms_absent: list[ExtractedSymptomItem] = []
    seen_absent_features = set()
    for item in raw_absent:
        term_str = item if isinstance(item, str) else item.get("name", str(item))
        resolved = mapper.resolve_symptom(term_str, known_features)
        feat_id = resolved.get("feature_id")
        hpo_id = resolved.get("hpo_id")
        hpo_label = resolved.get("hpo_label") or term_str
        category = resolved.get("category", "General")

        key = feat_id or hpo_label.lower()
        if key not in seen_absent_features and key not in seen_present_features:
            seen_absent_features.add(key)
            symptoms_absent.append(
                ExtractedSymptomItem(
                    name=hpo_label,
                    canonical_id=feat_id,
                    hpo_id=hpo_id,
                    hpo_label=hpo_label,
                    category=category,
                    status="absent",
                )
            )

    # 6. Parse Medical History
    history_entries: list[HistoryEntryCreate] = []
    for h in extracted_dict.get("medical_history", []):
        if isinstance(h, dict) and h.get("name"):
            cat_str = str(h.get("category", "chronic_condition")).lower().strip()
            if cat_str in {"family", "family_history"}:
                cat_enum = HistoryCategory.family_history
            elif cat_str in {"surgery", "surgical", "operation"}:
                cat_enum = HistoryCategory.surgery
            elif cat_str in {"hospitalization", "admission"}:
                cat_enum = HistoryCategory.hospitalization
            elif cat_str in {"immunization", "vaccine", "vaccination"}:
                cat_enum = HistoryCategory.immunization
            else:
                cat_enum = HistoryCategory.chronic_condition

            history_entries.append(
                HistoryEntryCreate(
                    category=cat_enum,
                    name=str(h["name"]),
                    details=h.get("details"),
                    onset_year=h.get("onset_year"),
                    resolved=bool(h.get("resolved", False)),
                )
            )

    # 7. Parse Medications
    medications: list[MedicationCreate] = []
    for m in extracted_dict.get("medications", []):
        if isinstance(m, dict) and m.get("name"):
            medications.append(
                MedicationCreate(
                    name=str(m["name"]),
                    dose=m.get("dose"),
                    frequency=m.get("frequency"),
                    is_active=bool(m.get("is_active", True)),
                    notes=m.get("notes"),
                )
            )

    # 8. Parse Allergies
    allergies: list[AllergyCreate] = []
    for a in extracted_dict.get("allergies", []):
        if isinstance(a, dict) and a.get("allergen"):
            type_str = str(a.get("type", "drug")).lower().strip()
            if type_str in {"medication", "medicine", "drug", "pharmaceutical"}:
                type_enum = AllergyType.drug
            elif type_str in {"food", "dietary"}:
                type_enum = AllergyType.food
            elif type_str in {"environmental", "pollen", "dust", "animal"}:
                type_enum = AllergyType.environmental
            else:
                type_enum = AllergyType.other

            allergies.append(
                AllergyCreate(
                    allergen=str(a["allergen"]),
                    type=type_enum,
                    reaction=a.get("reaction"),
                    severity=a.get("severity"),
                    notes=a.get("notes"),
                )
            )

    # 9. Parse Social & Physical Exam
    social_data = extracted_dict.get("social_history", {})
    social_history = ExtractedSocialHistory(
        smoking_status=social_data.get("smoking_status", "unknown"),
        pack_years=social_data.get("pack_years"),
        alcohol_use=social_data.get("alcohol_use"),
        recreational_drug_use=social_data.get("recreational_drug_use"),
        diet=social_data.get("diet"),
        exercise=social_data.get("exercise"),
        living_situation=social_data.get("living_situation"),
        occupational_exposure=social_data.get("occupational_exposure"),
        travel_history=social_data.get("travel_history"),
        sleep=social_data.get("sleep"),
    )

    def _norm_sign(v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip().lower()
        if not s or s in {"-", "none", "null", "not assessed", ""}:
            return None
        if s in {"absent", "no", "negative", "normal", "nil", "0"}:
            return "absent"
        if s in {
            "present", "yes", "positive", "abnormal", "mild", "moderate",
            "severe", "trace", "1+", "2+", "3+", "4+",
        }:
            return "present"
        return None

    exam_data = extracted_dict.get("physical_exam", {})
    physical_exam = ExtractedExamFindings(
        pallor=_norm_sign(exam_data.get("pallor")),
        edema=_norm_sign(exam_data.get("edema")),
        cyanosis=_norm_sign(exam_data.get("cyanosis")),
        clubbing=_norm_sign(exam_data.get("clubbing")),
        lymphadenopathy=_norm_sign(exam_data.get("lymphadenopathy")),
        dehydration=_norm_sign(exam_data.get("dehydration")),
        extra_notes=exam_data.get("extra_notes"),
    )

    return ExtractedClinicalCase(
        summary=extracted_dict.get("summary", "Clinical note successfully extracted."),
        demographics=demographics,
        visit_info=visit_info,
        hpi=hpi,
        vitals=vitals,
        symptoms_present=symptoms_present,
        symptoms_absent=symptoms_absent,
        medical_history=history_entries,
        medications=medications,
        allergies=allergies,
        social_history=social_history,
        physical_exam=physical_exam,
        working_notes=raw_note,
    )
