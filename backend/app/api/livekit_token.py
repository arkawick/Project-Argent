"""LiveKit JWT token generation for browser and agent participants."""
from __future__ import annotations

from fastapi import APIRouter, Query
from livekit.api import AccessToken, VideoGrants

from app.config import get_settings

router = APIRouter()


def _make_token(room: str, identity: str, can_publish: bool = True, can_subscribe: bool = True) -> str:
    cfg = get_settings()
    token = (
        AccessToken(cfg.livekit_api_key, cfg.livekit_api_secret)
        .with_identity(identity)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
            )
        )
    )
    return token.to_jwt()


def generate_agent_token(room: str) -> str:
    """Token for the backend agent participant (pub + sub)."""
    return _make_token(room, identity="ai-agent", can_publish=True, can_subscribe=True)


def generate_user_token(room: str, identity: str) -> str:
    """Token for a human browser participant."""
    return _make_token(room, identity=identity, can_publish=True, can_subscribe=True)


@router.get("/token")
async def get_livekit_token(
    room: str = Query(..., description="LiveKit room name (= call_id)"),
    identity: str = Query(default="user", description="Participant identity"),
) -> dict:
    """Issue a LiveKit JWT for the browser client."""
    token = generate_user_token(room, identity)
    cfg = get_settings()
    return {"token": token, "livekit_url": cfg.livekit_ws_url, "room": room}
