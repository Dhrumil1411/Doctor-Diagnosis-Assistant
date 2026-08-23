import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Vitals(Base):
    __tablename__ = "vitals"
    __table_args__ = (UniqueConstraint("visit_id", name="uq_vitals_visit_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    systolic_bp: Mapped[int | None] = mapped_column(SmallInteger)
    diastolic_bp: Mapped[int | None] = mapped_column(SmallInteger)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger)
    respiratory_rate: Mapped[int | None] = mapped_column(SmallInteger)
    spo2: Mapped[float | None] = mapped_column(Numeric(4, 1))
    blood_glucose_mg_dl: Mapped[int | None] = mapped_column(SmallInteger)
    pain_score: Mapped[int | None] = mapped_column(SmallInteger)
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
