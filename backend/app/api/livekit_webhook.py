"""LiveKit webhook receiver — handles room lifecycle events."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Request, Response
from livekit.api import WebhookReceiver

from app.config import get_settings
from app.dependencies import AsyncSessionLocal
from app.memory import postgres_store

log = structlog.get_logger()
router = APIRouter()


@router.post("/webhook")
async def livekit_webhook(request: Request) -> Response:
    cfg = get_settings()
    body = await request.body()
    auth_header = request.headers.get("Authorization", "")

    receiver = WebhookReceiver(cfg.livekit_api_key, cfg.livekit_api_secret)
    try:
        event = receiver.receive(body.decode(), auth_header)
    except Exception as e:
        log.warning("livekit.webhook_invalid", error=str(e))
        return Response(status_code=400)

    event_type = event.event

    if event_type == "room_started":
        room_name = event.room.name
        log.info("livekit.room_started", room=room_name)
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    await postgres_store.create_call(session, room_id=room_name)
        except Exception as e:
            log.warning("livekit.room_started_db_error", error=str(e))

    elif event_type == "room_finished":
        room_name = event.room.name
        log.info("livekit.room_finished", room=room_name)

    elif event_type == "participant_joined":
        identity = event.participant.identity
        room_name = event.room.name
        log.info("livekit.participant_joined", room=room_name, identity=identity)

    elif event_type == "participant_left":
        identity = event.participant.identity
        log.info("livekit.participant_left", room=event.room.name, identity=identity)

    return Response(status_code=200)
