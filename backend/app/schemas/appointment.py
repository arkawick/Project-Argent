import uuid
from datetime import datetime

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    customer_id: uuid.UUID
    call_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    scheduled_at: datetime
    duration_mins: int = 30
    agent_notes: str | None = None


class AppointmentUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None
    duration_mins: int | None = None
    status: str | None = None
    agent_notes: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    call_id: uuid.UUID | None
    title: str
    description: str | None
    scheduled_at: datetime
    duration_mins: int
    status: str
    agent_notes: str | None
    reminder_sent: bool
    created_at: datetime

    model_config = {"from_attributes": True}
