import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeneralExam(Base):
    __tablename__ = "general_exam"
    __table_args__ = (UniqueConstraint("visit_id", name="uq_general_exam_visit_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pallor: Mapped[str | None] = mapped_column(String(24))
    edema: Mapped[str | None] = mapped_column(String(24))
    cyanosis: Mapped[str | None] = mapped_column(String(24))
    clubbing: Mapped[str | None] = mapped_column(String(24))
    lymphadenopathy: Mapped[str | None] = mapped_column(String(24))
    dehydration: Mapped[str | None] = mapped_column(String(24))
    extra_notes: Mapped[str | None] = mapped_column(Text)
