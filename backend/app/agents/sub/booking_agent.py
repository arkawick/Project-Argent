"""Booking Agent — appointment scheduling, rescheduling, and cancellation."""
from __future__ import annotations

import structlog

from app.agents.state import AgentState
from app.agents.tools.booking_tools import check_available_slots, create_appointment
from app.services.llm_service import ollama_chat, _history_from_transcript

log = structlog.get_logger()

_SYSTEM = """\
You are Riley, an efficient and friendly AI scheduling assistant.
Your goal: help customers book, reschedule, or cancel appointments quickly and accurately.
Always confirm the date and time clearly in your response.
Respond in 1-2 sentences max.

Customer name: {name}
Available slots (next 7 days):
{slots}"""


async def booking_agent_node(state: AgentState) -> dict:
    profile = state["customer_profile"]
    customer_id = state["customer_id"]
    name = profile.get("name") or "there"

    # Fetch available slots
    try:
        slots = await check_available_slots(days_ahead=7)
        slots_str = "\n".join(
            f"  • {s['label']}" for s in slots[:5]
        ) if slots else "  No slots currently available — please try again tomorrow."
    except Exception:
        slots_str = "  Unable to fetch slots right now."
        slots = []

    system = _SYSTEM.format(name=name, slots=slots_str)
    history = _history_from_transcript(state["transcript"])

    # Detect if user confirmed a specific slot and auto-book it
    booked = None
    user_lower = state["user_input"].lower()
    confirmed_slot = next(
        (s for s in slots if _slot_mentioned(s["label"], state["user_input"])), None
    )
    if confirmed_slot and customer_id:
        try:
            booked = await create_appointment(
                customer_id=customer_id,
                call_id=state["call_id"],
                title="Customer Appointment",
                scheduled_at=confirmed_slot["datetime"],
                agent_notes=f"Booked via AI agent. Customer said: '{state['user_input'][:100]}'",
            )
            log.info("booking_agent.appointment_created", slot=confirmed_slot["label"])
        except Exception as e:
            log.warning("booking_agent.book_failed", error=str(e))

    user_input = state["user_input"]
    if booked and not booked.get("error"):
        user_input = f"{user_input} [Appointment confirmed for {confirmed_slot['label']}]"

    try:
        response = await ollama_chat(
            system_prompt=system,
            history=history,
            user_input=user_input,
            temperature=0.5,
        )
    except Exception as e:
        log.error("booking_agent.failed", error=str(e))
        response = "I can help you schedule that! Let me check our availability and find the best time for you."

    tool_results = {**state.get("tool_results", {})}
    if booked:
        tool_results["appointment"] = booked

    return {
        "agent_response": response,
        "active_agent": "booking",
        "tts_priority": "normal",
        "tool_results": tool_results,
    }


def _slot_mentioned(slot_label: str, user_text: str) -> bool:
    """Heuristic: check if the user's message references a specific slot label."""
    label_lower = slot_label.lower()
    text_lower = user_text.lower()
    # Check day name + time overlap
    words = label_lower.split()
    matches = sum(1 for w in words if len(w) > 3 and w in text_lower)
    return matches >= 2
