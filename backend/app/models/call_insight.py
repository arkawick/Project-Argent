import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.call import Call


class CallInsight(Base):
    __tablename__ = "call_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_secs: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    emotion: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    emotion_conf: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    intent_conf: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    barge_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    call: Mapped["Call"] = relationship(back_populates="insights")
