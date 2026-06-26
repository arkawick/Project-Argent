"""Ticket CRUD endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import Ticket
from app.schemas.ticket import TicketCreate, TicketOut, TicketUpdate

router = APIRouter()


@router.get("")
async def list_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    q = select(Ticket).order_by(Ticket.created_at.desc())
    if status:
        q = q.where(Ticket.status == status)
    if priority:
        q = q.where(Ticket.priority == priority)
    if category:
        q = q.where(Ticket.category == category)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()
    return {
        "items": [TicketOut.model_validate(r) for r in rows],
        "total": total or 0,
        "offset": offset,
        "limit": limit,
    }


@router.post("", response_model=TicketOut, status_code=201)
async def create_ticket(
    body: TicketCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Ticket:
    now = datetime.now(timezone.utc)
    ticket = Ticket(**body.model_dump(), created_at=now, updated_at=now)
    db.add(ticket)
    await db.flush()
    return ticket


@router.get("/{ticket_id}", response_model=TicketOut)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Ticket:
    t = await db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


@router.patch("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: uuid.UUID,
    body: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Ticket:
    t = await db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(t, field, val)
    t.updated_at = datetime.now(timezone.utc)
    if body.status in ("resolved", "closed") and not t.resolved_at:
        t.resolved_at = datetime.now(timezone.utc)
    return t
