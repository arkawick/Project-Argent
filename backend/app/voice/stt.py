"""
Faster-Whisper STT — CUDA inference with Redis GPU lock.

Model: whisper-small, float16, CUDA
Falls back to CPU int8 if CUDA is unavailable (useful for dev without GPU).

GPU lock prevents Whisper and Ollama from running simultaneously on the 4GB 1050 Ti.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import structlog
from faster_whisper import WhisperModel

from app.utils.gpu_lock import gpu_lock

log = structlog.get_logger()

_model: WhisperModel | None = None

WHISPER_MODEL_SIZE = "small"


def load_model() -> WhisperModel:
    global _model
    if _model is not None:
        return _model

    log.info("whisper.loading", size=WHISPER_MODEL_SIZE, device="cuda", compute="float16")
    try:
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cuda", compute_type="float16")
        log.info("whisper.ready", device="cuda")
    except Exception as e:
        log.warning("whisper.cuda_failed_falling_back_to_cpu", error=str(e))
        _model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
        log.info("whisper.ready", device="cpu")

    return _model


@dataclass
class TranscriptSegment:
    text: str
    start: float      # seconds from audio start
    end: float
    confidence: float  # 1.0 − no_speech_prob


async def transcribe(pcm_bytes: bytes, language: str = "en") -> list[TranscriptSegment]:
    """
    Transcribe raw 16kHz 16-bit mono PCM bytes.

    Uses the Redis GPU lock so Whisper and Ollama never overlap.
    Returns an empty list if audio is silence or too short.
    """
    if len(pcm_bytes) < 3200:  # < 100ms at 16kHz — skip
        return []

    # Convert int16 PCM → float32 normalised to [-1, 1] (Whisper expects this)
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    async with gpu_lock("stt"):
        model = load_model()
        raw_segments, _ = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=False,     # we already ran webrtcvad upstream
            word_timestamps=False,
            condition_on_previous_text=False,
        )
        # Materialise the generator while the lock is held
        raw_list = list(raw_segments)

    segments = [
        TranscriptSegment(
            text=seg.text.strip(),
            start=seg.start,
            end=seg.end,
            confidence=max(0.0, 1.0 - (seg.no_speech_prob or 0.0)),
        )
        for seg in raw_list
        if seg.text.strip()
    ]

    combined = " ".join(s.text for s in segments)
    log.debug("stt.transcribed", text=combined[:80], segments=len(segments))
    return segments


def full_text(segments: list[TranscriptSegment]) -> str:
    return " ".join(s.text for s in segments).strip()
