import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.call import Call


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    call_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_mins: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    agent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="appointments")
    call: Mapped["Call | None"] = relationship(back_populates="appointments")
