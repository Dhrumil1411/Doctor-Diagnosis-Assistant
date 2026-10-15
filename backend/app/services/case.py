import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.allergies import Allergy
from app.models.general_exam import GeneralExam
from app.models.lab_results import LabResult
from app.models.medical_history import MedicalHistory
from app.models.medications import Medication
from app.models.patients import Patient
from app.models.social_history import SocialHistory
from app.models.symptoms import Symptom, SymptomStatus
from app.models.visits import Visit
from app.models.vitals import Vitals
from app.services.symptom_mapper import get_symptom_mapper


def _patient_age(patient: Patient) -> int | None:
    if patient.date_of_birth is None:
        return None
    today = patient.date_of_birth.today()
    return today.year - patient.date_of_birth.year - (
        (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
    )


def assemble_case(db: Session, visit_id: uuid.UUID) -> dict:
    visit = db.get(Visit, visit_id)
    if visit is None:
        raise LookupError(f"visit {visit_id} not found")
    patient = db.get(Patient, visit.patient_id)
    mapper = get_symptom_mapper()

    raw_present_symptoms = db.scalars(
        select(Symptom).where(
            Symptom.visit_id == visit.id, Symptom.status == SymptomStatus.present
        )
    ).all()

    symptoms = []
    for s in raw_present_symptoms:
        resolved = mapper.resolve_symptom(s.name)
        symptoms.append({
            "name": s.name,
            "canonical_name": resolved.get("feature_id") or s.name,
            "hpo_id": resolved.get("hpo_id") or s.code,
            "hpo_label": resolved.get("hpo_label"),
            "category": resolved.get("category"),
            "severity": s.severity,
            "duration": s.duration,
        })

    absent_raw = db.scalars(
        select(Symptom).where(
            Symptom.visit_id == visit.id, Symptom.status == SymptomStatus.absent
        )
    ).all()
    absent = []
    for s in absent_raw:
        resolved = mapper.resolve_symptom(s.name)
        absent.append({
            "name": s.name,
            "canonical_name": resolved.get("feature_id") or s.name,
            "hpo_id": resolved.get("hpo_id") or s.code,
        })
    absent_names = [s["name"] for s in absent]

    unsure_raw = db.scalars(
        select(Symptom).where(
            Symptom.visit_id == visit.id, Symptom.status == SymptomStatus.unsure
        )
    ).all()
    unsure = [s.name for s in unsure_raw]

    vitals_row = db.scalar(select(Vitals).where(Vitals.visit_id == visit.id))
    vitals = None
    if vitals_row is not None:
        vitals = {
            k: getattr(vitals_row, k)
            for k in (
                "temperature_c",
                "systolic_bp",
                "diastolic_bp",
                "heart_rate",
                "respiratory_rate",
                "spo2",
                "blood_glucose_mg_dl",
                "pain_score",
            )
            if getattr(vitals_row, k) is not None
        }

    social_row = db.scalar(select(SocialHistory).where(SocialHistory.visit_id == visit.id))
    social = None
    if social_row is not None:
        social = {
            k: str(getattr(social_row, k)) if k == "lmp_date" else getattr(social_row, k)
            for k in (
                "smoking_status",
                "pack_years",
                "alcohol_use",
                "recreational_drug_use",
                "diet",
                "exercise",
                "living_situation",
                "occupational_exposure",
                "travel_history",
                "sexual_history",
                "sleep",
                "bowel_movements",
                "bladder_frequency",
                "addictions",
                "menstrual_history",
                "lmp_date",
            )
            if getattr(social_row, k) is not None
        }

    exam_row = db.scalar(select(GeneralExam).where(GeneralExam.visit_id == visit.id))
    general_exam = None
    if exam_row is not None:
        general_exam = {
            k: getattr(exam_row, k)
            for k in (
                "pallor", "edema", "cyanosis", "clubbing",
                "lymphadenopathy", "dehydration", "extra_notes",
            )
            if getattr(exam_row, k) is not None
        }

    history = [
        {
            "category": h.category.value,
            "name": h.name,
            "onset_year": h.onset_year,
            "resolved": h.resolved,
        }
        for h in db.scalars(
            select(MedicalHistory).where(MedicalHistory.patient_id == patient.id)
        ).all()
    ]
    medications = [
        {
            "name": m.name,
            "dose": m.dose,
            "frequency": m.frequency,
            "is_active": m.is_active,
        }
        for m in db.scalars(
            select(Medication).where(Medication.patient_id == patient.id)
        ).all()
    ]
    allergies = [
        {"allergen": a.allergen, "type": a.type.value, "reaction": a.reaction}
        for a in db.scalars(
            select(Allergy).where(Allergy.patient_id == patient.id)
        ).all()
    ]
    labs = [
        {
            "category": l.category.value,
            "test_name": l.test_name,
            "result_summary": l.result_summary,
            "performed_at": str(l.performed_at) if l.performed_at else None,
            "has_file": bool(l.file_path),
        }
        for l in db.scalars(
            select(LabResult).where(LabResult.visit_id == visit.id).order_by(LabResult.id.asc())
        ).all()
    ]

    patient_block = {
        "age": _patient_age(patient),
        "sex": patient.sex.value,
        "gender_identity": patient.gender_identity,
        "weight_kg": float(patient.weight_kg) if patient.weight_kg else None,
        "height_cm": float(patient.height_cm) if patient.height_cm else None,
        "occupation": patient.occupation,
    }

    visit_block = {
        "type": visit.visit_type.value,
        "chief_complaint": visit.chief_complaint,
        "complaint_duration": visit.complaint_duration,
        "severity_score_1_to_10": visit.severity_score,
        "progression": visit.progression.value if visit.progression else None,
        "hpi_onset": visit.hpi_onset,
        "hpi_location": visit.hpi_location,
        "hpi_character": visit.hpi_character,
        "hpi_aggravating_factors": visit.hpi_aggravating_factors,
        "hpi_relieving_factors": visit.hpi_relieving_factors,
        "hpi_radiation": visit.hpi_radiation,
        "hpi_timing": visit.hpi_timing,
        "working_notes": visit.working_notes,
    }

    # DDXPlus Clinical Ontological Structure (Antecedents vs Active Evidences vs Pertinent Negatives)
    antecedents = {
        "demographics": patient_block,
        "past_medical_history": history,
        "current_medications": medications,
        "known_allergies": allergies,
        "social_and_risk_factors": social,
    }

    active_evidences = {
        "chief_complaint_and_hpi": visit_block,
        "presenting_symptoms_with_hpo": symptoms,
        "vital_signs": vitals,
        "physical_examination": general_exam,
        "diagnostic_labs_and_imaging": labs,
    }

    pertinent_negatives = {
        "absent_symptoms": absent,
        "unsure_symptoms": unsure,
    }

    return {
        # Backward-compatible top-level keys
        "patient": patient_block,
        "visit": visit_block,
        "symptoms_present": symptoms,
        "symptoms_absent": absent_names,
        "symptoms_unsure": unsure,
        "vitals": vitals,
        "social_history": social,
        "general_exam": general_exam,
        "lab_results": labs,
        "medical_history": history,
        "medications": medications,
        "allergies": allergies,
        # DDXPlus Structured Evidence Blocks
        "antecedents": antecedents,
        "active_evidences": active_evidences,
        "pertinent_negatives": pertinent_negatives,
    }
