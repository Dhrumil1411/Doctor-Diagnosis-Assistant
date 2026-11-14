"""Idempotent seed script for public demo deployments.

Creates:
- 3 Demo accounts (Doctor, Read-Only, Admin) with environment-configurable passwords
- 6 Clearly synthetic patient cases with realistic clinical visits, vitals, and symptoms

Safe to run repeatedly; existing accounts and records are detected and updated rather than duplicated.
"""

from datetime import date, datetime, timezone
import os
from pathlib import Path
import sys

# Ensure backend package can be imported
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.security import hash_password
import app.models  # noqa: F401
from app.db.base import Base, SessionLocal, engine
from app.models.diagnoses import ConfidenceBand, Diagnosis, DiagnosisSource, DoctorDecision
from app.models.patients import Patient, Sex
from app.models.symptoms import Symptom, SymptomStatus
from app.models.users import User, UserRole
from app.models.visits import Progression, Visit, VisitType
from app.models.vitals import Vitals

DEMO_USERS = [
    {
        "email": "demo.doctor@example.com",
        "full_name": "Dr. Demo Doctor",
        "role": UserRole.doctor,
        "env_var": "DEMO_DOCTOR_PASSWORD",
        "default_pass": "DoctorDemo123!",
    },
    {
        "email": "demo.readonly@example.com",
        "full_name": "Demo Clinical Observer",
        "role": UserRole.read_only,
        "env_var": "DEMO_READONLY_PASSWORD",
        "default_pass": "ReadOnlyDemo123!",
    },
    {
        "email": "demo.admin@example.com",
        "full_name": "Demo Administrator",
        "role": UserRole.admin,
        "env_var": "DEMO_ADMIN_PASSWORD",
        "default_pass": "AdminDemo123!",
    },
]

