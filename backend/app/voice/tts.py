"""
Piper TTS — CPU synthesis via piper-tts Python package.

Runs in a thread-pool executor so it never blocks the event loop.
Does NOT hold the GPU lock — Piper uses ONNX Runtime on CPU only.

Output: WAV bytes (16-bit signed PCM, sample rate from model config).
"""
from __future__ import annotations

import asyncio
import io
import wave
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from piper import PiperVoice  # type: ignore[import]

log = structlog.get_logger()

_voice: "PiperVoice | None" = None


def _load_voice_sync(model_path: str) -> "PiperVoice | None":
    global _voice
    if _voice is not None:
        return _voice

    if not Path(model_path).exists():
        log.warning("piper.model_not_found", path=model_path,
                    hint="Run scripts/pull_models.sh to download the ONNX file.")
        return None

    try:
        from piper import PiperVoice  # type: ignore[import]
        _voice = PiperVoice.load(model_path, use_cuda=False)
        log.info("piper.ready", model=model_path, sample_rate=_voice.config.sample_rate)
    except Exception as e:
        log.error("piper.load_failed", error=str(e))
        _voice = None

    return _voice


def _synthesize_sync(text: str, model_path: str) -> bytes:
    """Blocking synthesis — call via run_in_executor."""
    voice = _load_voice_sync(model_path)
    if voice is None:
        return b""

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(voice.config.sample_rate)
        voice.synthesize(text, wav)

    return buf.getvalue()


async def synthesize(text: str, model_path: str) -> bytes:
    """
    Async wrapper — synthesises text and returns WAV bytes.
    Runs the blocking Piper call in the default thread-pool executor.
    """
    if not text.strip():
        return b""

    loop = asyncio.get_running_loop()
    wav_bytes = await loop.run_in_executor(None, _synthesize_sync, text, model_path)

    if wav_bytes:
        log.debug("piper.synthesized", chars=len(text), wav_bytes=len(wav_bytes))

    return wav_bytes


async def preload(model_path: str) -> None:
    """Warm up Piper at startup so the first call isn't slow."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _load_voice_sync, model_path)
