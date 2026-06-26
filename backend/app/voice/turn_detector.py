"""
Turn-taking state machine.

States:
  LISTENING  — waiting for user to speak
  PROCESSING — end-of-speech detected, running STT + LLM pipeline
  SPEAKING   — agent is sending TTS audio to the user

Transitions:
  LISTENING  → PROCESSING  : VAD fires SPEECH_END
  PROCESSING → SPEAKING    : TTS synthesis complete, audio streaming starts
  SPEAKING   → LISTENING   : TTS audio finished normally
  ANY        → LISTENING   : barge-in detected (user interrupts)

Callbacks fire on entry to each state so the WebSocket handler can push
{type: "turn_change"} events to the dashboard in real time.
"""
from __future__ import annotations

from enum import Enum
from typing import Awaitable, Callable

import structlog

log = structlog.get_logger()

StateCallback = Callable[[], Awaitable[None]]


class TurnState(Enum):
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


class TurnDetector:
    def __init__(self, call_id: str) -> None:
        self.call_id = call_id
        self.state = TurnState.LISTENING
        self._callbacks: dict[TurnState, StateCallback] = {}

    # ── Callback registration ─────────────────────────────────────────────────

    def on_listening(self, cb: StateCallback) -> None:
        self._callbacks[TurnState.LISTENING] = cb

    def on_processing(self, cb: StateCallback) -> None:
        self._callbacks[TurnState.PROCESSING] = cb

    def on_speaking(self, cb: StateCallback) -> None:
        self._callbacks[TurnState.SPEAKING] = cb

    # ── Event triggers ────────────────────────────────────────────────────────

    async def speech_ended(self) -> None:
        """VAD detected end of user utterance."""
        if self.state == TurnState.LISTENING:
            await self._transition(TurnState.PROCESSING)

    async def tts_started(self) -> None:
        """TTS synthesis complete, audio is now streaming."""
        await self._transition(TurnState.SPEAKING)

    async def tts_ended(self) -> None:
        """TTS audio stream finished playing normally."""
        await self._transition(TurnState.LISTENING)

    async def barge_in(self) -> None:
        """User interrupted while AI was speaking — cancel and listen."""
        log.info("turn.barge_in", call_id=self.call_id, from_state=self.state.value)
        await self._transition(TurnState.LISTENING)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _transition(self, new_state: TurnState) -> None:
        old = self.state
        self.state = new_state
        log.debug(
            "turn.transition",
            call_id=self.call_id,
            from_state=old.value,
            to_state=new_state.value,
        )
        cb = self._callbacks.get(new_state)
        if cb:
            await cb()
