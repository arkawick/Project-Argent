import uuid
from datetime import datetime

from pydantic import BaseModel


class TicketCreate(BaseModel):
    customer_id: uuid.UUID
    call_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    priority: str = "medium"
    category: str | None = None


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    resolution: str | None = None


class TicketOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    call_id: uuid.UUID | None
    title: str
    description: str | None
    priority: str
    status: str
    category: str | None
    resolution: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
