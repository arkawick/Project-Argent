"""Appointment scheduling endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import Appointment
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate

router = APIRouter()


@router.get("/slots")
async def get_available_slots(
    days_ahead: int = Query(7, le=30, ge=1),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    """Return free 30-min slots for the next N days (weekdays 9–17 UTC)."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = now + timedelta(days=days_ahead)

    booked_rows = (
        await db.execute(
            select(Appointment.scheduled_at)
            .where(Appointment.scheduled_at.between(now, end))
            .where(Appointment.status.in_(["pending", "confirmed"]))
        )
    ).scalars().all()
    booked_set = {dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt for dt in booked_rows}

    slots = []
    cursor = now
    while cursor < end and len(slots) < 20:
        if cursor.weekday() < 5 and 9 <= cursor.hour < 17:
            aware = cursor.replace(tzinfo=timezone.utc) if cursor.tzinfo is None else cursor
            if aware not in booked_set:
                slots.append({
                    "datetime": cursor.isoformat(),
                    "label": cursor.strftime("%A %b %d at %I:%M %p UTC"),
                })
        cursor += timedelta(minutes=30)
        if cursor.hour >= 17:
            cursor = cursor.replace(hour=9, minute=0) + timedelta(days=1)
            while cursor.weekday() >= 5:
                cursor += timedelta(days=1)

    return {"slots": slots}


@router.get("")
async def list_appointments(
    status: str | None = None,
    customer_id: uuid.UUID | None = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    q = select(Appointment).order_by(Appointment.scheduled_at)
    if status:
        q = q.where(Appointment.status == status)
    if customer_id:
        q = q.where(Appointment.customer_id == customer_id)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()
    return {
        "items": [AppointmentOut.model_validate(r) for r in rows],
        "total": total or 0,
        "offset": offset,
        "limit": limit,
    }


@router.post("", response_model=AppointmentOut, status_code=201)
async def create_appointment(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Appointment:
    appt = Appointment(**body.model_dump(), created_at=datetime.now(timezone.utc))
    db.add(appt)
    await db.flush()
    return appt


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def get_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Appointment:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    return appt


@router.patch("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Appointment:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(appt, field, val)
    return appt


@router.delete("/{appointment_id}", status_code=204)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> None:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    appt.status = "cancelled"
