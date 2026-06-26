# Deployment

## Local development (recommended for hackathon)

The fastest workflow: Docker for infrastructure, local processes for the backend and frontend.

### Step 1 — Prerequisites

- Docker Desktop ≥ 24 with Compose v2
- NVIDIA Container Toolkit (for Ollama GPU passthrough)
- Python 3.11
- Node.js ≥ 20

**Install NVIDIA Container Toolkit on Ubuntu/WSL2:**
```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Verify GPU access inside Docker:**
```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

### Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` — minimum changes:
```
POSTGRES_PASSWORD=your_strong_password
REDIS_PASSWORD=your_strong_password
NEO4J_PASSWORD=your_strong_password
LIVEKIT_API_SECRET=your_secret_must_be_at_least_32_characters_long
SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
STAFF_PASSWORD=your_dashboard_password
```

### Step 3 — Start infrastructure

```bash
docker compose up -d
bash scripts/healthcheck.sh   # wait until all services pass
bash scripts/pull_models.sh   # one-time: downloads Qwen3:4b + Piper voice
```

### Step 4 — Start backend

Migrations run automatically when the Docker container starts.

```bash
# Option A — Docker (recommended):
docker compose --profile app up -d backend

# Option B — local Python:
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://argent:<PASSWORD>@localhost:5433/argent
export REDIS_URL=redis://:<REDIS_PASSWORD>@localhost:6380/0
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 5 — Start frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Full Docker deployment

Run everything in containers.

```bash
# Build and start all services including backend + frontend
docker compose --profile app up -d --build

# Check logs
docker compose logs -f backend
docker compose logs -f frontend
```

The `backend` and `frontend` services use the `app` profile so they don't start with bare `docker compose up -d` (which only starts infrastructure).

---

## GPU setup details

### Verifying GPU passthrough

```bash
# Should show your GPU
docker compose exec ollama nvidia-smi

# Should show CUDA-capable device
docker compose exec backend python -c "import torch; print(torch.cuda.get_device_name(0))"
```

### Memory tuning for 4 GB VRAM

The system is pre-tuned for GTX 1050 Ti. If you change models:

| Model | VRAM | Can coexist with Whisper small? |
|-------|------|--------------------------------|
| qwen3:1.7b Q4 | ~1 GB | Yes (parallel possible) |
| qwen3:4b Q4 | ~2.3 GB | Yes (sequential, via GPU lock) |
| qwen3:8b Q4 | ~4.5 GB | No (needs ≥ 8 GB card) |
| llama3.2:3b Q4 | ~2 GB | Yes |
| mistral:7b Q4 | ~4 GB | No (too tight) |

Change the model by editing `OLLAMA_MODEL` in `.env` and re-running `scripts/pull_models.sh`.

### WSL2 GPU note

On Windows with WSL2, Docker Desktop uses the WSL2 backend. GPU passthrough works out of the box once the NVIDIA driver is installed on the Windows host (≥ 525.x). No separate NVIDIA Container Toolkit installation is needed on the WSL2 side — Docker Desktop handles it.

---

## Port reference

| Service | Port(s) | Exposure |
|---------|---------|----------|
| Frontend | 3000 | Browser |
| Backend API | 8000 | Browser + internal |
| LiveKit HTTP | 7880 | Browser (WebSocket) |
| LiveKit RTC TCP | 7881 | Browser (WebRTC) |
| LiveKit RTC UDP | 50200–50220 | Browser (WebRTC) |
| PostgreSQL | 5433 | Host port (container: 5432) |
| Redis | 6380 | Host port (container: 6379) |
| ChromaDB | 8002 | Host port (container: 8000) |
| Neo4j Browser | 7475 | Admin UI (`neo4j` / your password) |
| Neo4j Bolt | 7688 | Host port (container: 7687) |
| Ollama | 11434 | LLM REST API |

For a production deployment, only ports 3000, 7880, 7881, and 50200–50220 need to be publicly accessible.

---

## Production hardening checklist

The hackathon build is intentionally minimal. Before exposing to the internet:

- [ ] Replace `STAFF_USERNAME/STAFF_PASSWORD` with a proper user table and bcrypt hashing
- [ ] Add JWT auth to the WebSocket endpoints (`/ws/calls/*`, `/ws/dashboard`)
- [ ] Enable LiveKit TURN server for clients behind symmetric NAT
- [ ] Move secrets to a vault (Doppler, AWS Secrets Manager, etc.) — never commit `.env`
- [ ] Add rate limiting to the auth endpoint (e.g., slowapi)
- [ ] Set `CORS` origins to your actual domain instead of `localhost`
- [ ] Enable PostgreSQL SSL and restrict network access
- [ ] Back up ChromaDB and Neo4j volumes on a schedule
- [ ] Add Prometheus metrics and a Grafana dashboard
- [ ] Replace Piper with a commercial TTS API (ElevenLabs, Azure) for better voice quality
- [ ] Add Whisper large-v3 for higher STT accuracy (needs ≥ 6 GB VRAM)

---

## Resetting the database

```bash
# Drop and recreate (destroys all data)
docker compose exec postgres psql -U argent -c "DROP DATABASE argent;"
docker compose exec postgres psql -U argent -c "CREATE DATABASE argent;"
# Restart the backend so it re-runs migrations automatically:
docker compose --profile app restart backend
python scripts/seed_db.py
```

## Useful commands

```bash
# Tail backend logs
docker compose logs -f backend

# Open a Postgres shell
docker compose exec postgres psql -U argent -d argent

# Open a Redis CLI
docker compose exec redis redis-cli -a <REDIS_PASSWORD>

# Browse Neo4j (Cypher workbench)
open http://localhost:7475
# Login: neo4j / <NEO4J_PASSWORD>

# Check which process holds the GPU lock
docker compose exec redis redis-cli -a <REDIS_PASSWORD> GET gpu:lock

# List Ollama models
docker compose exec ollama ollama list

# Re-pull a model
docker compose exec ollama ollama pull qwen3:4b
```
