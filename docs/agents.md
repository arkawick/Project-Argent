# Multi-Agent System

AI FrontDesk uses a LangGraph `StateGraph` to orchestrate a pipeline of specialist agents. The graph is compiled once at startup and reused for every conversational turn.

---

## State

Every node in the graph reads from and writes to `AgentState` (a `TypedDict`):

```python
class AgentState(TypedDict):
    # Call context
    call_id: str
    customer_id: str | None
    transcript: list[dict]       # full conversation history
    turn_number: int

    # Current turn input
    user_input: str

    # Classification outputs
    user_emotion: str | None     # happy / neutral / frustrated / angry / confused / excited / sad
    user_urgency: float          # 0.0–1.0
    user_intent: str | None      # sales / support / booking / analytics / unknown
    active_agent: str | None
    route_confidence: float      # 0.0–1.0

    # Control flags
    escalate: bool               # True → override routing

    # Memory context loaded for this turn
    customer_profile: dict
    past_topics: list[str]
    semantic_context: list[str]

    # Sub-agent outputs
    tool_results: dict
    agent_response: str
    tts_priority: str            # "normal" | "calm" (for frustrated users)

    error: str | None
```

---

## Graph topology

```
START
  │
  ▼
memory_loader_node      ← Postgres CRM + Neo4j graph + Chroma semantic search
  │
  ▼
emotion_classifier_node ← Qwen3:4b JSON: {emotion, urgency}
  │
  ▼
intent_router_node      ← Qwen3:4b JSON: {intent, confidence}
  │
  ├─(sales)────────────► sales_agent_node
  ├─(support)──────────► support_agent_node
  ├─(booking)──────────► booking_agent_node
  ├─(analytics)────────► analytics_agent_node
  └─(low confidence / unknown)► fallback_node
                │
                ▼
         memory_writer_node  ← Postgres insight + Chroma summary + Neo4j edges
                │
                ▼
              END
```

The `route_to_agent` conditional edge also overrides routing based on emotion:
- `urgency > 0.75` AND emotion is `angry` or `frustrated` → always route to `support_agent`
- `confidence < 0.45` → route to `fallback_node` (asks user to rephrase)

---

## Nodes

### `memory_loader_node`

Runs three memory lookups in parallel:

1. **Postgres** — fetches full `Customer` row by phone or ID; loads last 10 transcript turns
2. **Neo4j** — fetches topics this customer has raised before; counts prior frustration events
3. **ChromaDB** — semantic search for similar past calls using the current `user_input`

All results are merged into `AgentState` fields (`customer_profile`, `past_topics`, `semantic_context`).

### `emotion_classifier_node`

Single Ollama JSON call:

```json
{"emotion": "frustrated", "urgency": 0.82}
```

Prompt gives the model the last 3 transcript turns plus the current utterance. Temperature is 0.1 for consistent classification.

### `intent_router_node`

Single Ollama JSON call:

```json
{"intent": "support", "confidence": 0.91, "reason": "user reports missing order"}
```

The `reason` field is ignored at runtime but improves classification quality via chain-of-thought pressure.

### Sub-agents

Each sub-agent is a dedicated node with a defined persona and set of tools:

| Agent | Persona | Key tools | Auto-action |
|-------|---------|-----------|-------------|
| `sales_agent` | Alex | `search_knowledge_base`, Chroma semantic | VIP tone adjustment |
| `support_agent` | Jordan | `get_open_tickets`, `create_ticket` | Auto-creates ticket if urgency > 0.6 |
| `booking_agent` | Riley | `check_available_slots`, `create_appointment` | Auto-books on confirmed slot |
| `analytics_agent` | (system) | Live Postgres aggregates | None |
| `fallback_node` | (system) | None | Asks user to rephrase |

Each sub-agent builds a system prompt enriched with:
- The agent persona and role
- Customer tier (VIP gets warmer tone)
- Relevant context from memory (past topics, open tickets, etc.)
- The last N turns of conversation

The LLM call uses `ollama_chat()` (a streaming-compatible Ollama `/api/chat` call) with temperature 0.7 for natural-sounding responses.

### `memory_writer_node`

After the sub-agent responds, three writes happen in parallel:

1. **Postgres** — inserts a `CallInsight` row: emotion, intent, confidence, latency, barge-in flag
2. **ChromaDB** — upserts a turn summary into the `call_summaries` collection
3. **Neo4j** — creates/updates `Topic` and `Emotion` nodes; links them to the `Customer` and `Call` nodes

---

## Tools

Tools are async functions that sub-agents call directly (not via LangChain's tool-calling mechanism — they are invoked imperatively inside each node):

| Tool | Source | Description |
|------|--------|-------------|
| `lookup_customer` | CRM (Postgres) | Fetch customer by ID |
| `get_customer_past_topics` | Neo4j | Topics this customer raised before |
| `get_frustration_count` | Neo4j | Number of prior frustrated interactions |
| `check_available_slots` | Booking (Postgres) | Next N 30-min weekday slots |
| `create_appointment` | Postgres | Insert appointment row |
| `create_ticket` | Postgres | Insert ticket row |
| `get_open_tickets` | Postgres | Open/in-progress tickets for customer |
| `search_knowledge_base` | ChromaDB | Semantic search over KB collection |
| `search_call_summaries` | ChromaDB | Semantic search over past call summaries |
| `get_customer_graph_context` | Neo4j | Full customer subgraph as structured text |

---

## Extending the system

### Adding a new agent

1. Create `backend/app/agents/sub/my_agent.py` with an `async def my_agent_node(state: AgentState) -> AgentState` function
2. Add the node and an edge in `backend/app/agents/graph.py`
3. Add a routing case in `backend/app/agents/router.py` (the intent router prompt)

### Adding a new tool

1. Create the tool function in `backend/app/agents/tools/`
2. Import and call it directly in the relevant sub-agent node

### Changing the LLM

Edit `OLLAMA_MODEL` in `.env`. Any Ollama-hosted model works. For JSON-mode calls (emotion, router), the model must support `format: "json"`. Tested with:
- `qwen3:4b` (default, Q4, 2.3 GB VRAM)
- `llama3.2:3b` (faster, slightly lower quality)
- `mistral:7b-instruct-q4_0` (higher quality, needs 4+ GB VRAM alone)