DEMO_PATIENTS = [
    {
        "mrn": "DEMO-SYNTH-001",
        "full_name": "Demo Patient 01 (Synthetic)",
        "date_of_birth": date(1980, 5, 14),
        "sex": Sex.male,
        "weight_kg": 76.5,
        "height_cm": 178.0,
        "occupation": "Software Engineer",
        "chief_complaint": "Persistent dry cough, mild shortness of breath, and low-grade evening fever for 5 days.",
        "complaint_duration": "5 days",
        "severity_score": 6,
        "progression": Progression.worsening,
        "vitals": {
            "temperature_c": 38.1,
            "systolic_bp": 122,
            "diastolic_bp": 80,
            "heart_rate": 86,
            "respiratory_rate": 18,
            "spo2": 96.5,
            "pain_score": 3,
        },
        "symptoms": [
            ("cough", SymptomStatus.present, 6, "Frequent bouts of non-productive cough"),
            ("shortness of breath", SymptomStatus.present, 4, "Mild exertional breathlessness"),
            ("fever", SymptomStatus.present, 5, "Temperature up to 38.2C in evenings"),
            ("sharp chest pain", SymptomStatus.absent, 0, "No pleuritic or radiating chest pain"),
        ],
        "diagnosis": {
            "condition": "Acute Bronchitis",
            "reasoning": "Clinical presentation and vital signs consistent with acute viral bronchitis.",
        },
    },
    {
        "mrn": "DEMO-SYNTH-002",
        "full_name": "Demo Patient 02 (Synthetic)",
        "date_of_birth": date(1964, 11, 23),
        "sex": Sex.female,
        "weight_kg": 68.0,
        "height_cm": 162.0,
        "occupation": "Retired Teacher",
        "chief_complaint": "Gradual exertional dyspnea, fatigue, and bilateral ankle swelling over past 3 weeks.",
        "complaint_duration": "3 weeks",
        "severity_score": 7,
        "progression": Progression.worsening,
        "vitals": {
            "temperature_c": 36.8,
            "systolic_bp": 146,
            "diastolic_bp": 92,
            "heart_rate": 78,
            "respiratory_rate": 20,
            "spo2": 94.5,
            "pain_score": 2,
        },
        "symptoms": [
            ("fatigue", SymptomStatus.present, 7, "Progressive generalized weakness"),
            ("shortness of breath", SymptomStatus.present, 7, "Dyspnea on climbing one flight of stairs"),
            ("chest tightness", SymptomStatus.present, 5, "Substernal pressure sensation without radiation"),
            ("dizziness", SymptomStatus.present, 3, "Occasional postural lightheadedness"),
        ],
        "diagnosis": {
            "condition": "Congestive Heart Failure (Mild/Moderate)",
            "reasoning": "Fluid overload signs with bilateral peripheral edema and reduced exercise tolerance.",
        },
    },
    {
        "mrn": "DEMO-SYNTH-003",
        "full_name": "Demo Patient 03 (Synthetic)",
        "date_of_birth": date(1996, 8, 3),
        "sex": Sex.male,
        "weight_kg": 72.0,
        "height_cm": 181.0,
        "occupation": "Graphic Designer",
        "chief_complaint": "Sharp right lower quadrant abdominal pain, anorexia, and low fever starting 12 hours ago.",
        "complaint_duration": "12 hours",
        "severity_score": 8,
        "progression": Progression.worsening,
        "vitals": {
            "temperature_c": 38.3,
            "systolic_bp": 118,
            "diastolic_bp": 74,
            "heart_rate": 98,
            "respiratory_rate": 20,
            "spo2": 99.0,
            "pain_score": 8,
        },
        "symptoms": [
            ("abdominal pain", SymptomStatus.present, 8, "Periumbilical pain migrating to right iliac fossa"),
            ("nausea", SymptomStatus.present, 6, "Persistent nausea since morning"),
            ("fever", SymptomStatus.present, 5, "Low-grade pyrexia"),
        ],
        "diagnosis": None,
    },
    {
        "mrn": "DEMO-SYNTH-004",
        "full_name": "Demo Patient 04 (Synthetic)",
        "date_of_birth": date(1971, 2, 19),
        "sex": Sex.female,
        "weight_kg": 84.0,
        "height_cm": 165.0,
        "occupation": "Accountant",
        "chief_complaint": "Polydipsia, polyuria, unintentional 4 kg weight loss, and blurry vision over past 2 months.",
        "complaint_duration": "2 months",
        "severity_score": 5,
        "progression": Progression.fluctuating,
        "vitals": {
            "temperature_c": 36.6,
            "systolic_bp": 134,
            "diastolic_bp": 86,
            "heart_rate": 82,
            "respiratory_rate": 16,
            "spo2": 98.0,
            "blood_glucose_mg_dl": 235,
            "pain_score": 1,
        },
        "symptoms": [
            ("fatigue", SymptomStatus.present, 6, "Constant afternoon sluggishness"),
            ("dizziness", SymptomStatus.present, 4, "Transient visual blurriness and dizziness"),
            ("headache", SymptomStatus.absent, 0, "No cephalalgia reported"),
        ],
        "diagnosis": None,
    },
    {
        "mrn": "DEMO-SYNTH-005",
        "full_name": "Demo Patient 05 (Synthetic)",
        "date_of_birth": date(1989, 7, 29),
        "sex": Sex.female,
        "weight_kg": 59.0,
        "height_cm": 168.0,
        "occupation": "Research Scientist",
        "chief_complaint": "Throbbing left-sided hemicranial headache with photophobia and nausea for 24 hours.",
        "complaint_duration": "24 hours",
        "severity_score": 7,
        "progression": Progression.stable,
        "vitals": {
            "temperature_c": 36.7,
            "systolic_bp": 114,
            "diastolic_bp": 72,
            "heart_rate": 70,
            "respiratory_rate": 14,
            "spo2": 99.0,
            "pain_score": 7,
        },
        "symptoms": [
            ("headache", SymptomStatus.present, 8, "Unilateral pulsating headache exacerbated by light/sound"),
            ("nausea", SymptomStatus.present, 5, "Associated nausea without emesis"),
            ("fever", SymptomStatus.absent, 0, "Afebrile"),
        ],
        "diagnosis": None,
    },
    {
        "mrn": "DEMO-SYNTH-006",
        "full_name": "Demo Patient 06 (Synthetic)",
        "date_of_birth": date(1975, 10, 11),
        "sex": Sex.male,
        "weight_kg": 81.5,
        "height_cm": 176.0,
        "occupation": "Logistics Coordinator",
        "chief_complaint": "Burning retrosternal discomfort after meals and nocturnal acid regurgitation for 4 weeks.",
        "complaint_duration": "4 weeks",
        "severity_score": 4,
        "progression": Progression.fluctuating,
        "vitals": {
            "temperature_c": 36.6,
            "systolic_bp": 126,
            "diastolic_bp": 82,
            "heart_rate": 72,
            "respiratory_rate": 14,
            "spo2": 98.5,
            "pain_score": 4,
        },
        "symptoms": [
            ("chest tightness", SymptomStatus.present, 4, "Post-prandial burning sensation behind sternum"),
            ("nausea", SymptomStatus.present, 3, "Mild regurgitation and dyspepsia"),
            ("shortness of breath", SymptomStatus.absent, 0, "No respiratory distress"),
        ],
        "diagnosis": None,
    },
]


