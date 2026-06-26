import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.call import Call
    from app.models.appointment import Appointment
    from app.models.ticket import Ticket


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="standard", index=True, nullable=False)
    lifetime_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    first_contact: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_contact: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    calls: Mapped[list["Call"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
