import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    company: str | None = None
    tier: str = "standard"
    preferences: dict = {}
    tags: list[str] = []


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = None
    company: str | None = None
    tier: str | None = None
    preferences: dict | None = None
    tags: list[str] | None = None


class CustomerOut(CustomerBase):
    id: uuid.UUID
    lifetime_value: Decimal
    first_contact: datetime
    last_contact: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerSummary(BaseModel):
    id: uuid.UUID
    name: str | None
    phone: str | None
    tier: str
    last_contact: datetime | None

    model_config = {"from_attributes": True}
