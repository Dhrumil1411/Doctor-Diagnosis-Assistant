import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AllergyType(str, enum.Enum):
    drug = "drug"
    food = "food"
    environmental = "environmental"
    other = "other"


class Allergy(TimestampMixin, Base):
    __tablename__ = "allergies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    allergen: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[AllergyType] = mapped_column(
        Enum(AllergyType, name="allergy_type", native_enum=False),
        default=AllergyType.drug,
        nullable=False,
    )
    reaction: Mapped[str | None] = mapped_column(String(200))
    severity: Mapped[str | None] = mapped_column(String(32))
    notes: Mapped[str | None] = mapped_column(Text)
