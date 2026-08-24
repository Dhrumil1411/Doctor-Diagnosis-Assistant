import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.social_history import SmokingStatus
from app.models.symptoms import SymptomStatus
from app.models.visits import Progression, VisitType


class SymptomEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=32)
    status: SymptomStatus = SymptomStatus.present
    severity: int | None = Field(default=None, ge=1, le=10)
    duration: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class SymptomEntryRead(SymptomEntryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID


class VitalsUpsert(BaseModel):
    temperature_c: float | None = Field(default=None, ge=25, le=45)
    systolic_bp: int | None = Field(default=None, ge=50, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=300)
    respiratory_rate: int | None = Field(default=None, ge=4, le=80)
    spo2: float | None = Field(default=None, ge=50, le=100)
    blood_glucose_mg_dl: int | None = Field(default=None, ge=10, le=1500)
    pain_score: int | None = Field(default=None, ge=0, le=10)

    @model_validator(mode="after")
    def check_bp(self) -> "VitalsUpsert":
        if (
            self.systolic_bp is not None
            and self.diastolic_bp is not None
            and self.diastolic_bp >= self.systolic_bp
        ):
            raise ValueError("diastolic_bp must be lower than systolic_bp")
        return self


class VitalsRead(VitalsUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID


class SocialHistoryUpsert(BaseModel):
    smoking_status: SmokingStatus = SmokingStatus.unknown
    pack_years: int | None = Field(default=None, ge=0, le=200)
    alcohol_use: str | None = Field(default=None, max_length=64)
    recreational_drug_use: str | None = Field(default=None, max_length=120)
    diet: str | None = Field(default=None, max_length=120)
    exercise: str | None = Field(default=None, max_length=120)
    living_situation: str | None = Field(default=None, max_length=255)
    occupational_exposure: str | None = Field(default=None, max_length=255)
    travel_history: str | None = None
    sexual_history: str | None = None


class SocialHistoryRead(SocialHistoryUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID


class VisitCreate(BaseModel):
    patient_id: uuid.UUID
    visit_type: VisitType
    occurred_at: datetime | None = None
    attending_doctor_id: uuid.UUID | None = None
    referring_doctor_name: str | None = Field(default=None, max_length=255)
    chief_complaint: str | None = None
    complaint_duration: str | None = Field(default=None, max_length=64)
    severity_score: int | None = Field(default=None, ge=1, le=10)
    progression: Progression | None = None
    hpi_onset: str | None = Field(default=None, max_length=64)
    hpi_location: str | None = Field(default=None, max_length=120)
    hpi_character: str | None = Field(default=None, max_length=120)
    hpi_aggravating_factors: str | None = None
    hpi_relieving_factors: str | None = None
    hpi_radiation: str | None = Field(default=None, max_length=120)
    hpi_timing: str | None = Field(default=None, max_length=120)
    working_notes: str | None = None


class VisitUpdate(BaseModel):
    visit_type: VisitType | None = None
    occurred_at: datetime | None = None
    attending_doctor_id: uuid.UUID | None = None
    referring_doctor_name: str | None = Field(default=None, max_length=255)
    chief_complaint: str | None = None
    complaint_duration: str | None = Field(default=None, max_length=64)
    severity_score: int | None = Field(default=None, ge=1, le=10)
    progression: Progression | None = None
    hpi_onset: str | None = Field(default=None, max_length=64)
    hpi_location: str | None = Field(default=None, max_length=120)
    hpi_character: str | None = Field(default=None, max_length=120)
    hpi_aggravating_factors: str | None = None
    hpi_relieving_factors: str | None = None
    hpi_radiation: str | None = Field(default=None, max_length=120)
    hpi_timing: str | None = Field(default=None, max_length=120)
    working_notes: str | None = None


class VisitRead(VisitCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class VisitDetail(VisitRead):
    symptoms: list[SymptomEntryRead] = []
    vitals: VitalsRead | None = None
    social_history: SocialHistoryRead | None = None
