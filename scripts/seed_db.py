"""
Seed demo data into PostgreSQL.
Run AFTER `alembic upgrade head` and with infra services running.

Usage (from project root):
    docker compose exec backend python /app/../scripts/seed_db.py
    # or locally with DATABASE_URL set:
    DATABASE_URL=postgresql+asyncpg://... python scripts/seed_db.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://argent:changeme@localhost:5432/argent",
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Import models directly (run from project root or inside container)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.models import Customer, Call, Appointment, CallInsight, Ticket  # noqa: E402

now = datetime.now(timezone.utc)


CUSTOMERS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Sarah Mitchell",
        "phone": "+14155550101",
        "email": "sarah.mitchell@example.com",
        "company": "Apex Logistics",
        "tier": "vip",
        "tags": ["frequent", "high-value"],
        "preferences": {"language": "en", "tone": "professional"},
        "first_contact": now - timedelta(days=180),
        "last_contact": now - timedelta(days=2),
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "James Okafor",
        "phone": "+14155550102",
        "email": "james.okafor@example.com",
        "company": "Bright Ventures",
        "tier": "premium",
        "tags": ["referral"],
        "preferences": {"language": "en", "tone": "friendly"},
        "first_contact": now - timedelta(days=60),
        "last_contact": now - timedelta(days=7),
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "name": "Priya Sharma",
        "phone": "+14155550103",
        "email": "priya.sharma@example.com",
        "company": None,
        "tier": "standard",
        "tags": [],
        "preferences": {},
        "first_contact": now - timedelta(days=10),
        "last_contact": now - timedelta(days=1),
    },
]

CALLS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0001-000000000001"),
        "customer_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "livekit_room_id": "demo-room-001",
        "status": "completed",
        "started_at": now - timedelta(days=2, hours=3),
        "ended_at": now - timedelta(days=2, hours=2, minutes=45),
        "duration_secs": 900,
        "agent_type": "support",
        "summary": "Customer reported delayed delivery on order #8821. Ticket created, estimated resolution 48h.",
        "sentiment_score": -0.35,
        "outcome": "resolved",
        "transcript": [
            {"speaker": "agent", "text": "Hi, thanks for calling AI FrontDesk. How can I help you today?", "ts": 0.0},
            {"speaker": "user", "text": "Hi, I placed an order last week and it still hasn't arrived.", "ts": 3.2},
            {"speaker": "agent", "text": "I'm sorry to hear that. Let me look up your order right away.", "ts": 7.1},
            {"speaker": "user", "text": "Order number 8821. This is really frustrating.", "ts": 10.5},
            {"speaker": "agent", "text": "I completely understand. I've created a priority ticket and our team will resolve this within 48 hours.", "ts": 14.2},
        ],
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0001-000000000002"),
        "customer_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "livekit_room_id": "demo-room-002",
        "status": "completed",
        "started_at": now - timedelta(days=7, hours=1),
        "ended_at": now - timedelta(days=7, minutes=30),
        "duration_secs": 390,
        "agent_type": "booking",
        "summary": "Customer booked a product demo for next Tuesday at 2 PM.",
        "sentiment_score": 0.72,
        "outcome": "booked",
        "transcript": [
            {"speaker": "agent", "text": "Welcome to AI FrontDesk! What can I help you with?", "ts": 0.0},
            {"speaker": "user", "text": "I'd like to schedule a demo of your enterprise plan.", "ts": 2.8},
            {"speaker": "agent", "text": "Absolutely! I have availability Tuesday at 2 PM or Thursday at 11 AM. Which works for you?", "ts": 5.5},
            {"speaker": "user", "text": "Tuesday at 2 PM is perfect.", "ts": 9.1},
            {"speaker": "agent", "text": "Done! I've booked your demo for Tuesday at 2 PM. You'll receive a confirmation shortly.", "ts": 11.3},
        ],
    },
]

INSIGHTS = [
    # Call 1 insights
    {"call_id": uuid.UUID("00000000-0000-0000-0001-000000000001"), "turn_number": 0, "speaker": "agent", "text": "Hi, thanks for calling AI FrontDesk. How can I help you today?", "timestamp_secs": 0.0, "emotion": "neutral", "emotion_conf": 0.91, "intent": "greeting", "intent_conf": 0.98, "latency_ms": 320},
    {"call_id": uuid.UUID("00000000-0000-0000-0001-000000000001"), "turn_number": 1, "speaker": "user", "text": "Hi, I placed an order last week and it still hasn't arrived.", "timestamp_secs": 3.2, "emotion": "frustrated", "emotion_conf": 0.78, "intent": "complaint", "intent_conf": 0.92, "latency_ms": None},
    {"call_id": uuid.UUID("00000000-0000-0000-0001-000000000001"), "turn_number": 3, "speaker": "user", "text": "Order number 8821. This is really frustrating.", "timestamp_secs": 10.5, "emotion": "angry", "emotion_conf": 0.84, "intent": "complaint", "intent_conf": 0.95, "barge_in": True, "latency_ms": None},
    # Call 2 insights
    {"call_id": uuid.UUID("00000000-0000-0000-0001-000000000002"), "turn_number": 1, "speaker": "user", "text": "I'd like to schedule a demo of your enterprise plan.", "timestamp_secs": 2.8, "emotion": "happy", "emotion_conf": 0.82, "intent": "booking", "intent_conf": 0.96, "latency_ms": None},
    {"call_id": uuid.UUID("00000000-0000-0000-0001-000000000002"), "turn_number": 3, "speaker": "user", "text": "Tuesday at 2 PM is perfect.", "timestamp_secs": 9.1, "emotion": "happy", "emotion_conf": 0.89, "intent": "confirmation", "intent_conf": 0.99, "latency_ms": None},
]

APPOINTMENTS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0002-000000000001"),
        "customer_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "call_id": uuid.UUID("00000000-0000-0000-0001-000000000002"),
        "title": "Enterprise Plan Demo",
        "description": "Demo of enterprise features including multi-agent routing and analytics.",
        "scheduled_at": now + timedelta(days=2, hours=14),
        "duration_mins": 45,
        "status": "confirmed",
        "agent_notes": "Customer interested in multi-location deployment.",
    },
]

TICKETS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0003-000000000001"),
        "customer_id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "call_id": uuid.UUID("00000000-0000-0000-0001-000000000001"),
        "title": "Delayed delivery — Order #8821",
        "description": "Customer reported order placed 7 days ago has not arrived. Priority escalation requested.",
        "priority": "high",
        "status": "in_progress",
        "category": "delivery",
    },
]


async def seed(session: AsyncSession) -> None:
    for c in CUSTOMERS:
        session.add(Customer(
            id=c["id"], name=c["name"], phone=c["phone"], email=c["email"],
            company=c["company"], tier=c["tier"], tags=c["tags"],
            preferences=c["preferences"], first_contact=c["first_contact"],
            last_contact=c["last_contact"], created_at=now, updated_at=now,
        ))

    for call_data in CALLS:
        session.add(Call(
            id=call_data["id"], customer_id=call_data["customer_id"],
            livekit_room_id=call_data["livekit_room_id"], status=call_data["status"],
            started_at=call_data["started_at"], ended_at=call_data["ended_at"],
            duration_secs=call_data["duration_secs"], agent_type=call_data["agent_type"],
            summary=call_data["summary"], sentiment_score=call_data["sentiment_score"],
            outcome=call_data["outcome"], transcript=call_data["transcript"],
            created_at=call_data["started_at"],
        ))

    for ins in INSIGHTS:
        session.add(CallInsight(
            call_id=ins["call_id"], turn_number=ins["turn_number"],
            speaker=ins["speaker"], text=ins["text"],
            timestamp_secs=ins.get("timestamp_secs"),
            emotion=ins.get("emotion"), emotion_conf=ins.get("emotion_conf"),
            intent=ins.get("intent"), intent_conf=ins.get("intent_conf"),
            barge_in=ins.get("barge_in", False), latency_ms=ins.get("latency_ms"),
            created_at=now,
        ))

    for appt in APPOINTMENTS:
        session.add(Appointment(
            id=appt["id"], customer_id=appt["customer_id"], call_id=appt["call_id"],
            title=appt["title"], description=appt["description"],
            scheduled_at=appt["scheduled_at"], duration_mins=appt["duration_mins"],
            status=appt["status"], agent_notes=appt["agent_notes"], created_at=now,
        ))

    for tkt in TICKETS:
        session.add(Ticket(
            id=tkt["id"], customer_id=tkt["customer_id"], call_id=tkt["call_id"],
            title=tkt["title"], description=tkt["description"],
            priority=tkt["priority"], status=tkt["status"], category=tkt["category"],
            created_at=now, updated_at=now,
        ))

    await session.commit()
    print(f"Seeded: {len(CUSTOMERS)} customers, {len(CALLS)} calls, {len(INSIGHTS)} insights, "
          f"{len(APPOINTMENTS)} appointments, {len(TICKETS)} tickets.")


async def main() -> None:
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
