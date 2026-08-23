import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DiagnosisSource(str, enum.Enum):
    classifier = "classifier"
    llm = "llm"
    doctor = "doctor"


class ConfidenceBand(str, enum.Enum):
    high = "high"
    moderate = "moderate"
    low = "low"


class DoctorDecision(str, enum.Enum):
    accepted = "accepted"
    edited = "edited"
    rejected = "rejected"


class Diagnosis(TimestampMixin, Base):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[DiagnosisSource] = mapped_column(
        Enum(DiagnosisSource, name="diagnosis_source", native_enum=False), nullable=False
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    disease_label: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    confidence_band: Mapped[ConfidenceBand | None] = mapped_column(
        Enum(ConfidenceBand, name="confidence_band", native_enum=False)
    )
    reasoning: Mapped[str | None] = mapped_column(Text)
    suggested_next_steps: Mapped[str | None] = mapped_column(Text)
    red_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    doctor_decision: Mapped[DoctorDecision | None] = mapped_column(
        Enum(DoctorDecision, name="doctor_decision", native_enum=False)
    )
    edited_label: Mapped[str | None] = mapped_column(String(200))
    accepted_suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="SET NULL"), use_alter=True
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
