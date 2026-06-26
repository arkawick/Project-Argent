"""
Intent router — classifies the user's intent and selects the appropriate sub-agent.

Makes one Ollama JSON call, then applies business-rule overrides:
  - High urgency + frustrated/angry → support regardless of predicted agent
  - Low confidence → fallback (ask clarifying question)
"""
from __future__ import annotations

import structlog

from app.agents.state import AgentState
from app.services.llm_service import ollama_json

log = structlog.get_logger()

_ROUTER_PROMPT = """\
You are a call-routing classifier. Given the customer's message and context, \
pick the best agent to handle the call.

Agents available:
  sales    — purchase intent, pricing questions, upsell, product interest
  support  — complaints, problems, refunds, technical issues, frustrated customers
  booking  — scheduling, appointments, cancellations, rescheduling
  analytics — business reports, usage statistics (internal staff queries)
  unknown  — unclear intent; ask a clarifying question

Customer's recent topics: {past_topics}
Customer emotion: {emotion}
Customer message: "{user_input}"

Output ONLY valid JSON:
{{"intent": "<short intent label>", "agent": "<sales|support|booking|analytics|unknown>", "confidence": <0.0-1.0>}}

JSON:"""


async def intent_router_node(state: AgentState) -> dict:
    past_topics_str = ", ".join(state["past_topics"]) if state["past_topics"] else "none"

    try:
        result = await ollama_json(
            _ROUTER_PROMPT.format(
                past_topics=past_topics_str,
                emotion=state["user_emotion"],
                user_input=state["user_input"],
            ),
            temperature=0.1,
        )
        agent = result.get("agent", "unknown")
        confidence = float(result.get("confidence", 0.5))
        intent = result.get("intent", "inquiry")

        # Sanitise
        valid_agents = {"sales", "support", "booking", "analytics", "unknown"}
        if agent not in valid_agents:
            agent = "unknown"
        confidence = max(0.0, min(1.0, confidence))

    except Exception as e:
        log.warning("router.failed", error=str(e))
        agent, confidence, intent = "unknown", 0.0, "inquiry"

    log.info("router.decision", agent=agent, confidence=confidence, intent=intent)
    return {
        "active_agent": agent,
        "route_confidence": confidence,
        "user_intent": intent,
    }


def route_to_agent(state: AgentState) -> str:
    """
    Conditional edge function — maps AgentState to a node name.
    Applied AFTER intent_router_node updates the state.
    """
    emotion = state["user_emotion"]
    urgency = state["user_urgency"]
    confidence = state["route_confidence"]
    agent = state["active_agent"]

    # Business override: angry/frustrated + high urgency → always go to support
    if urgency > 0.75 and emotion in ("angry", "frustrated"):
        log.info("router.override", reason="high_urgency_frustrated", target="support_agent")
        return "support_agent"

    # Low confidence → clarifying question
    if confidence < 0.45:
        return "fallback_node"

    node_map = {
        "sales": "sales_agent",
        "support": "support_agent",
        "booking": "booking_agent",
        "analytics": "analytics_agent",
        "unknown": "fallback_node",
    }
    return node_map.get(agent, "fallback_node")
