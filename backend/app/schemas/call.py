import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CallCreate(BaseModel):
    customer_id: uuid.UUID | None = None
    livekit_room_id: str


class CallUpdate(BaseModel):
    status: str | None = None
    outcome: str | None = None
    agent_type: str | None = None
    summary: str | None = None
    sentiment_score: float | None = None


class TranscriptTurn(BaseModel):
    speaker: str          # "user" | "agent"
    text: str
    ts: float             # seconds from call start
    emotion: str | None = None
    intent: str | None = None


class CallOut(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID | None
    livekit_room_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None
    duration_secs: int | None
    agent_type: str | None
    transcript: list[dict]
    summary: str | None
    sentiment_score: Decimal | None
    outcome: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightOut(BaseModel):
    id: uuid.UUID
    call_id: uuid.UUID
    turn_number: int
    speaker: str
    text: str
    timestamp_secs: Decimal | None
    emotion: str | None
    emotion_conf: Decimal | None
    intent: str | None
    intent_conf: Decimal | None
    barge_in: bool
    latency_ms: int | None

    model_config = {"from_attributes": True}
