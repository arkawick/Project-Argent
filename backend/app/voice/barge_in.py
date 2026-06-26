"""
Barge-in (interruption) detection.

When the AI is speaking (TTS audio being sent to LiveKit) and the user starts
talking, we detect this as a barge-in: cancel TTS playback and snap back to
LISTENING state.

TTS state is tracked via a Redis key with a TTL so stale keys auto-expire.
"""
from __future__ import annotations

import structlog

from app.dependencies import get_redis

log = structlog.get_logger()

_TTS_KEY = "call:{call_id}:tts_playing"
_TTS_TTL_SECS = 60   # safety TTL — cleared explicitly, but auto-expires on crash


class BargeInDetector:
    """One instance per call session."""

    # ── TTS state management ──────────────────────────────────────────────────

    async def set_tts_playing(self, call_id: str) -> None:
        """Mark TTS as active for this call. Call before streaming audio."""
        redis = get_redis()
        await redis.set(_TTS_KEY.format(call_id=call_id), "1", ex=_TTS_TTL_SECS)

    async def clear_tts_playing(self, call_id: str) -> None:
        """Mark TTS as finished. Call when audio stream ends normally."""
        redis = get_redis()
        await redis.delete(_TTS_KEY.format(call_id=call_id))

    async def is_tts_playing(self, call_id: str) -> bool:
        redis = get_redis()
        return bool(await redis.exists(_TTS_KEY.format(call_id=call_id)))

    # ── Barge-in check ────────────────────────────────────────────────────────

    async def check(self, call_id: str, speech_detected: bool) -> bool:
        """
        Returns True if this is a genuine barge-in (user speaks while TTS active).
        Side-effect: clears the TTS flag on barge-in so the caller knows to cancel.
        """
        if not speech_detected:
            return False
        if await self.is_tts_playing(call_id):
            await self.clear_tts_playing(call_id)
            log.info("barge_in.detected", call_id=call_id)
            return True
        return False
