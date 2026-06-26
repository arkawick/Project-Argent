"""
LangGraph agent graph — compiled once at import time.

Flow:
  START → memory_loader → emotion_classifier → intent_router
       → [sales|support|booking|analytics|fallback]
       → memory_writer → END

Import `agent_graph` and call `await agent_graph.ainvoke(state)`.
"""
from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph

from app.agents.state import AgentState
from app.agents.router import intent_router_node, route_to_agent
from app.agents.sub.analytics_agent import analytics_agent_node
from app.agents.sub.booking_agent import booking_agent_node
from app.agents.sub.sales_agent import sales_agent_node
from app.agents.sub.support_agent import support_agent_node
from app.services.emotion_service import classify as classify_emotion

log = structlog.get_logger()


# ── Node implementations ───────────────────────────────────────────────────────

async def memory_loader_node(state: AgentState) -> dict:
    """Load customer profile, past topics, and semantic context before agent call."""
    from app.agents.tools.crm_tools import lookup_customer, get_customer_past_topics, get_frustration_count
    from app.agents.tools.memory_tools import search_call_summaries

    customer_id = state["customer_id"]

    profile = await lookup_customer(customer_id)
    past_topics = await get_customer_past_topics(customer_id) if customer_id else []
    semantic_context = await search_call_summaries(state["user_input"], customer_id=customer_id)
    frustration_count = await get_frustration_count(customer_id) if customer_id else 0

    return {
        "customer_profile": profile,
        "past_topics": past_topics,
        "semantic_context": semantic_context,
        "tool_results": {
            **state.get("tool_results", {}),
            "frustration_count": frustration_count,
        },
    }


async def emotion_classifier_node(state: AgentState) -> dict:
    """Classify emotion and urgency from the user's latest utterance."""
    emotion, urgency = await classify_emotion(state["user_input"])
    return {"user_emotion": emotion, "user_urgency": urgency}


async def fallback_node(state: AgentState) -> dict:
    """Ask a clarifying question when intent is unclear."""
    return {
        "agent_response": "I want to make sure I help you in the best way. Could you tell me a bit more about what you need today?",
        "active_agent": "unknown",
        "tts_priority": "normal",
    }


async def memory_writer_node(state: AgentState) -> dict:
    """
    Persist this turn's insights to all three stores after the agent responds.
    Runs after every turn; failures are logged but never crash the call.
    """
    from datetime import datetime, timezone

    import uuid

    from app.dependencies import AsyncSessionLocal
    from app.memory import postgres_store, neo4j_store, chroma_store

    call_id = state["call_id"]
    customer_id = state["customer_id"]
    turn_n = state["turn_number"]
    now = datetime.now(timezone.utc)

    # 1. Write call_insight row to Postgres
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await postgres_store.add_insight(
                    session,
                    call_id=uuid.UUID(call_id),
                    turn_number=turn_n,
                    speaker="user",
                    text=state["user_input"],
                    emotion=state["user_emotion"],
                    emotion_conf=None,
                    intent=state["user_intent"],
                    intent_conf=state["route_confidence"],
                    barge_in=False,
                )
    except Exception as e:
        log.warning("memory_writer.postgres_failed", error=str(e))

    # 2. Write emotion + topic to Neo4j
    if customer_id:
        try:
            await neo4j_store.record_emotion(
                customer_id, call_id, state["user_emotion"], turn_n, state["user_urgency"]
            )
            if state["user_intent"] not in ("inquiry", "other", ""):
                await neo4j_store.record_topic(customer_id, call_id, state["user_intent"])
        except Exception as e:
            log.warning("memory_writer.neo4j_failed", error=str(e))

    # 3. Upsert turn summary to ChromaDB
    try:
        summary_text = (
            f"Turn {turn_n} — Customer: '{state['user_input']}' | "
            f"Agent ({state['active_agent']}): '{state['agent_response']}'"
        )
        await chroma_store.upsert_call_summary(
            call_id=f"{call_id}_{turn_n}",
            text=summary_text,
            metadata={
                "call_id": call_id,
                "turn": turn_n,
                "emotion": state["user_emotion"],
                "intent": state["user_intent"],
                "agent": state["active_agent"],
            },
        )
    except Exception as e:
        log.warning("memory_writer.chroma_failed", error=str(e))

    # Increment turn counter for next round
    return {"turn_number": turn_n + 1}


# ── Graph compilation ──────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("memory_loader", memory_loader_node)
    builder.add_node("emotion_classifier", emotion_classifier_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("sales_agent", sales_agent_node)
    builder.add_node("support_agent", support_agent_node)
    builder.add_node("booking_agent", booking_agent_node)
    builder.add_node("analytics_agent", analytics_agent_node)
    builder.add_node("fallback_node", fallback_node)
    builder.add_node("memory_writer", memory_writer_node)

    # Linear pre-routing
    builder.add_edge(START, "memory_loader")
    builder.add_edge("memory_loader", "emotion_classifier")
    builder.add_edge("emotion_classifier", "intent_router")

    # Conditional dispatch
    builder.add_conditional_edges(
        "intent_router",
        route_to_agent,
        {
            "sales_agent": "sales_agent",
            "support_agent": "support_agent",
            "booking_agent": "booking_agent",
            "analytics_agent": "analytics_agent",
            "fallback_node": "fallback_node",
        },
    )

    # All sub-agents → memory_writer → END
    for node in ("sales_agent", "support_agent", "booking_agent", "analytics_agent", "fallback_node"):
        builder.add_edge(node, "memory_writer")

    builder.add_edge("memory_writer", END)

    return builder.compile()


# Singleton — compiled once at module import
agent_graph = _build_graph()
