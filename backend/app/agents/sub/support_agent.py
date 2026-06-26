"""Support Agent — handles complaints, refunds, and technical issues."""
from __future__ import annotations

import structlog

from app.agents.state import AgentState
from app.agents.tools.ticket_tools import create_ticket, get_open_tickets
from app.agents.tools.rag_tools import search_knowledge_base
from app.services.llm_service import ollama_chat, _history_from_transcript

log = structlog.get_logger()

_SYSTEM = """\
You are Jordan, an empathetic and solution-focused AI support specialist.
Your goal: acknowledge the customer's frustration, resolve the issue if possible, or escalate with clear next steps.
Respond in 1-2 sentences max. Be warm, patient, and professional.
If you create a ticket, mention the ticket reference naturally.

Customer name: {name}
Customer tier: {tier}
Open tickets: {open_tickets}
Frustration history: {frustration_note}
Relevant knowledge:
{kb_context}"""


async def support_agent_node(state: AgentState) -> dict:
    profile = state["customer_profile"]
    customer_id = state["customer_id"]
    name = profile.get("name") or "there"
    tier = profile.get("tier", "standard")

    # Fetch open tickets and knowledge base context in parallel
    import asyncio

    async def _no_tickets():
        return []

    open_tickets_raw, kb_context = await asyncio.gather(
        get_open_tickets(customer_id) if customer_id else _no_tickets(),
        search_knowledge_base(state["user_input"]),
    )

    open_ticket_str = (
        ", ".join(t["title"] for t in open_tickets_raw) if open_tickets_raw else "none"
    )

    # Check if this is a repeat complainer (from Neo4j, already in tool_results if set)
    frustration_count = state.get("tool_results", {}).get("frustration_count", 0)
    frustration_note = (
        f"This customer has expressed frustration {frustration_count} times previously. Handle with extra care."
        if frustration_count >= 2
        else "First or second frustration — standard empathetic tone."
    )

    system = _SYSTEM.format(
        name=name,
        tier=tier,
        open_tickets=open_ticket_str,
        frustration_note=frustration_note,
        kb_context=kb_context or "No relevant articles found.",
    )

    history = _history_from_transcript(state["transcript"])

    # Create a ticket automatically if this looks like an escalation
    ticket_created = None
    if state["user_urgency"] > 0.6 and customer_id:
        try:
            ticket_created = await create_ticket(
                customer_id=customer_id,
                call_id=state["call_id"],
                title=f"Customer issue: {state['user_intent']}",
                description=state["user_input"],
                priority="high" if state["user_urgency"] > 0.8 else "medium",
                category=state["user_intent"],
            )
            log.info("support_agent.ticket_auto_created", ticket_id=ticket_created.get("id"))
        except Exception as e:
            log.warning("support_agent.ticket_failed", error=str(e))

    # Append ticket ref to the user input context so the LLM can mention it
    user_input = state["user_input"]
    if ticket_created and not ticket_created.get("error"):
        ticket_id_short = ticket_created["id"][:8]
        user_input = f"{user_input} [Ticket #{ticket_id_short} created automatically]"

    try:
        response = await ollama_chat(
            system_prompt=system,
            history=history,
            user_input=user_input,
            temperature=0.6,
        )
    except Exception as e:
        log.error("support_agent.failed", error=str(e))
        response = "I completely understand and I'm sorry you're experiencing this. Let me escalate this right away and make sure it gets resolved quickly."

    tool_results = {**state.get("tool_results", {})}
    if ticket_created:
        tool_results["ticket"] = ticket_created

    tts_priority = "calm" if state["user_emotion"] in ("angry", "frustrated") else "normal"
    return {
        "agent_response": response,
        "active_agent": "support",
        "tts_priority": tts_priority,
        "tool_results": tool_results,
    }
