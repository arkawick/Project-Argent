"""Classify emotion and urgency from a customer utterance."""
from __future__ import annotations

import structlog

from app.services.llm_service import ollama_json

log = structlog.get_logger()

_EMOTION_PROMPT = """\
Classify the emotion and urgency in this customer message. Be concise.
Output ONLY valid JSON with exactly these keys:
  "emotion": one of neutral, happy, frustrated, angry, sad, confused
  "urgency": float 0.0 to 1.0 (1.0 = extremely urgent)

Message: {text}

JSON:"""

_FALLBACK = {"emotion": "neutral", "urgency": 0.3}


async def classify(text: str) -> tuple[str, float]:
    """
    Returns (emotion, urgency_score).
    Falls back to ("neutral", 0.3) on any error.
    """
    if not text.strip():
        return "neutral", 0.0

    try:
        result = await ollama_json(_EMOTION_PROMPT.format(text=text))
        emotion = result.get("emotion", "neutral")
        urgency = float(result.get("urgency", 0.3))

        # Sanitise
        valid_emotions = {"neutral", "happy", "frustrated", "angry", "sad", "confused"}
        if emotion not in valid_emotions:
            emotion = "neutral"
        urgency = max(0.0, min(1.0, urgency))

        log.debug("emotion.classified", emotion=emotion, urgency=urgency)
        return emotion, urgency

    except Exception as e:
        log.warning("emotion.classify_failed", error=str(e))
        return "neutral", 0.3
