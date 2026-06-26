"""
AgentState — the single shared state dict that flows through every LangGraph node.

All fields are plain Python types (no LangChain reducers) to keep the graph
easy to inspect and debug during the hackathon demo.
"""
from __future__ import annotations

from typing import Literal, TypedDict


class ConversationTurn(TypedDict):
    speaker: Literal["user", "agent"]
    text: str
    ts: float
    emotion: str | None
    intent: str | None


class AgentState(TypedDict):
    # ── Call identity ──────────────────────────────────────────────────────────
    call_id: str
    customer_id: str | None

    # ── Conversation history (append-only by convention) ──────────────────────
    transcript: list[ConversationTurn]

    # ── Current turn ──────────────────────────────────────────────────────────
    user_input: str
    user_emotion: str        # neutral | happy | frustrated | angry | sad | confused
    user_urgency: float      # 0.0 – 1.0
    user_intent: str         # inquiry | complaint | booking | purchase | cancel | other

    # ── Routing ───────────────────────────────────────────────────────────────
    active_agent: str        # sales | support | booking | analytics | unknown
    route_confidence: float
    escalate: bool

    # ── Memory context (injected by memory_loader before agent call) ───────────
    customer_profile: dict   # from Postgres
    past_topics: list[str]   # from Neo4j
    semantic_context: str    # top-k ChromaDB results joined as text

    # ── Tool outputs (ephemeral per turn) ─────────────────────────────────────
    tool_results: dict

    # ── Response ──────────────────────────────────────────────────────────────
    agent_response: str
    tts_priority: str        # normal | urgent | calm

    # ── Meta ──────────────────────────────────────────────────────────────────
    turn_number: int
    error: str | None


def initial_state(call_id: str, customer_id: str | None = None) -> AgentState:
    return AgentState(
        call_id=call_id,
        customer_id=customer_id,
        transcript=[],
        user_input="",
        user_emotion="neutral",
        user_urgency=0.0,
        user_intent="inquiry",
        active_agent="unknown",
        route_confidence=0.0,
        escalate=False,
        customer_profile={},
        past_topics=[],
        semantic_context="",
        tool_results={},
        agent_response="",
        tts_priority="normal",
        turn_number=0,
        error=None,
    )
