from __future__ import annotations

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import get_settings

_driver: AsyncDriver | None = None

# Cypher run once at startup to create constraints and indexes
_INIT_CYPHER = [
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT call_id IF NOT EXISTS FOR (c:Call) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT emotion_name IF NOT EXISTS FOR (e:Emotion) REQUIRE e.name IS UNIQUE",
    "CREATE INDEX customer_phone IF NOT EXISTS FOR (c:Customer) ON (c.phone)",
]


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        cfg = get_settings()
        _driver = AsyncGraphDatabase.driver(
            cfg.neo4j_uri,
            auth=(cfg.neo4j_user, cfg.neo4j_password),
        )
    return _driver


async def init_graph() -> None:
    driver = await get_driver()
    async with driver.session() as session:
        for stmt in _INIT_CYPHER:
            await session.run(stmt)


async def close() -> None:
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


# ── Write helpers ──────────────────────────────────────────────────────────────

async def upsert_customer(customer_id: str, name: str, phone: str | None, tier: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (c:Customer {id: $id})
            SET c.name = $name, c.phone = $phone, c.tier = $tier
            """,
            id=customer_id, name=name, phone=phone, tier=tier,
        )


async def link_call_to_customer(customer_id: str, call_id: str, started_at: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (c:Customer {id: $cid})
            MERGE (call:Call {id: $callid})
            SET call.started_at = $started_at
            MERGE (c)-[:PLACED {at: datetime($started_at)}]->(call)
            """,
            cid=customer_id, callid=call_id, started_at=started_at,
        )


async def record_topic(customer_id: str, call_id: str, topic: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (t:Topic {name: $topic})
            MERGE (call:Call {id: $callid})
            MERGE (call)-[:DISCUSSED]->(t)
            MERGE (c:Customer {id: $cid})
            """,
            topic=topic.lower(), callid=call_id, cid=customer_id,
        )


async def record_emotion(customer_id: str, call_id: str, emotion: str, turn: int, confidence: float) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (e:Emotion {name: $emotion})
            MERGE (c:Customer {id: $cid})
            CREATE (c)-[:EXPRESSED {turn: $turn, confidence: $conf, call_id: $callid}]->(e)
            """,
            emotion=emotion, cid=customer_id, turn=turn, conf=confidence, callid=call_id,
        )


async def link_ticket(customer_id: str, ticket_id: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (c:Customer {id: $cid})
            MERGE (t:Ticket {id: $tid})
            MERGE (c)-[:HAS_TICKET]->(t)
            """,
            cid=customer_id, tid=ticket_id,
        )


async def link_appointment(customer_id: str, appointment_id: str, scheduled_at: str) -> None:
    driver = await get_driver()
    async with driver.session() as session:
        await session.run(
            """
            MERGE (c:Customer {id: $cid})
            MERGE (a:Appointment {id: $aid})
            SET a.scheduled_at = datetime($scheduled_at)
            MERGE (c)-[:HAS_APPOINTMENT]->(a)
            """,
            cid=customer_id, aid=appointment_id, scheduled_at=scheduled_at,
        )


# ── Read helpers ───────────────────────────────────────────────────────────────

async def get_customer_topics(customer_id: str, days: int = 90) -> list[dict]:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Customer {id: $cid})-[:PLACED]->(call:Call)-[:DISCUSSED]->(t:Topic)
            WHERE call.started_at > datetime() - duration({days: $days})
            RETURN t.name AS topic, count(*) AS freq
            ORDER BY freq DESC
            """,
            cid=customer_id, days=days,
        )
        return [{"topic": r["topic"], "freq": r["freq"]} async for r in result]


async def get_frustration_count(customer_id: str) -> int:
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Customer {id: $cid})-[:EXPRESSED]->(e:Emotion {name: 'frustrated'})
            RETURN count(*) AS cnt
            """,
            cid=customer_id,
        )
        record = await result.single()
        return record["cnt"] if record else 0
