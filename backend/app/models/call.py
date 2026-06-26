import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.call_insight import CallInsight
    from app.models.appointment import Appointment
    from app.models.ticket import Ticket


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    livekit_room_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_secs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    transcript: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped["Customer | None"] = relationship(back_populates="calls")
    insights: Mapped[list["CallInsight"]] = relationship(back_populates="call", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="call")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="call")
