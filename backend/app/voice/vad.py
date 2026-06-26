"""
Voice Activity Detection using webrtcvad.

Frame contract: 16kHz, 16-bit signed little-endian mono PCM.
webrtcvad requires exactly 10 / 20 / 30ms frames — we use 30ms (960 bytes).

State machine:
  SILENCE → SPEAKING  : after MIN_SPEECH_FRAMES consecutive voiced frames
  SPEAKING → SILENCE  : after SILENCE_HANGOVER consecutive unvoiced frames
  SPEAKING → SPEECH_END emitted on transition, with accumulated audio bytes
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import webrtcvad

SAMPLE_RATE = 16_000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000   # 480 samples
FRAME_BYTES = FRAME_SAMPLES * 2                   # 960 bytes (int16 = 2 bytes)

# Minimum voiced frames before declaring speech started (avoids click triggers)
MIN_SPEECH_FRAMES = 4   # 4 × 30ms = 120ms

# Consecutive silence frames before declaring end-of-speech
SILENCE_HANGOVER = 10   # 10 × 30ms = 300ms trailing silence


class VADEvent(Enum):
    SPEECH_START = auto()
    SPEECH_END = auto()


@dataclass
class SpeechSegment:
    """Accumulated audio from one utterance."""
    audio: bytes       # raw 16kHz 16-bit mono PCM
    duration_secs: float


class VAD:
    """
    Stateful VAD processor. Feed raw PCM chunks of any size.
    Call .feed() — it buffers internally and returns (event, segment) per call.

    event is None if nothing notable happened.
    segment is non-None only when event == VADEvent.SPEECH_END.
    """

    def __init__(self, aggressiveness: int = 2) -> None:
        # aggressiveness 0-3: higher = more aggressive noise filtering
        self._vad = webrtcvad.Vad(aggressiveness)
        self._residual: bytes = b""          # leftover bytes < FRAME_BYTES
        self._speech_buf: bytes = b""        # accumulates voiced audio
        self._speech_frames: int = 0         # consecutive voiced frames
        self._silence_frames: int = 0        # consecutive silent frames in speech
        self._in_speech: bool = False

    # ── public API ────────────────────────────────────────────────────────────

    def feed(self, pcm_chunk: bytes) -> tuple[VADEvent | None, SpeechSegment | None]:
        """
        Process an arbitrary-sized PCM chunk.
        Returns (event, segment) — both may be None if no state change occurred.
        """
        self._residual += pcm_chunk
        event: VADEvent | None = None
        segment: SpeechSegment | None = None

        while len(self._residual) >= FRAME_BYTES:
            frame = self._residual[:FRAME_BYTES]
            self._residual = self._residual[FRAME_BYTES:]
            ev, seg = self._process_frame(frame)
            if ev is not None:
                event, segment = ev, seg  # last event wins (rare to get two in one call)

        return event, segment

    @property
    def in_speech(self) -> bool:
        return self._in_speech

    def reset(self) -> None:
        """Force-reset state (e.g. after barge-in cancels an utterance)."""
        self._residual = b""
        self._speech_buf = b""
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False

    # ── internal ──────────────────────────────────────────────────────────────

    def _process_frame(self, frame: bytes) -> tuple[VADEvent | None, SpeechSegment | None]:
        is_voiced = self._vad.is_speech(frame, SAMPLE_RATE)

        if is_voiced:
            return self._handle_voiced(frame)
        else:
            return self._handle_silence(frame)

    def _handle_voiced(self, frame: bytes) -> tuple[VADEvent | None, SpeechSegment | None]:
        self._silence_frames = 0
        self._speech_frames += 1
        self._speech_buf += frame

        if not self._in_speech and self._speech_frames >= MIN_SPEECH_FRAMES:
            self._in_speech = True
            return VADEvent.SPEECH_START, None

        return None, None

    def _handle_silence(self, frame: bytes) -> tuple[VADEvent | None, SpeechSegment | None]:
        if not self._in_speech:
            self._speech_frames = max(0, self._speech_frames - 1)  # decay pre-speech counter
            return None, None

        self._silence_frames += 1
        self._speech_buf += frame  # include trailing silence so Whisper hears full utterance

        if self._silence_frames >= SILENCE_HANGOVER:
            audio = self._speech_buf
            duration = len(audio) / (SAMPLE_RATE * 2)
            self._reset_speech()
            return VADEvent.SPEECH_END, SpeechSegment(audio=audio, duration_secs=duration)

        return None, None

    def _reset_speech(self) -> None:
        self._speech_buf = b""
        self._speech_frames = 0
        self._silence_frames = 0
        self._in_speech = False
