# AI FrontDesk

An open-source autonomous front-office operating system built on a fully local, GPU-accelerated voice AI stack. Inspired by Retell AI, AI FrontDesk adds persistent memory, multi-agent routing, and a live analytics dashboard — all running on a single developer machine.

```
Browser mic → LiveKit (WebRTC) → Whisper STT → LangGraph → Piper TTS → Browser speaker
                                                    ↓
                              Postgres + ChromaDB + Neo4j (3-layer memory)
```

---

## What it does

- **Real-time voice calls** — browser microphone in, AI voice out, ~2–3 s turn-around on a GTX 1050 Ti
- **Intent routing** — classifies each utterance and dispatches to the right specialist agent (Sales · Support · Booking · Analytics)
- **Emotion detection** — detects happy / frustrated / angry in real time; overrides routing when urgency spikes
- **Persistent memory** — every call is stored in Postgres, semantically indexed in ChromaDB, and graphed in Neo4j
- **Live dashboard** — WebSocket-fed metrics, emotion trends, intent breakdown, per-agent performance
- **CRM** — customer tier management, full call history, ticket queue, appointment scheduling

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Voice I/O | LiveKit (WebRTC), webrtcvad |
| STT | Faster-Whisper (CUDA, `small` model) |
| LLM | Ollama + Qwen3:4b (Q4 quantised) |
| TTS | Piper (`en_US-lessac-medium`, CPU) |
| Orchestration | LangGraph `StateGraph` |
| API | FastAPI + Uvicorn |
| Primary DB | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Vector DB | ChromaDB |
| Graph DB | Neo4j 5 Community + APOC |
| Cache / Lock | Redis 7 |
| Frontend | Next.js 14 App Router, Tailwind CSS, Recharts |
| Infra | Docker Compose |

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Docker Desktop ≥ 24 | With Compose v2 |
| NVIDIA GPU | GTX 1050 Ti (4 GB VRAM) or better |
| NVIDIA Container Toolkit | For GPU passthrough into Docker containers |
| Node.js ≥ 20 | For local frontend dev |
| Python 3.11 | For local backend dev (optional — Docker handles it) |

> **Windows users:** the helper scripts (`healthcheck.sh`, `pull_models.sh`) require **Git Bash** or **WSL2**. All `docker compose` commands work normally in PowerShell or CMD.

---

## Quick start

### 1 — Clone and configure

```bash
git clone <repo-url> ai-frontdesk
cd ai-frontdesk

cp .env.example .env
```

Open `.env` and set strong values for every password field. Generate a `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2 — Start infrastructure services

```bash
docker compose up -d
```

This starts six services: **PostgreSQL · Redis · ChromaDB · Neo4j · LiveKit · Ollama**

Wait ~30 seconds, then verify everything is healthy:

```bash
bash scripts/healthcheck.sh          # Git Bash / WSL2 on Windows
```

### 3 — Pull AI models (one-time)

```bash
bash scripts/pull_models.sh
```

Downloads **Qwen3:4b** into Ollama (~2.5 GB) and the **Piper en_US-lessac-medium** ONNX voice model (~60 MB) into `piper-models/`.

### 4 — Seed demo data (optional but recommended)

```bash
# Via Docker (infra must be running):
docker compose run --rm \
  -e DATABASE_URL=postgresql+asyncpg://argent:${POSTGRES_PASSWORD}@localhost:5432/argent \
  --network host \
  python scripts/seed_db.py

# Or locally (with backend deps installed):
DATABASE_URL=postgresql+asyncpg://argent:<your-password>@localhost:5432/argent \
  python scripts/seed_db.py
```

Creates 3 demo customers (VIP, Premium, Standard), 2 completed calls with transcripts, 1 appointment, and 1 open ticket.

### 5 — Start the backend

**Option A — Docker (recommended for first run):**

```bash
docker compose --profile app up -d backend
```

Database migrations run automatically on container start. Logs:

```bash
docker compose logs -f backend
```

**Option B — Local Python (faster iteration):**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Export required env vars (or use a .env loader like python-dotenv)
export DATABASE_URL=postgresql+asyncpg://argent:<your-password>@localhost:5432/argent
export REDIS_URL=redis://:<your-redis-password>@localhost:6379/0
# ... (see .env.example for the full list)

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend available at: `http://localhost:8000`  
Interactive API docs (Swagger UI): `http://localhost:8000/docs`

### 6 — Start the frontend

```bash
cd frontend
npm install

cp .env.example .env.local
# Defaults already point to localhost — no edits needed for local dev

npm run dev
```

Frontend available at: `http://localhost:3000`

---

## First login

| Field | Value |
|-------|-------|
| URL | `http://localhost:3000/login` |
| Username | `admin` (or your `STAFF_USERNAME` in `.env`) |
| Password | `changeme` (or your `STAFF_PASSWORD` in `.env`) |

