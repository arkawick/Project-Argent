"""
Redis-based GPU lock — ensures Faster-Whisper and Ollama never share VRAM simultaneously.
Piper TTS runs on CPU and must NOT use this lock.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog

from app.dependencies import get_redis

log = structlog.get_logger()

_GPU_LOCK_KEY = "gpu:lock"
_GPU_LOCK_TTL = 30      # seconds — auto-expire if holder crashes
_POLL_INTERVAL = 0.05   # 50ms poll when waiting


@asynccontextmanager
async def gpu_lock(owner: str):
    """
    Acquire the GPU lock before entering, release on exit.
    Blocks until the lock is available (with 50ms polling).

    Usage:
        async with gpu_lock("stt"):
            segments = model.transcribe(audio)
    """
    redis = get_redis()
    wait_cycles = 0
    while True:
        acquired = await redis.set(_GPU_LOCK_KEY, owner, ex=_GPU_LOCK_TTL, nx=True)
        if acquired:
            break
        wait_cycles += 1
        if wait_cycles % 20 == 0:  # log every ~1 second of waiting
            current = await redis.get(_GPU_LOCK_KEY)
            log.debug("gpu_lock.waiting", owner=owner, held_by=current)
        await asyncio.sleep(_POLL_INTERVAL)

    log.debug("gpu_lock.acquired", owner=owner)
    try:
        yield
    finally:
        await redis.delete(_GPU_LOCK_KEY)
        log.debug("gpu_lock.released", owner=owner)
