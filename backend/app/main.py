from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.memory import chroma_store, neo4j_store
from app.utils.logger import configure_logging

configure_logging()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    log.info("startup", ollama_model=cfg.ollama_model)

    # Preload Whisper model into VRAM (avoids cold-start on first call)
    try:
        from app.voice.stt import load_model
        load_model()
    except Exception as e:
        log.warning("whisper.preload_failed", error=str(e))

    # Preload Piper voice model into memory
    try:
        from app.voice.tts import preload
        await preload(cfg.piper_model_path)
    except Exception as e:
        log.warning("piper.preload_failed", error=str(e))

    # Initialise ChromaDB collections (idempotent)
    try:
        await chroma_store.ensure_collections()
        log.info("chroma.ready")
    except Exception as e:
        log.warning("chroma.unavailable", error=str(e))

    # Initialise Neo4j constraints (idempotent)
    try:
        await neo4j_store.init_graph()
        log.info("neo4j.ready")
    except Exception as e:
        log.warning("neo4j.unavailable", error=str(e))

    yield

    # Teardown
    await neo4j_store.close()
    log.info("shutdown")


def create_app() -> FastAPI:
    cfg = get_settings()

    app = FastAPI(
        title="AI FrontDesk API",
        version="0.1.0",
        description="Autonomous front-office operating system with voice AI, memory, and multi-agent routing.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── LiveKit API + WebSocket routers (Phase 3) ─────────────────────────────
    from app.api.livekit_token import router as lk_token_router
    from app.api.livekit_webhook import router as lk_webhook_router
    from app.ws.call_socket import router as call_ws_router
    from app.ws.dashboard_socket import router as dash_ws_router

    app.include_router(lk_token_router, prefix="/api/livekit", tags=["livekit"])
    app.include_router(lk_webhook_router, prefix="/api/livekit", tags=["livekit"])
    app.include_router(call_ws_router, tags=["websocket"])
    app.include_router(dash_ws_router, tags=["websocket"])

    # ── REST API routers (Phase 4) ────────────────────────────────────────────
    from app.api.routes.auth import router as auth_router
    from app.api.routes.calls import router as calls_router
    from app.api.routes.customers import router as customers_router
    from app.api.routes.appointments import router as appointments_router
    from app.api.routes.tickets import router as tickets_router
    from app.api.routes.analytics import router as analytics_router

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    app.include_router(calls_router, prefix="/api/calls", tags=["calls"])
    app.include_router(customers_router, prefix="/api/customers", tags=["customers"])
    app.include_router(appointments_router, prefix="/api/appointments", tags=["appointments"])
    app.include_router(tickets_router, prefix="/api/tickets", tags=["tickets"])
    app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "model": cfg.ollama_model}

    return app


app = create_app()
