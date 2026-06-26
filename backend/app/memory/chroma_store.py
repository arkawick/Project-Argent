from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings

_client: chromadb.AsyncHttpClient | None = None

COLLECTIONS = {
    "call_summaries": "Embeddings of completed call transcripts for semantic search",
    "customer_profiles": "Embeddings of customer preference and history text",
    "knowledge_base": "Product/service documentation for RAG retrieval",
}


async def get_client() -> chromadb.AsyncHttpClient:
    global _client
    if _client is None:
        cfg = get_settings()
        _client = await chromadb.AsyncHttpClient(
            host=cfg.chroma_host,
            port=cfg.chroma_port,
            settings=ChromaSettings(
                chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
                chroma_client_auth_credentials=cfg.chroma_token,
            ),
        )
    return _client


async def ensure_collections() -> None:
    client = await get_client()
    for name in COLLECTIONS:
        await client.get_or_create_collection(name=name)


async def upsert_call_summary(call_id: str, text: str, metadata: dict) -> None:
    client = await get_client()
    col = await client.get_collection("call_summaries")
    await col.upsert(ids=[call_id], documents=[text], metadatas=[metadata])


async def upsert_customer_profile(customer_id: str, text: str, metadata: dict) -> None:
    client = await get_client()
    col = await client.get_collection("customer_profiles")
    await col.upsert(ids=[customer_id], documents=[text], metadatas=[metadata])


async def query_call_summaries(query: str, n_results: int = 3) -> list[dict]:
    client = await get_client()
    col = await client.get_collection("call_summaries")
    results = await col.query(query_texts=[query], n_results=n_results)
    return _format_results(results)


async def query_knowledge_base(query: str, n_results: int = 5) -> list[dict]:
    client = await get_client()
    col = await client.get_collection("knowledge_base")
    results = await col.query(query_texts=[query], n_results=n_results)
    return _format_results(results)


async def query_customer_profile(customer_id: str, query: str, n_results: int = 3) -> list[dict]:
    client = await get_client()
    col = await client.get_collection("customer_profiles")
    results = await col.query(
        query_texts=[query],
        n_results=n_results,
        where={"customer_id": customer_id},
    )
    return _format_results(results)


def _format_results(results: dict) -> list[dict]:
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    return [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(docs, metas, distances)
    ]
