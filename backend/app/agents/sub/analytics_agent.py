"""Analytics Agent — answers business intelligence queries from staff."""
from __future__ import annotations

import structlog
from sqlalchemy import func, select

from app.agents.state import AgentState
from app.dependencies import AsyncSessionLocal
from app.models import Call, CallInsight, Ticket
from app.services.llm_service import ollama_chat, _history_from_transcript

log = structlog.get_logger()

_SYSTEM = """\
You are an AI analytics assistant helping business staff understand performance metrics.
Provide clear, concise, data-driven answers. Use the metrics below to inform your response.
Respond in 2-3 sentences max.

Live metrics:
{metrics}"""


async def analytics_agent_node(state: AgentState) -> dict:
    metrics = await _fetch_metrics()
    metrics_str = "\n".join(f"  {k}: {v}" for k, v in metrics.items())

    system = _SYSTEM.format(metrics=metrics_str)
    history = _history_from_transcript(state["transcript"])

    try:
        response = await ollama_chat(
            system_prompt=system,
            history=history,
            user_input=state["user_input"],
            temperature=0.4,
        )
    except Exception as e:
        log.error("analytics_agent.failed", error=str(e))
        response = f"Based on current data: {metrics_str[:200]}"

    return {
        "agent_response": response,
        "active_agent": "analytics",
        "tts_priority": "normal",
        "tool_results": {"metrics": metrics},
    }


async def _fetch_metrics() -> dict:
    """Pull summary metrics from Postgres for the analytics agent."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                total_calls = await session.scalar(select(func.count(Call.id)))
                active_calls = await session.scalar(
                    select(func.count(Call.id)).where(Call.status == "active")
                )
                open_tickets = await session.scalar(
                    select(func.count(Ticket.id)).where(Ticket.status.in_(["open", "in_progress"]))
                )
                avg_sentiment = await session.scalar(
                    select(func.avg(Call.sentiment_score)).where(Call.sentiment_score.isnot(None))
                )
                top_emotion_row = await session.execute(
                    select(CallInsight.emotion, func.count(CallInsight.id).label("cnt"))
                    .where(CallInsight.emotion.isnot(None))
                    .group_by(CallInsight.emotion)
                    .order_by(func.count(CallInsight.id).desc())
                    .limit(1)
                )
                top_emotion_row = top_emotion_row.first()

        return {
            "total_calls": total_calls or 0,
            "active_calls": active_calls or 0,
            "open_tickets": open_tickets or 0,
            "avg_sentiment": f"{float(avg_sentiment):.2f}" if avg_sentiment else "N/A",
            "top_emotion": top_emotion_row[0] if top_emotion_row else "N/A",
        }
    except Exception as e:
        log.warning("analytics.fetch_failed", error=str(e))
        return {}