---

## Running a demo call

1. Go to **Demo Call** in the sidebar or navigate to `/demo`
2. Click **Start Demo Call** — your browser will request microphone permission
3. Speak naturally — the agent will respond in real time through your speaker
4. Try different intents:
   - *"I'd like to upgrade my plan"* → Sales agent (Alex)
   - *"My order hasn't arrived and I'm frustrated"* → Support agent (Jordan)
   - *"Can I book an appointment for next Tuesday?"* → Booking agent (Riley)
   - *"How many calls did you handle today?"* → Analytics agent
5. Click **End Call** — the full transcript and emotion insights are saved automatically

---

## Environment variables

Full list in [`.env.example`](.env.example). Key variables:

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL password (user: `argent`, db: `argent`) |
| `REDIS_PASSWORD` | Redis password |
| `NEO4J_PASSWORD` | Neo4j password |
| `LIVEKIT_API_KEY` | LiveKit API key (any string) |
| `LIVEKIT_API_SECRET` | LiveKit secret (must be ≥ 32 characters) |
| `SECRET_KEY` | JWT signing key (≥ 32 chars — use `secrets.token_hex(32)`) |
| `STAFF_USERNAME` | Dashboard login username (default: `admin`) |
| `STAFF_PASSWORD` | Dashboard login password (default: `changeme`) |
| `OLLAMA_MODEL` | Ollama model (default: `qwen3:4b`) |
| `PIPER_MODEL` | Piper voice model (default: `en_US-lessac-medium`) |

---

## Service ports

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 3000 | Next.js dev server |
| Backend API | 8000 | FastAPI + Uvicorn |
| LiveKit HTTP/WS | 7880 | WebRTC signalling |
| LiveKit RTC TCP | 7881 | WebRTC media fallback |
| LiveKit RTC UDP | 50200–50220 | WebRTC media (primary) |
| PostgreSQL | 5433 | Host port (container listens on 5432 internally) |
| Redis | 6380 | Host port (container listens on 6379 internally) |
| ChromaDB | 8002 | Host port (container listens on 8000 internally) |
| Neo4j Browser | 7475 | Admin UI (`neo4j` / your password) |
| Neo4j Bolt | 7688 | Host port (container uses 7687 internally) |
| Ollama | 11434 | LLM REST API |

---

## Project structure

```
ai-frontdesk/
├── backend/
│   ├── app/
│   │   ├── agents/         # LangGraph multi-agent system
│   │   ├── api/            # FastAPI routers (REST + LiveKit)
│   │   ├── memory/         # Postgres, Chroma, Neo4j stores
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── services/       # LLM + emotion service
│   │   ├── utils/          # GPU lock, audio utils, logger
│   │   ├── voice/          # VAD, STT, TTS, barge-in, turn detector
│   │   └── ws/             # WebSocket handlers (call + dashboard)
│   ├── alembic/            # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js App Router pages
│   ├── components/         # React components
│   └── lib/                # API client, auth context, hooks, types
├── docs/
│   ├── architecture.md
│   ├── voice-pipeline.md
│   ├── agents.md
│   ├── memory-system.md
│   ├── api-reference.md
│   └── deployment.md
├── scripts/
│   ├── healthcheck.sh      # Checks all 8 services + models
│   ├── pull_models.sh      # Downloads Ollama + Piper models
│   └── seed_db.py          # Inserts demo data
├── livekit-config/         # LiveKit server YAML config
├── neo4j-conf/             # Neo4j memory-tuned config
├── piper-models/           # ONNX voice model files (downloaded by pull_models.sh)
├── docker-compose.yml
└── .env.example
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design, data flow, VRAM management |
| [Voice Pipeline](docs/voice-pipeline.md) | VAD → STT → LangGraph → TTS in detail |
| [Multi-Agent System](docs/agents.md) | LangGraph graph, routing logic, agent personas |
| [Memory System](docs/memory-system.md) | Three-layer memory: Postgres + ChromaDB + Neo4j |
| [API Reference](docs/api-reference.md) | All REST endpoints and WebSocket events |
| [Deployment](docs/deployment.md) | Docker, GPU setup, production hardening |

---

## Hardware notes

The system is tuned for a **GTX 1050 Ti (4 GB VRAM)**:

| Component | VRAM usage | Notes |
|-----------|-----------|-------|
| Faster-Whisper `small` | ~500 MB | STT |
| Qwen3:4b Q4 | ~2.3 GB | LLM (emotion + routing + agent) |
| Piper TTS | 0 MB | Runs on CPU |

A Redis-based GPU lock (`SET NX` with 30 s TTL) serialises all CUDA operations so the two models never compete. On GPUs with ≥ 8 GB VRAM you can remove the lock and run them concurrently, reducing turn-around from ~2–3 s to ~1 s.
