from pydantic import BaseModel


class OverviewOut(BaseModel):
    total_calls: int
    active_calls: int
    avg_duration_secs: float | None
    resolution_rate: float | None
    avg_sentiment: float | None
    total_customers: int
    open_tickets: int
    appointments_today: int


class EmotionCount(BaseModel):
    emotion: str
    count: int


class IntentCount(BaseModel):
    intent: str
    count: int


class AgentStats(BaseModel):
    agent_type: str
    calls_handled: int
    avg_sentiment: float | None
    resolution_rate: float | None


class LiveMetrics(BaseModel):
    active_calls: int
    emotion_counts: list[EmotionCount]
    intent_counts: list[IntentCount]
    avg_latency_ms: float | None
