import enum
import uuid

from sqlalchemy import Enum, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SymptomStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    unsure = "unsure"


class Symptom(Base):
    __tablename__ = "symptoms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[SymptomStatus] = mapped_column(
        Enum(SymptomStatus, name="symptom_status", native_enum=False),
        default=SymptomStatus.present,
        nullable=False,
    )
    severity: Mapped[int | None] = mapped_column(SmallInteger)
    duration: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
