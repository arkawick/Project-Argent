"""Sales Agent — handles purchase intent, pricing, and upsell."""
from __future__ import annotations

import structlog

from app.agents.state import AgentState
from app.agents.tools.rag_tools import search_knowledge_base
from app.agents.tools.memory_tools import search_call_summaries
from app.services.llm_service import ollama_chat, _history_from_transcript

log = structlog.get_logger()

_SYSTEM = """\
You are Alex, an enthusiastic and knowledgeable AI sales specialist.
Your goal: understand customer needs, explain value clearly, and help them make confident decisions.
Respond in 1-2 sentences max. Be conversational, warm, and concise.
Never make up pricing — say "I'll get you the exact figure" if unsure.

Customer tier: {tier}
Customer name: {name}
Past topics: {past_topics}
Relevant product info:
{kb_context}
Prior conversation context:
{semantic_context}"""


async def sales_agent_node(state: AgentState) -> dict:
    profile = state["customer_profile"]
    tier = profile.get("tier", "standard")
    name = profile.get("name") or "there"

    # Fetch relevant knowledge base snippets for this query
    kb_context = await search_knowledge_base(state["user_input"])
    semantic_context = state["semantic_context"] or "None available."

    system = _SYSTEM.format(
        tier=tier,
        name=name,
        past_topics=", ".join(state["past_topics"]) or "none",
        kb_context=kb_context or "No product info found.",
        semantic_context=semantic_context,
    )

    # Tone adjustment for VIP customers
    if tier == "vip":
        system += "\nThis is a VIP customer — prioritise exclusivity and personalised service."

    history = _history_from_transcript(state["transcript"])

    try:
        response = await ollama_chat(
            system_prompt=system,
            history=history,
            user_input=state["user_input"],
            temperature=0.75,
        )
    except Exception as e:
        log.error("sales_agent.failed", error=str(e))
        response = "I'd love to help with that! Could you give me just a moment to pull up the details for you?"

    return {"agent_response": response, "active_agent": "sales", "tts_priority": "normal"}
