"""
Dashboard WebSocket — broadcasts live metrics every 2 seconds.

The Next.js dashboard connects here to get real-time data without polling REST.
Payload shape: LiveMetrics schema from app/schemas/analytics.py
"""
from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select

from app.dependencies import AsyncSessionLocal
from app.models import Call, CallInsight

log = structlog.get_logger()
router = APIRouter()

BROADCAST_INTERVAL = 2.0  # seconds


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    log.info("dashboard.connected")
    try:
        while True:
            metrics = await _fetch_live_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(BROADCAST_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.warning("dashboard.error", error=str(e))
    finally:
        log.info("dashboard.disconnected")


async def _fetch_live_metrics() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                active_calls = await session.scalar(
                    select(func.count(Call.id)).where(Call.status == "active")
                ) or 0

                # Emotion distribution from last 100 insights
                emotion_rows = await session.execute(
                    select(CallInsight.emotion, func.count(CallInsight.id).label("cnt"))
                    .where(CallInsight.emotion.isnot(None))
                    .group_by(CallInsight.emotion)
                    .order_by(func.count(CallInsight.id).desc())
                    .limit(10)
                )
                emotion_counts = [
                    {"emotion": r[0], "count": r[1]} for r in emotion_rows
                ]

                # Intent distribution
                intent_rows = await session.execute(
                    select(CallInsight.intent, func.count(CallInsight.id).label("cnt"))
                    .where(CallInsight.intent.isnot(None))
                    .group_by(CallInsight.intent)
                    .order_by(func.count(CallInsight.id).desc())
                    .limit(10)
                )
                intent_counts = [
                    {"intent": r[0], "count": r[1]} for r in intent_rows
                ]

                avg_latency = await session.scalar(
                    select(func.avg(CallInsight.latency_ms)).where(
                        CallInsight.latency_ms.isnot(None)
                    )
                )

        return {
            "type": "metrics",
            "active_calls": active_calls,
            "emotion_counts": emotion_counts,
            "intent_counts": intent_counts,
            "avg_latency_ms": float(avg_latency) if avg_latency else None,
        }
    except Exception as e:
        log.warning("dashboard.fetch_failed", error=str(e))
        return {"type": "metrics", "active_calls": 0, "emotion_counts": [], "intent_counts": [], "avg_latency_ms": None}
