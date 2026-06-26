"""Analytics endpoints — all responses are Redis-cached."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis, get_current_user
from app.models import Call, CallInsight, Customer, Ticket, Appointment

log = structlog.get_logger()
router = APIRouter()


# ── Cache helpers ──────────────────────────────────────────────────────────────

async def _from_cache(redis, key: str) -> Any | None:
    raw = await redis.get(key)
    return json.loads(raw) if raw else None


async def _to_cache(redis, key: str, data: Any, ttl: int = 30) -> None:
    await redis.set(key, json.dumps(data, default=str), ex=ttl)


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    cache_key = "analytics:overview"
    if cached := await _from_cache(redis, cache_key):
        return cached

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_calls = await db.scalar(select(func.count(Call.id))) or 0
    active_calls = await db.scalar(
        select(func.count(Call.id)).where(Call.status == "active")
    ) or 0
    avg_duration = await db.scalar(
        select(func.avg(Call.duration_secs)).where(Call.duration_secs.isnot(None))
    )
    completed = await db.scalar(
        select(func.count(Call.id)).where(Call.status == "completed")
    ) or 0
    resolved = await db.scalar(
        select(func.count(Call.id)).where(Call.outcome == "resolved")
    ) or 0
    avg_sentiment = await db.scalar(
        select(func.avg(Call.sentiment_score)).where(Call.sentiment_score.isnot(None))
    )
    total_customers = await db.scalar(select(func.count(Customer.id))) or 0
    open_tickets = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
    ) or 0
    appts_today = await db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at < today_start + timedelta(days=1),
            Appointment.status.in_(["pending", "confirmed"]),
        )
    ) or 0

    result = {
        "total_calls": total_calls,
        "active_calls": active_calls,
        "avg_duration_secs": float(avg_duration) if avg_duration else None,
        "resolution_rate": round(resolved / completed, 3) if completed else None,
        "avg_sentiment": float(f"{float(avg_sentiment):.3f}") if avg_sentiment else None,
        "total_customers": total_customers,
        "open_tickets": open_tickets,
        "appointments_today": appts_today,
    }
    await _to_cache(redis, cache_key, result, ttl=30)
    return result


@router.get("/emotions")
async def emotion_trends(
    period: str = "week",   # day | week | month | all
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    cache_key = f"analytics:emotions:{period}"
    if cached := await _from_cache(redis, cache_key):
        return cached

    q = (
        select(
            func.date_trunc("day", CallInsight.created_at).label("date"),
            CallInsight.emotion,
            func.count(CallInsight.id).label("count"),
        )
        .where(CallInsight.emotion.isnot(None))
    )
    if period != "all":
        days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.where(CallInsight.created_at >= since)

    q = q.group_by("date", CallInsight.emotion).order_by("date")
    rows = (await db.execute(q)).all()

    result = {
        "period": period,
        "data": [{"date": str(r[0]), "emotion": r[1], "count": r[2]} for r in rows],
    }
    await _to_cache(redis, cache_key, result, ttl=30)
    return result


@router.get("/intents")
async def intent_breakdown(
    period: str = "week",
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    cache_key = f"analytics:intents:{period}"
    if cached := await _from_cache(redis, cache_key):
        return cached

    q = (
        select(CallInsight.intent, func.count(CallInsight.id).label("count"))
        .where(CallInsight.intent.isnot(None))
    )
    if period != "all":
        days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
        q = q.where(CallInsight.created_at >= datetime.now(timezone.utc) - timedelta(days=days))

    q = q.group_by(CallInsight.intent).order_by(func.count(CallInsight.id).desc())
    rows = (await db.execute(q)).all()

    result = {
        "period": period,
        "data": [{"intent": r[0], "count": r[1]} for r in rows],
    }
    await _to_cache(redis, cache_key, result, ttl=30)
    return result


@router.get("/agents")
async def agent_performance(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    cache_key = "analytics:agents"
    if cached := await _from_cache(redis, cache_key):
        return cached

    rows = (
        await db.execute(
            select(
                Call.agent_type,
                func.count(Call.id).label("calls_handled"),
                func.avg(Call.sentiment_score).label("avg_sentiment"),
                func.avg(
                    case((Call.duration_secs.isnot(None), Call.duration_secs), else_=None)
                ).label("avg_duration"),
                func.sum(
                    case((Call.outcome == "resolved", 1), else_=0)
                ).label("resolved_count"),
            )
            .where(Call.agent_type.isnot(None))
            .where(Call.status == "completed")
            .group_by(Call.agent_type)
        )
    ).all()

    data = []
    for r in rows:
        handled = r[1] or 0
        resolved = r[4] or 0
        data.append({
            "agent_type": r[0],
            "calls_handled": handled,
            "avg_sentiment": float(f"{float(r[2]):.3f}") if r[2] else None,
            "avg_duration_secs": float(r[3]) if r[3] else None,
            "resolution_rate": round(resolved / handled, 3) if handled else None,
        })

    result = {"data": data}
    await _to_cache(redis, cache_key, result, ttl=30)
    return result


@router.get("/customers")
async def customer_stats(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    cache_key = "analytics:customers"
    if cached := await _from_cache(redis, cache_key):
        return cached

    tier_rows = (
        await db.execute(
            select(Customer.tier, func.count(Customer.id).label("count"))
            .group_by(Customer.tier)
            .order_by(func.count(Customer.id).desc())
        )
    ).all()

    avg_ltv = await db.scalar(select(func.avg(Customer.lifetime_value)))
    total = await db.scalar(select(func.count(Customer.id))) or 0

    result = {
        "total_customers": total,
        "avg_lifetime_value": float(f"{float(avg_ltv):.2f}") if avg_ltv else 0.0,
        "tier_distribution": [{"tier": r[0], "count": r[1]} for r in tier_rows],
    }
    await _to_cache(redis, cache_key, result, ttl=60)
    return result


@router.get("/live")
async def live_metrics(
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    _=Depends(get_current_user),
) -> dict:
    """Lightweight live snapshot — short cache (5s). Complements the WS feed."""
    cache_key = "analytics:live"
    if cached := await _from_cache(redis, cache_key):
        return cached

    active = await db.scalar(select(func.count(Call.id)).where(Call.status == "active")) or 0
    avg_latency = await db.scalar(
        select(func.avg(CallInsight.latency_ms)).where(CallInsight.latency_ms.isnot(None))
    )

    result = {
        "active_calls": active,
        "avg_latency_ms": float(avg_latency) if avg_latency else None,
    }
    await _to_cache(redis, cache_key, result, ttl=5)
    return result
