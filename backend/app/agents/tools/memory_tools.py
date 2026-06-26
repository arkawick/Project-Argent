"""Memory tools — semantic search (ChromaDB) and graph queries (Neo4j)."""
from __future__ import annotations

import structlog

from app.memory import chroma_store, neo4j_store

log = structlog.get_logger()


async def search_call_summaries(query: str, customer_id: str | None = None, n: int = 3) -> str:
    """
    Search past call summaries for semantically similar content.
    Returns top-k results joined as a single context string.
    """
    try:
        if customer_id:
            results = await chroma_store.query_customer_profile(customer_id, query, n_results=n)
        else:
            results = await chroma_store.query_call_summaries(query, n_results=n)

        if not results:
            return ""

        snippets = [r["text"] for r in results if r.get("text")]
        return "\n---\n".join(snippets[:n])

    except Exception as e:
        log.warning("memory.search_failed", error=str(e))
        return ""


async def get_customer_graph_context(customer_id: str) -> dict:
    """
    Pull relationship context from Neo4j for this customer:
    - topics they've discussed
    - frustration count
    Returns a context dict for injecting into agent prompts.
    """
    if not customer_id:
        return {}
    try:
        topics = await neo4j_store.get_customer_topics(customer_id)
        frustration = await neo4j_store.get_frustration_count(customer_id)
        return {
            "past_topics": [t["topic"] for t in topics],
            "frustration_count": frustration,
            "is_repeat_complainer": frustration >= 3,
        }
    except Exception as e:
        log.warning("memory.graph_context_failed", error=str(e))
        return {}
