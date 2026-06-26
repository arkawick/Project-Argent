# Memory System

AI FrontDesk uses three databases simultaneously, each serving a distinct memory role. Together they give the agent a complete picture of who the caller is and what has happened before.

---

## Overview

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   PostgreSQL     │   │    ChromaDB      │   │     Neo4j        │
│                  │   │                  │   │                  │
│  Structured CRM  │   │ Semantic search  │   │ Relationship     │
│  Transactional   │   │ Vector embeddings│   │ graph traversal  │
│  Source of truth │   │ Fuzzy recall     │   │ Pattern detection│
└──────────────────┘   └──────────────────┘   └──────────────────┘
         ▲                      ▲                      ▲
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                         memory_loader_node
                         memory_writer_node
```

---

## PostgreSQL — transactional memory

**What it stores:** Every piece of structured business data.

### Schema

| Table | Purpose |
|-------|---------|
| `customers` | CRM profile: name, phone, email, tier, lifetime value, tags |
| `calls` | Call records: room ID, status, transcript (JSONB), sentiment, outcome |
| `call_insights` | Per-turn analytics: emotion, intent, confidence, latency, barge-in |
| `tickets` | Support tickets: title, priority, status, resolution |
| `appointments` | Scheduled meetings: datetime, duration, status |

### How agents use it

**Memory loader:**
```python
customer = await get_customer_by_phone(session, phone)
# → customer_profile in AgentState
```

**Support agent:**
```python
open_tickets = await get_open_tickets(customer_id)
# Shows agent Jordan which issues are already tracked
```

**Booking agent:**
```python
slots = await get_available_slots(db)
# Checks appointments table for conflicts
```

**Memory writer:**
```python
await add_insight(session, call_id=..., emotion="frustrated", latency_ms=820)
```

---

## ChromaDB — semantic memory

**What it stores:** Dense vector embeddings of call summaries and knowledge base articles.

### Collections

| Collection | Content | Used by |
|------------|---------|---------|
| `call_summaries` | One embedding per conversation turn | All agents (context retrieval) |
| `customer_profiles` | Customer preference summary | Sales agent |
| `knowledge_base` | Product/policy articles | Sales and Support agents |

### How agents use it

**Memory loader** (at turn start):
```python
results = await query_call_summaries(customer_id, query_text=user_input, n=3)
# state["semantic_context"] = ["User asked about refund policy last Tuesday...", ...]
```

Each retrieved snippet is injected into the sub-agent's system prompt as "relevant past context", giving the agent long-term conversational memory without loading the full transcript.

**Memory writer** (at turn end):
```python
await upsert_call_summary(call_id, turn_number, text=f"User: {user_input} | Agent: {response}")
```

**Knowledge base search** (inside sub-agents):
```python
kb_context = await search_knowledge_base(user_input, n=2)
# Returns top-2 relevant articles embedded at startup or seeded via scripts/seed_db.py
```

### Embedding model

ChromaDB uses its default embedding function (`all-MiniLM-L6-v2` via the `chromadb` Python package) — a 384-dimension sentence transformer that runs on CPU and requires no separate setup.

---

## Neo4j — relationship memory

**What it stores:** The graph of who called about what, how they felt, and how entities relate.

### Graph schema

```
(Customer)-[:MADE]->(Call)
(Call)-[:DISCUSSES]->(Topic)
(Call)-[:EXPRESSED]->(Emotion)
(Customer)-[:HAS_TOPIC]->(Topic)
(Call)-[:HAS_TICKET]->(Ticket)
(Call)-[:HAS_APPOINTMENT]->(Appointment)
```

**Node properties:**

| Node | Properties |
|------|-----------|
| Customer | id, name, phone, tier |
| Call | id, room_id, started_at |
| Topic | name |
| Emotion | name, intensity |
| Ticket | id, title, status |
| Appointment | id, scheduled_at |

### How agents use it

**Memory loader:**
```python
past_topics = await get_customer_topics(customer_id)
# → ["billing", "shipping delay", "product upgrade"]
# Injected into system prompt so agent knows recurring themes

frustration = await get_frustration_count(customer_id)
# → 3  (3 prior calls with angry/frustrated emotion)
# Triggers "handle with extra care" instruction to support agent
```

**Memory writer:**
```python
await record_topic(call_id, customer_id, topic="refund request")
await record_emotion(call_id, customer_id, emotion="frustrated", intensity=0.82)
```

**Analytics:**
```python
# GET /api/customers/{id}/graph
topics = await get_customer_topics(customer_id)
frustration = await get_frustration_count(customer_id)
# Returns: is_repeat_complainer = frustration >= 3
```

### Why Neo4j for this?

The key query is: *"What topics does this customer keep coming back to?"* This is a 2-hop graph traversal:

```cypher
MATCH (c:Customer {id: $id})-[:MADE]->(:Call)-[:DISCUSSES]->(t:Topic)
RETURN t.name, count(*) as frequency
ORDER BY frequency DESC
```

This is trivial in Cypher but awkward in SQL (requires joining calls → call_insights → grouping). As the conversation graph grows, more complex patterns become possible: common topic co-occurrence, emotion escalation paths, agent performance by topic.

---

## Memory lifecycle

```
Call starts
    │
    ▼
memory_loader_node
    ├── Postgres:  load customer profile
    ├── Neo4j:     load past topics + frustration count
    └── Chroma:    semantic search relevant past turns
    │
    [sub-agent uses enriched context]
    │
    ▼
memory_writer_node
    ├── Postgres:  insert CallInsight row
    ├── Chroma:    upsert turn summary embedding
    └── Neo4j:     create/update Topic + Emotion nodes
    │
    ▼
Call ends
    ├── Postgres:  update Call.status, Call.ended_at, Call.duration_secs
    └── Chroma:    call summary available for future calls
```

---

## Adding knowledge base articles

The knowledge base is a ChromaDB collection. To add articles:

```python
from app.memory.chroma_store import upsert_knowledge_base

await upsert_knowledge_base(
    doc_id="kb-refund-policy",
    text="Our refund policy allows returns within 30 days of purchase...",
    metadata={"category": "policy", "topic": "refunds"},
)
```

Or add them in bulk via `scripts/seed_db.py`.
