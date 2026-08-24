import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.patients import Sex
from app.schemas.clinical import AllergyRead, HistoryEntryRead, MedicationRead


def _reject_future_dob(dob: date | None) -> date | None:
    if dob is not None and dob > date.today():
        raise ValueError("date_of_birth cannot be in the future")
    return dob


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    mrn: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    sex: Sex = Sex.unknown
    gender_identity: str | None = Field(default=None, max_length=64)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    occupation: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = None
    address: str | None = None
    consent_given: bool = False

    @model_validator(mode="after")
    def check_dob(self) -> "PatientCreate":
        _reject_future_dob(self.date_of_birth)
        return self


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    mrn: str | None = Field(default=None, max_length=64)
    date_of_birth: date | None = None
    sex: Sex | None = None
    gender_identity: str | None = Field(default=None, max_length=64)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    height_cm: float | None = Field(default=None, gt=0, le=300)
    occupation: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = None
    address: str | None = None
    consent_given: bool | None = None

    @model_validator(mode="after")
    def check_dob(self) -> "PatientUpdate":
        _reject_future_dob(self.date_of_birth)
        return self


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class PatientDetail(PatientRead):
    allergies: list[AllergyRead] = []
    history: list[HistoryEntryRead] = []
    medications: list[MedicationRead] = []
