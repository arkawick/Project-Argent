# Architecture

## System overview

AI FrontDesk is a real-time voice AI platform. A browser microphone connects to a LiveKit room over WebRTC; a backend agent participant joins the same room, runs the full voice pipeline, and plays the AI response back through the same room.

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser                                                        │
│  ┌─────────┐  WebRTC audio   ┌──────────┐  WebSocket events   │
│  │   Mic   │ ──────────────► │ LiveKit  │ ◄──────────────────  │
│  │Speaker  │ ◄────────────── │  Room    │  transcript/emotion  │
│  └─────────┘                 └────┬─────┘                      │
└────────────────────────────────── │ ──────────────────────────-┘
                                    │ WebRTC (agent participant)
┌───────────────────────────────────▼─────────────────────────────┐
│  Backend (FastAPI + Uvicorn)                                    │
│                                                                 │
│  call_socket.py (WebSocket /ws/calls/{id})                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LiveKit audio frames                                    │   │
│  │       ↓                                                  │   │
│  │  VAD (webrtcvad) ─── speech end? ──► STT (Faster-Whisper│   │
│  │                                           ↓ GPU lock    │   │
│  │                                      LangGraph graph    │   │
│  │                                           ↓             │   │
│  │   [memory_loader → emotion → router → sub-agent → writer│   │
│  │                                           ↓ GPU lock    │   │
│  │                                      Piper TTS (CPU)    │   │
│  │                                           ↓             │   │
│  │                                  LiveKit audio frames   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │Postgres  │  │ChromaDB  │  │  Neo4j   │  │  Redis        │  │
│  │(CRM/data)│  │(semantic)│  │ (graph)  │  │(lock + cache) │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Request lifecycle

### 1. Call start

1. Browser navigates to `/demo`
2. Frontend calls `GET /api/livekit/token?room={callId}` → receives a signed LiveKit JWT
3. Frontend opens `WebSocket /ws/calls/{callId}` → backend agent joins the LiveKit room and publishes a TTS audio track
4. Frontend connects to LiveKit with the user token → browser microphone is published into the room

### 2. Turn processing (per utterance)

```
Browser mic PCM
     │
     ▼ (30 ms frames via LiveKit AudioStream)
 VAD.feed()
     │ SPEECH_END event
     ▼
 transcribe()   ← acquires GPU lock, runs Faster-Whisper, releases lock
     │ text
     ▼
 agent_graph.ainvoke(state)
     │
     ├─ memory_loader_node  ← Postgres CRM + Neo4j graph + Chroma semantics
     ├─ emotion_classifier  ← ollama_json (acquires + releases GPU lock)
     ├─ intent_router       ← ollama_json (acquires + releases GPU lock)
     ├─ [sub-agent]         ← ollama_chat (acquires + releases GPU lock)
     └─ memory_writer       ← writes insight row, Chroma summary, Neo4j edges
     │ AgentState with agent_response
     ▼
 synthesize()   ← Piper TTS on CPU (no GPU lock needed)
     │ WAV bytes
     ▼
 stream 20 ms PCM chunks into LiveKit AudioSource
     │
     ▼
 Browser speaker plays agent voice
```

### 3. Event streaming

At every stage, structured JSON events are pushed to the browser over the call WebSocket:

| Event type | Payload fields |
|------------|----------------|
| `transcript` | speaker, text, emotion, intent |
| `turn_change` | state: listening / processing / speaking |
| `agent_route` | agent, confidence |
| `barge_in` | (none) |

---

## VRAM management

The GTX 1050 Ti has 4 GB VRAM. Two models compete:

| Model | VRAM | When loaded |
|-------|------|-------------|
| Faster-Whisper small | ~500 MB | STT transcription |
| Qwen3:4b Q4 | ~2.3 GB | Emotion, routing, agent response |

A Redis key `gpu:lock` (30 s TTL, SET NX) serialises all GPU operations:

```python
@asynccontextmanager
async def gpu_lock(owner: str):
    while True:
        acquired = await redis.set("gpu:lock", owner, ex=30, nx=True)
        if acquired: break
        await asyncio.sleep(0.05)   # 50 ms poll
    try: yield
    finally: await redis.delete("gpu:lock")
```

Piper TTS runs on CPU and never acquires the lock, so TTS playback begins immediately after the LLM finishes.

---

## Barge-in detection

When the agent is speaking, the user can interrupt (barge-in):

1. TTS playback sets Redis key `call:{id}:tts_playing`
2. Each 20 ms audio chunk checks this key before sending to LiveKit
3. If VAD detects speech while `tts_playing` is set → barge-in event
4. TTS loop exits, VAD resets, turn state returns to LISTENING

---

## Turn-state machine

```
           speech_ended()
LISTENING ──────────────► PROCESSING
    ▲                          │
    │      tts_ended()         │ tts_started()
    └──────────────── SPEAKING ◄┘
         barge_in() ──────────────► LISTENING
```

State is tracked in `TurnDetector` per call; async callbacks push `turn_change` events to the browser.

---

## Database roles

| Database | Role | Tables / Collections |
|----------|------|----------------------|
| PostgreSQL | Source of truth — CRM, calls, tickets, appointments | customers, calls, call_insights, tickets, appointments |
| ChromaDB | Semantic search — call summaries, knowledge base | call_summaries, customer_profiles, knowledge_base |
| Neo4j | Relationship graph — topic co-occurrence, emotion history | Customer, Call, Topic, Emotion nodes + edges |
| Redis | Ephemeral — GPU lock, TTS state, analytics cache | gpu:lock, call:*:tts_playing, analytics:* |

---

## Service dependency graph

```
backend ──► postgres
        ──► redis
        ──► chromadb
        ──► neo4j
        ──► ollama (LLM)
        ──► livekit (WebRTC signalling)

frontend ──► backend (REST + WebSocket)
         ──► livekit (WebRTC media, direct browser connection)
```
