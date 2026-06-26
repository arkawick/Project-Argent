"""RAG tools — knowledge base retrieval for agent context."""
from __future__ import annotations

import structlog

from app.memory import chroma_store

log = structlog.get_logger()


async def search_knowledge_base(query: str, n: int = 4) -> str:
    """
    Retrieve relevant snippets from the knowledge base collection.
    Returns joined text for injection into agent system prompts.
    """
    try:
        results = await chroma_store.query_knowledge_base(query, n_results=n)
        if not results:
            return ""
        snippets = [r["text"] for r in results if r.get("text")]
        return "\n\n".join(snippets)
    except Exception as e:
        log.warning("rag.search_failed", error=str(e))
        return ""
