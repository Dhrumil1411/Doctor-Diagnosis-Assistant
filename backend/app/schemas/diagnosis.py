import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.diagnoses import ConfidenceBand, DiagnosisSource, DoctorDecision


class DiagnosisDecisionCreate(BaseModel):
    doctor_decision: DoctorDecision
    disease_label: str = Field(min_length=1, max_length=200)
    edited_label: str | None = Field(default=None, max_length=200)
    reasoning: str | None = None
    source: DiagnosisSource = DiagnosisSource.llm
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_band: ConfidenceBand | None = None
    suggested_next_steps: str | None = None


class DiagnosisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    visit_id: uuid.UUID
    source: DiagnosisSource
    disease_label: str
    confidence: float | None = None
    confidence_band: ConfidenceBand | None = None
    reasoning: str | None = None
    suggested_next_steps: str | None = None
    doctor_decision: DoctorDecision | None = None
    edited_label: str | None = None
    decided_at: datetime | None = None
