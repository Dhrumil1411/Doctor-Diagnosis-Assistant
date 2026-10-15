"""Loader and parser for Synthea synthetic patient data.

Converts Synthea CSV records (patients, encounters, conditions, observations,
medications, allergies) into standardized Doctor Diagnosis Assistant payload format
for end-to-end clinical workflow testing.
"""

from __future__ import annotations

import csv
from datetime import datetime, date
from pathlib import Path
from typing import Any


def get_synthea_data_dir() -> Path:
    # Look for Data/Synthea relative to repo root or backend
    candidates = [
        Path(__file__).resolve().parents[3] / "Data" / "Synthea",
        Path("Data/Synthea").resolve(),
        Path("../Data/Synthea").resolve(),
    ]
    for p in candidates:
        if p.exists() and (p / "patients.csv").exists():
            return p
    return candidates[0]


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    try:
        if "T" in val:
            val = val.split("T")[0]
        return datetime.strptime(val.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def load_synthea_cases(limit: int = 5) -> list[dict[str, Any]]:
    """Load a structured batch of clinical cases from Synthea CSV files."""
    synthea_dir = get_synthea_data_dir()
    if not synthea_dir.exists():
        return []

    # 1. Load Patients
    patients_file = synthea_dir / "patients.csv"
    patients: dict[str, dict[str, Any]] = {}
    if patients_file.exists():
        with open(patients_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["Id"]
                gender = "male" if row.get("GENDER") == "M" else ("female" if row.get("GENDER") == "F" else "unknown")
                # Remove digits from Synthea synthetic names
                first = "".join(c for c in row.get("FIRST", "John") if not c.isdigit())
                last = "".join(c for c in row.get("LAST", "Doe") if not c.isdigit())
                patients[pid] = {
                    "id": pid,
                    "full_name": f"{first} {last}".strip(),
                    "date_of_birth": _parse_date(row.get("BIRTHDATE")),
                    "sex": gender,
                    "mrn": f"SYN-{pid[:8].upper()}",
                    "address": f"{row.get('ADDRESS', '')}, {row.get('CITY', '')}, {row.get('STATE', '')}".strip(" ,"),
                    "consent_given": True,
                }

    # 2. Load Encounters
    encounters_file = synthea_dir / "encounters.csv"
    encounters: list[dict[str, Any]] = []
    if encounters_file.exists():
        with open(encounters_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["PATIENT"]
                if pid in patients:
                    encounters.append(row)

    # 3. Load Conditions
    conditions_file = synthea_dir / "conditions.csv"
    conditions_by_patient: dict[str, list[dict[str, Any]]] = {}
    if conditions_file.exists():
        with open(conditions_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["PATIENT"]
                conditions_by_patient.setdefault(pid, []).append(row)

    # 4. Load Observations (Vitals & Labs)
    obs_file = synthea_dir / "observations.csv"
    obs_by_encounter: dict[str, list[dict[str, Any]]] = {}
    if obs_file.exists():
        with open(obs_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                enc_id = row.get("ENCOUNTER")
                if enc_id:
                    obs_by_encounter.setdefault(enc_id, []).append(row)

    # 5. Load Medications
    meds_file = synthea_dir / "medications.csv"
    meds_by_patient: dict[str, list[dict[str, Any]]] = {}
    if meds_file.exists():
        with open(meds_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["PATIENT"]
                meds_by_patient.setdefault(pid, []).append(row)

    # 6. Load Allergies
    allergies_file = synthea_dir / "allergies.csv"
    allergies_by_patient: dict[str, list[dict[str, Any]]] = {}
    if allergies_file.exists():
        with open(allergies_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row["PATIENT"]
                allergies_by_patient.setdefault(pid, []).append(row)

    # Assemble cases prioritizing encounters with rich observations and conditions
    assembled_cases = []
    seen_patients = set()

    for enc in encounters:
        enc_id = enc["Id"]
        pid = enc["PATIENT"]
        if pid in seen_patients:
            continue

        p_data = patients.get(pid)
        if not p_data:
            continue

        p_obs = obs_by_encounter.get(enc_id, [])
        p_conds = conditions_by_patient.get(pid, [])
        p_meds = meds_by_patient.get(pid, [])
        p_allergies = allergies_by_patient.get(pid, [])

        # Parse vitals & labs from observations
        vitals: dict[str, Any] = {}
        labs: list[dict[str, Any]] = []

        for obs in p_obs:
            desc = (obs.get("DESCRIPTION") or "").lower()
            code = obs.get("CODE")
            val_str = obs.get("VALUE")
            units = obs.get("UNITS", "")
            try:
                val_float = float(val_str) if val_str is not None else None
            except ValueError:
                val_float = None

            if "systolic blood pressure" in desc or code == "8480-6":
                if val_float:
                    vitals["systolic_bp"] = int(val_float)
            elif "diastolic blood pressure" in desc or code == "8462-4":
                if val_float:
                    vitals["diastolic_bp"] = int(val_float)
            elif "heart rate" in desc or code == "8867-4":
                if val_float:
                    vitals["heart_rate"] = int(val_float)
            elif "respiratory rate" in desc or code == "9279-1":
                if val_float:
                    vitals["respiratory_rate"] = int(val_float)
            elif "body temperature" in desc or code == "8310-5":
                if val_float:
                    vitals["temperature_c"] = round(val_float, 1)
            elif "oxygen saturation" in desc or code in ("2708-6", "59408-5"):
                if val_float:
                    vitals["spo2"] = round(val_float, 1)
            elif "pain severity" in desc or code == "72514-3":
                if val_float:
                    vitals["pain_score"] = int(min(10, max(0, val_float)))
            elif "glucose" in desc or code == "2339-0":
                if val_float:
                    vitals["blood_glucose_mg_dl"] = int(val_float)
            elif "body height" in desc or code == "8302-2":
                if val_float:
                    p_data["height_cm"] = round(val_float, 1)
            elif "body weight" in desc or code == "29463-7":
                if val_float:
                    p_data["weight_kg"] = round(val_float, 1)
            elif obs.get("CATEGORY") == "laboratory" and val_str:
                test_name = obs.get("DESCRIPTION") or "Laboratory Test"
                labs.append({
                    "category": "blood",
                    "test_name": test_name,
                    "result_summary": f"{val_str} {units}".strip(),
                })

        # Ensure valid systolic/diastolic pair if present
        if "systolic_bp" in vitals and "diastolic_bp" in vitals:
            if vitals["diastolic_bp"] >= vitals["systolic_bp"]:
                vitals["diastolic_bp"] = vitals["systolic_bp"] - 40

        # Extract Chief complaint & conditions
        active_conditions = [c.get("DESCRIPTION", "") for c in p_conds if c.get("DESCRIPTION")]
        chief_complaint = (
            enc.get("DESCRIPTION")
            or (active_conditions[0] if active_conditions else "Routine Evaluation")
        )

        medication_list = [
            {"name": m.get("DESCRIPTION", "Medication"), "status": "active"}
            for m in p_meds[:5]
        ]
        allergy_list = [
            {"allergen": a.get("DESCRIPTION", "Unknown Allergen"), "allergy_type": "drug"}
            for a in p_allergies[:3]
        ]
        history_list = [
            {"condition_name": c, "status": "active"}
            for c in active_conditions[:5]
        ]

        # Convert active conditions/symptoms to simple symptom names
        symptoms = []
        for cond in active_conditions:
            cond_lower = cond.lower()
            if "sinusitis" in cond_lower:
                symptoms.extend(["headache", "nasal_congestion", "sinus_pain"])
            elif "anemia" in cond_lower:
                symptoms.extend(["fatigue", "weakness_in_limbs"])
            elif "prediabetes" in cond_lower or "diabetes" in cond_lower:
                symptoms.extend(["polyuria", "increased_appetite", "excessive_hunger"])
            elif "hypertension" in cond_lower:
                symptoms.extend(["headache", "dizziness"])
            elif "bronchitis" in cond_lower or "pneumonia" in cond_lower:
                symptoms.extend(["cough", "high_fever", "breathlessness"])

        # Fallback symptom if empty
        if not symptoms:
            symptoms = ["fatigue", "malaise"]

        case = {
            "case_id": f"synthea_{pid[:8]}",
            "source": "Synthea",
            "patient": {
                "full_name": p_data["full_name"],
                "date_of_birth": p_data["date_of_birth"].isoformat() if p_data["date_of_birth"] else "1980-01-01",
                "sex": p_data["sex"],
                "mrn": p_data["mrn"],
                "weight_kg": p_data.get("weight_kg", 72.0),
                "height_cm": p_data.get("height_cm", 175.0),
                "address": p_data["address"] or "123 Boston Way",
                "consent_given": True,
            },
            "visit": {
                "visit_type": "new",
                "chief_complaint": chief_complaint,
                "chief_complaint_duration": "3 days",
                "chief_complaint_severity": 5,
                "chief_complaint_progression": "worsening",
                "hpi_onset": "gradual",
                "hpi_location": "systemic",
                "hpi_character": "dull",
                "notes": f"Synthea simulated clinical encounter {enc_id}.",
            },
            "vitals": vitals or {
                "temperature_c": 37.0,
                "systolic_bp": 120,
                "diastolic_bp": 80,
                "heart_rate": 74,
                "respiratory_rate": 16,
                "spo2": 98.0,
            },
            "symptoms": list(dict.fromkeys(symptoms)),
            "labs": labs[:4],
            "medications": medication_list,
            "allergies": allergy_list,
            "medical_history": history_list,
            "social_history": {
                "smoking_status": "never",
                "alcohol_use": "none",
                "diet": "balanced",
                "exercise": "moderate",
            }
        }

        assembled_cases.append(case)
        seen_patients.add(pid)

        if len(assembled_cases) >= limit:
            break

    return assembled_cases
