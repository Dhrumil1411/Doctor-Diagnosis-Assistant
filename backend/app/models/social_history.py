import enum
import uuid

from sqlalchemy import Enum, ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SmokingStatus(str, enum.Enum):
    never = "never"
    former = "former"
    current = "current"
    unknown = "unknown"


class SocialHistory(Base):
    __tablename__ = "social_history"
    __table_args__ = (UniqueConstraint("visit_id", name="uq_social_history_visit_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), nullable=False, index=True
    )
    smoking_status: Mapped[SmokingStatus] = mapped_column(
        Enum(SmokingStatus, name="smoking_status", native_enum=False),
        default=SmokingStatus.unknown,
        nullable=False,
    )
    pack_years: Mapped[int | None] = mapped_column(SmallInteger)
    alcohol_use: Mapped[str | None] = mapped_column(String(64))
    recreational_drug_use: Mapped[str | None] = mapped_column(String(120))
    diet: Mapped[str | None] = mapped_column(String(120))
    exercise: Mapped[str | None] = mapped_column(String(120))
    living_situation: Mapped[str | None] = mapped_column(String(255))
    occupational_exposure: Mapped[str | None] = mapped_column(String(255))
    travel_history: Mapped[str | None] = mapped_column(Text)
    sexual_history: Mapped[str | None] = mapped_column(Text)
