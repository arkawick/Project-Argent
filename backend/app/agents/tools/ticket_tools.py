"""Ticket tools — create and update support tickets."""
from __future__ import annotations

import uuid

import structlog

from app.dependencies import AsyncSessionLocal
from app.memory import postgres_store, neo4j_store

log = structlog.get_logger()


async def create_ticket(
    customer_id: str,
    call_id: str | None,
    title: str,
    description: str,
    priority: str = "medium",
    category: str = "general",
) -> dict:
    """Create a support ticket in Postgres and link it in Neo4j."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                ticket = await postgres_store.create_ticket(
                    session,
                    customer_id=uuid.UUID(customer_id),
                    call_id=uuid.UUID(call_id) if call_id else None,
                    title=title,
                    description=description,
                    priority=priority,
                    category=category,
                    status="open",
                )
                ticket_id = str(ticket.id)

        await neo4j_store.link_ticket(customer_id, ticket_id)
        log.info("ticket.created", ticket_id=ticket_id, priority=priority)

        return {
            "id": ticket_id,
            "title": title,
            "priority": priority,
            "status": "open",
            "category": category,
        }

    except Exception as e:
        log.error("ticket.create_failed", error=str(e))
        return {"error": str(e)}


async def get_open_tickets(customer_id: str) -> list[dict]:
    """Fetch open tickets for a customer."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                tickets = await postgres_store.get_open_tickets(session, uuid.UUID(customer_id))
                return [
                    {
                        "id": str(t.id),
                        "title": t.title,
                        "priority": t.priority,
                        "status": t.status,
                        "category": t.category,
                    }
                    for t in tickets
                ]
    except Exception as e:
        log.warning("ticket.get_open_failed", error=str(e))
        return []
