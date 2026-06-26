"""Customer CRM endpoints."""
from __future__ import annotations

import uuid
from datetime import timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.memory import neo4j_store
from app.models import Call, Customer, Ticket
from app.schemas.customer import CustomerCreate, CustomerOut, CustomerSummary, CustomerUpdate
from app.schemas.call import CallOut
from app.schemas.ticket import TicketOut

router = APIRouter()


@router.get("")
async def list_customers(
    tier: str | None = None,
    tag: str | None = None,
    limit: int = Query(20, le=100, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    q = select(Customer).order_by(Customer.last_contact.desc().nullslast())
    if tier:
        q = q.where(Customer.tier == tier)
    if tag:
        q = q.where(Customer.tags.contains([tag]))

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()

    return {
        "items": [CustomerSummary.model_validate(r) for r in rows],
        "total": total or 0,
        "offset": offset,
        "limit": limit,
    }


@router.post("", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Customer:
    customer = Customer(**body.model_dump(), created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
    db.add(customer)
    await db.flush()

    # Mirror in Neo4j
    try:
        await neo4j_store.upsert_customer(
            str(customer.id), customer.name or "", customer.phone, customer.tier
        )
    except Exception:
        pass

    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Customer:
    c = await db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return c


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Customer:
    c = await db.get(Customer, customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(c, field, val)
    c.updated_at = datetime.now(timezone.utc)
    return c


@router.get("/{customer_id}/calls")
async def get_customer_calls(
    customer_id: uuid.UUID,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    rows = (
        await db.execute(
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(Call.started_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return {"items": [CallOut.model_validate(r) for r in rows], "total": len(rows)}


@router.get("/{customer_id}/tickets")
async def get_customer_tickets(
    customer_id: uuid.UUID,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    q = select(Ticket).where(Ticket.customer_id == customer_id).order_by(Ticket.created_at.desc())
    if status:
        q = q.where(Ticket.status == status)
    rows = (await db.execute(q)).scalars().all()
    return {"items": [TicketOut.model_validate(r) for r in rows], "total": len(rows)}


@router.get("/{customer_id}/graph")
async def get_customer_graph(
    customer_id: uuid.UUID,
    _=Depends(get_current_user),
) -> dict:
    cid = str(customer_id)
    try:
        topics = await neo4j_store.get_customer_topics(cid)
        frustration = await neo4j_store.get_frustration_count(cid)
    except Exception:
        topics, frustration = [], 0
    return {
        "customer_id": cid,
        "topics": topics,
        "frustration_count": frustration,
        "is_repeat_complainer": frustration >= 3,
    }
