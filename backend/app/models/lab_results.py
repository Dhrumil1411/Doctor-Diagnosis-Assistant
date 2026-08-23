import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LabCategory(str, enum.Enum):
    blood = "blood"
    imaging = "imaging"
    ecg = "ecg"
    other = "other"


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[LabCategory] = mapped_column(
        Enum(LabCategory, name="lab_category", native_enum=False),
        default=LabCategory.other,
        nullable=False,
    )
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500))
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
