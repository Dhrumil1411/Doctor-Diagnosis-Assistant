import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class VisitType(str, enum.Enum):
    new = "new"
    follow_up = "follow_up"
    emergency = "emergency"
    telehealth = "telehealth"


class Progression(str, enum.Enum):
    improving = "improving"
    worsening = "worsening"
    stable = "stable"
    fluctuating = "fluctuating"


class Visit(TimestampMixin, Base):
    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint("severity_score BETWEEN 1 AND 10", name="severity_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visit_type: Mapped[VisitType] = mapped_column(
        Enum(VisitType, name="visit_type", native_enum=False), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    attending_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    referring_doctor_name: Mapped[str | None] = mapped_column(String(255))
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    complaint_duration: Mapped[str | None] = mapped_column(String(64))
    severity_score: Mapped[int | None] = mapped_column(SmallInteger)
    progression: Mapped[Progression | None] = mapped_column(
        Enum(Progression, name="progression", native_enum=False)
    )
    hpi_onset: Mapped[str | None] = mapped_column(String(64))
    hpi_location: Mapped[str | None] = mapped_column(String(120))
    hpi_character: Mapped[str | None] = mapped_column(String(120))
    hpi_aggravating_factors: Mapped[str | None] = mapped_column(Text)
    hpi_relieving_factors: Mapped[str | None] = mapped_column(Text)
    hpi_radiation: Mapped[str | None] = mapped_column(String(120))
    hpi_timing: Mapped[str | None] = mapped_column(String(120))
    working_notes: Mapped[str | None] = mapped_column(Text)
