"""Booking tools — slot checking and appointment management."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog

from app.dependencies import AsyncSessionLocal
from app.memory import postgres_store, neo4j_store

log = structlog.get_logger()


async def check_available_slots(days_ahead: int = 7) -> list[dict]:
    """
    Return available 30-minute appointment slots over the next N days.
    Slots 9 AM – 5 PM Mon–Fri; excludes already-booked times.
    """
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now + timedelta(days=days_ahead)

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                booked = await postgres_store.get_available_slots(session, now, end)
                booked_times = {a.scheduled_at for a in booked}

        slots = []
        cursor = now
        while cursor < end:
            # Only weekdays 9 AM – 5 PM UTC
            if cursor.weekday() < 5 and 9 <= cursor.hour < 17:
                if cursor not in booked_times:
                    slots.append({
                        "datetime": cursor.isoformat(),
                        "label": cursor.strftime("%A %b %d at %I:%M %p UTC"),
                    })
            cursor += timedelta(minutes=30)
            if cursor.hour >= 17:
                cursor = cursor.replace(hour=9, minute=0) + timedelta(days=1)
                while cursor.weekday() >= 5:
                    cursor += timedelta(days=1)

        return slots[:8]  # return next 8 available slots

    except Exception as e:
        log.warning("booking.check_slots_failed", error=str(e))
        return []


async def create_appointment(
    customer_id: str,
    call_id: str | None,
    title: str,
    scheduled_at: str,
    duration_mins: int = 30,
    agent_notes: str | None = None,
) -> dict:
    """Create an appointment in Postgres and link it in Neo4j."""
    try:
        scheduled_dt = datetime.fromisoformat(scheduled_at)
        if scheduled_dt.tzinfo is None:
            scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)

        async with AsyncSessionLocal() as session:
            async with session.begin():
                appt = await postgres_store.create_appointment(
                    session,
                    customer_id=uuid.UUID(customer_id),
                    call_id=uuid.UUID(call_id) if call_id else None,
                    title=title,
                    scheduled_at=scheduled_dt,
                    duration_mins=duration_mins,
                    status="confirmed",
                    agent_notes=agent_notes,
                )
                appointment_id = str(appt.id)

        await neo4j_store.link_appointment(customer_id, appointment_id, scheduled_at)
        log.info("booking.created", appointment_id=appointment_id, scheduled_at=scheduled_at)

        return {
            "id": appointment_id,
            "title": title,
            "scheduled_at": scheduled_at,
            "duration_mins": duration_mins,
            "status": "confirmed",
        }

    except Exception as e:
        log.error("booking.create_failed", error=str(e))
        return {"error": str(e)}
