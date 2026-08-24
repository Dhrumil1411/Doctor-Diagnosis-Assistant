import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.allergies import AllergyType
from app.models.medical_history import HistoryCategory


class AllergyCreate(BaseModel):
    allergen: str = Field(min_length=1, max_length=200)
    type: AllergyType = AllergyType.other
    reaction: str | None = Field(default=None, max_length=200)
    severity: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class AllergyUpdate(BaseModel):
    allergen: str | None = Field(default=None, min_length=1, max_length=200)
    type: AllergyType | None = None
    reaction: str | None = Field(default=None, max_length=200)
    severity: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class AllergyRead(AllergyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID


class HistoryEntryCreate(BaseModel):
    category: HistoryCategory
    name: str = Field(min_length=1, max_length=200)
    details: str | None = None
    onset_year: int | None = Field(default=None, ge=1900, le=2100)
    resolved: bool = False


class HistoryEntryUpdate(BaseModel):
    category: HistoryCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    details: str | None = None
    onset_year: int | None = Field(default=None, ge=1900, le=2100)
    resolved: bool | None = None


class HistoryEntryRead(HistoryEntryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID


class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    is_active: bool = True
    started_on: date | None = None
    stopped_on: date | None = None
    notes: str | None = None


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    started_on: date | None = None
    stopped_on: date | None = None
    notes: str | None = None


class MedicationRead(MedicationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
