"""Thin CRUD helpers used by agents and API routes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Call, Customer, Appointment, Ticket, CallInsight


# ── Customer ───────────────────────────────────────────────────────────────────

async def get_customer_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    return result.scalar_one_or_none()


async def get_customer(session: AsyncSession, customer_id: uuid.UUID) -> Customer | None:
    return await session.get(Customer, customer_id)


async def create_customer(session: AsyncSession, **kwargs) -> Customer:
    customer = Customer(**kwargs)
    session.add(customer)
    await session.flush()
    return customer


async def touch_customer(session: AsyncSession, customer_id: uuid.UUID) -> None:
    await session.execute(
        update(Customer)
        .where(Customer.id == customer_id)
        .values(last_contact=datetime.now(timezone.utc))
    )


# ── Call ───────────────────────────────────────────────────────────────────────

async def create_call(session: AsyncSession, room_id: str, customer_id: uuid.UUID | None = None) -> Call:
    call = Call(
        livekit_room_id=room_id,
        customer_id=customer_id,
        started_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(call)
    await session.flush()
    return call


async def end_call(
    session: AsyncSession,
    call_id: uuid.UUID,
    outcome: str,
    summary: str | None = None,
    agent_type: str | None = None,
    sentiment_score: float | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    call = await session.get(Call, call_id)
    if call:
        call.status = "completed"
        call.ended_at = now
        call.duration_secs = int((now - call.started_at).total_seconds())
        call.outcome = outcome
        call.summary = summary
        call.agent_type = agent_type
        call.sentiment_score = sentiment_score


async def append_transcript_turn(session: AsyncSession, call_id: uuid.UUID, turn: dict) -> None:
    call = await session.get(Call, call_id)
    if call:
        call.transcript = (call.transcript or []) + [turn]


# ── CallInsight ────────────────────────────────────────────────────────────────

async def add_insight(session: AsyncSession, **kwargs) -> CallInsight:
    insight = CallInsight(created_at=datetime.now(timezone.utc), **kwargs)
    session.add(insight)
    await session.flush()
    return insight


# ── Appointment ────────────────────────────────────────────────────────────────

async def create_appointment(session: AsyncSession, **kwargs) -> Appointment:
    appt = Appointment(created_at=datetime.now(timezone.utc), **kwargs)
    session.add(appt)
    await session.flush()
    return appt


async def get_available_slots(session: AsyncSession, date_start: datetime, date_end: datetime) -> list[Appointment]:
    result = await session.execute(
        select(Appointment)
        .where(Appointment.scheduled_at.between(date_start, date_end))
        .where(Appointment.status.in_(["pending", "confirmed"]))
        .order_by(Appointment.scheduled_at)
    )
    return list(result.scalars().all())


# ── Ticket ─────────────────────────────────────────────────────────────────────

async def create_ticket(session: AsyncSession, **kwargs) -> Ticket:
    ticket = Ticket(**kwargs)
    session.add(ticket)
    await session.flush()
    return ticket


async def get_open_tickets(session: AsyncSession, customer_id: uuid.UUID) -> list[Ticket]:
    result = await session.execute(
        select(Ticket)
        .where(Ticket.customer_id == customer_id)
        .where(Ticket.status.in_(["open", "in_progress"]))
        .order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())
