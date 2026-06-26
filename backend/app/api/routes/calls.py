"""Call CRUD endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.models import Call, CallInsight
from app.schemas.call import CallCreate, CallUpdate, CallOut, InsightOut

router = APIRouter()


@router.get("")
async def list_calls(
    status: str | None = None,
    agent_type: str | None = None,
    limit: int = Query(20, le=100, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    q = select(Call).order_by(Call.started_at.desc())
    if status:
        q = q.where(Call.status == status)
    if agent_type:
        q = q.where(Call.agent_type == agent_type)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()

    return {
        "items": [CallOut.model_validate(r) for r in rows],
        "total": total or 0,
        "offset": offset,
        "limit": limit,
    }


@router.post("", response_model=CallOut, status_code=201)
async def create_call(
    body: CallCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Call:
    call = Call(
        livekit_room_id=body.livekit_room_id,
        customer_id=body.customer_id,
        started_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(call)
    await db.flush()
    return call


@router.get("/{call_id}", response_model=CallOut)
async def get_call(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Call:
    call = await db.get(Call, call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return call


@router.patch("/{call_id}", response_model=CallOut)
async def update_call(
    call_id: uuid.UUID,
    body: CallUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> Call:
    call = await db.get(Call, call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(call, field, val)
    if body.status == "completed" and not call.ended_at:
        call.ended_at = datetime.now(timezone.utc)
        if call.started_at:
            call.duration_secs = int((call.ended_at - call.started_at).total_seconds())
    return call


@router.delete("/{call_id}", status_code=204)
async def delete_call(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> None:
    call = await db.get(Call, call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    call.status = "deleted"


@router.get("/{call_id}/insights")
async def get_insights(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    rows = (
        await db.execute(
            select(CallInsight)
            .where(CallInsight.call_id == call_id)
            .order_by(CallInsight.turn_number)
        )
    ).scalars().all()
    return {"items": [InsightOut.model_validate(r) for r in rows], "total": len(rows)}


@router.get("/{call_id}/transcript")
async def get_transcript(
    call_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
) -> dict:
    call = await db.get(Call, call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return {"call_id": str(call_id), "transcript": call.transcript or []}
