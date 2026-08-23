import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HistoryCategory(str, enum.Enum):
    chronic_condition = "chronic_condition"
    surgery = "surgery"
    hospitalization = "hospitalization"
    immunization = "immunization"
    family_history = "family_history"


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[HistoryCategory] = mapped_column(
        Enum(HistoryCategory, name="history_category", native_enum=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    onset_year: Mapped[int | None] = mapped_column(SmallInteger)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