def seed_demo() -> dict[str, int]:
    """Idempotently seeds demo users and synthetic patient cases.

    Returns a summary dict with counts of created/updated entities.
    """
    # Ensure tables exist (e.g. for standalone execution or testing)
    Base.metadata.create_all(bind=engine)

    stats = {"users_seeded": 0, "patients_seeded": 0, "visits_seeded": 0}

    with SessionLocal() as db:
        user_map: dict[str, User] = {}

        # 1. Seed or update demo accounts
        for u_data in DEMO_USERS:
            email = u_data["email"].lower()
            password = os.getenv(u_data["env_var"], u_data["default_pass"])

            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=u_data["full_name"],
                    role=u_data["role"],
                    is_active=True,
                )
                db.add(user)
                db.flush()
            else:
                user.hashed_password = hash_password(password)
                user.full_name = u_data["full_name"]
                user.role = u_data["role"]
                user.is_active = True
                db.flush()

            user_map[u_data["role"].value] = user
            stats["users_seeded"] += 1

        doctor = user_map.get(UserRole.doctor.value)

        # 2. Seed synthetic patient cases
        for p_info in DEMO_PATIENTS:
            mrn = p_info["mrn"]
            patient = db.scalar(select(Patient).where(Patient.mrn == mrn))

            if patient is None:
                patient = Patient(
                    mrn=mrn,
                    full_name=p_info["full_name"],
                    date_of_birth=p_info["date_of_birth"],
                    sex=p_info["sex"],
                    weight_kg=p_info["weight_kg"],
                    height_cm=p_info["height_cm"],
                    occupation=p_info["occupation"],
                    consent_given=True,
                    consent_recorded_at=datetime.now(timezone.utc),
                    created_by_id=doctor.id if doctor else None,
                )
                db.add(patient)
                db.flush()
                stats["patients_seeded"] += 1
            else:
                patient.full_name = p_info["full_name"]
                patient.weight_kg = p_info["weight_kg"]
                patient.height_cm = p_info["height_cm"]
                patient.consent_given = True
                db.flush()

            # Ensure a visit exists for the synthetic patient
            visit = db.scalar(select(Visit).where(Visit.patient_id == patient.id))
            if visit is None:
                visit = Visit(
                    patient_id=patient.id,
                    visit_type=VisitType.new,
                    chief_complaint=p_info["chief_complaint"],
                    complaint_duration=p_info["complaint_duration"],
                    severity_score=p_info["severity_score"],
                    progression=p_info["progression"],
                    attending_doctor_id=doctor.id if doctor else None,
                )
                db.add(visit)
                db.flush()
                stats["visits_seeded"] += 1

                # Add vitals
                v_data = p_info["vitals"]
                vitals = Vitals(
                    visit_id=visit.id,
                    temperature_c=v_data.get("temperature_c"),
                    systolic_bp=v_data.get("systolic_bp"),
                    diastolic_bp=v_data.get("diastolic_bp"),
                    heart_rate=v_data.get("heart_rate"),
                    respiratory_rate=v_data.get("respiratory_rate"),
                    spo2=v_data.get("spo2"),
                    blood_glucose_mg_dl=v_data.get("blood_glucose_mg_dl"),
                    pain_score=v_data.get("pain_score"),
                    recorded_at=datetime.now(timezone.utc),
                )
                db.add(vitals)

                # Add symptoms
                for s_name, s_status, s_sev, s_notes in p_info["symptoms"]:
                    symptom = Symptom(
                        visit_id=visit.id,
                        name=s_name,
                        status=s_status,
                        severity=s_sev,
                        notes=s_notes,
                    )
                    db.add(symptom)

                # Optional diagnosis
                if p_info.get("diagnosis"):
                    diag = Diagnosis(
                        visit_id=visit.id,
                        source=DiagnosisSource.doctor,
                        rank=1,
                        disease_label=p_info["diagnosis"]["condition"],
                        confidence=0.92,
                        confidence_band=ConfidenceBand.high,
                        reasoning=p_info["diagnosis"]["reasoning"],
                        doctor_decision=DoctorDecision.accepted,
                        decided_at=datetime.now(timezone.utc),
                    )
                    db.add(diag)

        db.commit()

    return stats


def main() -> int:
    print("Seeding demo accounts and synthetic patients...")
    stats = seed_demo()
    print(f"Demo seed complete: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
