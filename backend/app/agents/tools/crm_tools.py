"""CRM tools — customer lookup and updates used by agent nodes."""
from __future__ import annotations

import uuid

import structlog

from app.dependencies import AsyncSessionLocal
from app.memory import postgres_store, neo4j_store

log = structlog.get_logger()


async def lookup_customer(customer_id: str | None, phone: str | None = None) -> dict:
    """
    Fetch a customer's profile dict from Postgres.
    Tries by ID first, then falls back to phone.
    Returns an empty dict if not found.
    """
    if not customer_id and not phone:
        return {}

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                customer = None
                if customer_id:
                    try:
                        customer = await postgres_store.get_customer(session, uuid.UUID(customer_id))
                    except (ValueError, Exception):
                        pass
                if customer is None and phone:
                    customer = await postgres_store.get_customer_by_phone(session, phone)

                if customer is None:
                    return {}

                return {
                    "id": str(customer.id),
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "company": customer.company,
                    "tier": customer.tier,
                    "lifetime_value": float(customer.lifetime_value or 0),
                    "tags": customer.tags or [],
                    "preferences": customer.preferences or {},
                    "last_contact": customer.last_contact.isoformat() if customer.last_contact else None,
                }
    except Exception as e:
        log.warning("crm.lookup_failed", error=str(e))
        return {}


async def get_customer_past_topics(customer_id: str, days: int = 90) -> list[str]:
    """Return the topics this customer discussed in the past N days (from Neo4j)."""
    if not customer_id:
        return []
    try:
        records = await neo4j_store.get_customer_topics(customer_id, days=days)
        return [r["topic"] for r in records]
    except Exception as e:
        log.warning("crm.topics_failed", error=str(e))
        return []


async def get_frustration_count(customer_id: str) -> int:
    """Return number of times this customer expressed frustration (from Neo4j)."""
    if not customer_id:
        return 0
    try:
        return await neo4j_store.get_frustration_count(customer_id)
    except Exception as e:
        log.warning("crm.frustration_failed", error=str(e))
        return 0
