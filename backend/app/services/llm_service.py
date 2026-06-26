"""
Ollama HTTP client wrapper.

Provides two interfaces:
  - ollama_json(prompt)  → dict   (for structured routing/classification calls)
  - ollama_chat(system, history, user_input) → str  (for agent responses)

Both interfaces hold the Redis GPU lock during inference to prevent
simultaneous Whisper + Ollama VRAM usage on the GTX 1050 Ti.
"""
from __future__ import annotations

import json

import httpx
import structlog

from app.config import get_settings
from app.utils.gpu_lock import gpu_lock

log = structlog.get_logger()


async def ollama_json(prompt: str, temperature: float = 0.1, max_tokens: int = 200) -> dict:
    """
    Make a single-turn Ollama call expecting JSON output.
    Uses format='json' to force valid JSON from the model.
    """
    cfg = get_settings()

    async with gpu_lock("llm"):
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{cfg.ollama_base_url}/api/chat",
                json={
                    "model": cfg.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            raw = resp.json()["message"]["content"]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("llm.json_parse_failed", raw=raw[:200])
        return {}


async def ollama_chat(
    system_prompt: str,
    history: list[dict],  # [{"role": "user"|"assistant", "content": str}]
    user_input: str,
    temperature: float = 0.7,
    max_tokens: int = 300,
) -> str:
    """
    Multi-turn Ollama chat call, returns the assistant's response text.
    """
    cfg = get_settings()

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    async with gpu_lock("llm"):
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{cfg.ollama_base_url}/api/chat",
                json={
                    "model": cfg.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            content = resp.json()["message"]["content"]

    return content.strip()


def _history_from_transcript(transcript: list[dict]) -> list[dict]:
    """Convert transcript turns → Ollama message history (last 10 turns)."""
    history = []
    for turn in transcript[-10:]:
        role = "user" if turn["speaker"] == "user" else "assistant"
        history.append({"role": role, "content": turn["text"]})
    return history
