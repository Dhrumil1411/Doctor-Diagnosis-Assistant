import uuid
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.clinical import AllergyCreate, HistoryEntryCreate, MedicationCreate


class ExtractNoteRequest(BaseModel):
    raw_note: str = Field(min_length=5, description="Unformatted clinical note or consultation transcript")


class ExtractedDemographics(BaseModel):
    full_name: str | None = None
    age_years: int | None = None
    date_of_birth: str | None = None
    sex: str | None = "unknown"  # "male" | "female" | "other" | "unknown"
    weight_kg: float | None = None
    height_cm: float | None = None
    occupation: str | None = None


class ExtractedVisitInfo(BaseModel):
    chief_complaint: str | None = None
    complaint_duration: str | None = None
    severity_score: int | None = Field(default=None, ge=1, le=10)
    progression: str | None = None  # "improving" | "stable" | "worsening" | "fluctuating"


class ExtractedHpi(BaseModel):
    hpi_onset: str | None = None
    hpi_location: str | None = None
    hpi_character: str | None = None
    hpi_aggravating_factors: str | None = None
    hpi_relieving_factors: str | None = None
    hpi_radiation: str | None = None
    hpi_timing: str | None = None


class ExtractedVitals(BaseModel):
    temperature_c: float | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    heart_rate: int | None = None
    respiratory_rate: int | None = None
    spo2: float | None = None
    blood_glucose_mg_dl: float | None = None
    pain_score: int | None = Field(default=None, ge=0, le=10)


class ExtractedSymptomItem(BaseModel):
    name: str
    canonical_id: str | None = None
    hpo_id: str | None = None
    hpo_label: str | None = None
    category: str | None = None
    status: str = "present"  # "present" | "absent"
    confidence: float = 1.0


class ExtractedSocialHistory(BaseModel):
    smoking_status: str | None = "unknown"
    pack_years: float | None = None
    alcohol_use: str | None = None
    recreational_drug_use: str | None = None
    diet: str | None = None
    exercise: str | None = None
    living_situation: str | None = None
    occupational_exposure: str | None = None
    travel_history: str | None = None
    sleep: str | None = None


class ExtractedExamFindings(BaseModel):
    pallor: str | None = None
    edema: str | None = None
    cyanosis: str | None = None
    clubbing: str | None = None
    lymphadenopathy: str | None = None
    dehydration: str | None = None
    extra_notes: str | None = None


class ExtractedClinicalCase(BaseModel):
    summary: str
    demographics: ExtractedDemographics = Field(default_factory=ExtractedDemographics)
    visit_info: ExtractedVisitInfo = Field(default_factory=ExtractedVisitInfo)
    hpi: ExtractedHpi = Field(default_factory=ExtractedHpi)
    vitals: ExtractedVitals = Field(default_factory=ExtractedVitals)
    symptoms_present: list[ExtractedSymptomItem] = []
    symptoms_absent: list[ExtractedSymptomItem] = []
    medical_history: list[HistoryEntryCreate] = []
    medications: list[MedicationCreate] = []
    allergies: list[AllergyCreate] = []
    social_history: ExtractedSocialHistory = Field(default_factory=ExtractedSocialHistory)
    physical_exam: ExtractedExamFindings = Field(default_factory=ExtractedExamFindings)
    working_notes: str | None = None
