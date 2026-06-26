"""
Voice call WebSocket handler — the orchestration heart of AI FrontDesk.

Architecture:
  Browser ──WebRTC──► LiveKit room ◄──WebRTC── Backend agent participant
  Browser ──WebSocket── /ws/calls/{call_id} ── receives transcript/emotion events

Audio flow per turn:
  LiveKit audio frames → VAD → [SPEECH_END] → Whisper STT → LangGraph
  → Piper TTS → LiveKit audio frames → browser speaker
  + Real-time events pushed over WebSocket at every step.

The WebSocket carries only signalling (JSON events), never raw audio.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from livekit import rtc

from app.agents.graph import agent_graph
from app.agents.state import AgentState, initial_state
from app.api.livekit_token import generate_agent_token
from app.config import get_settings
from app.dependencies import AsyncSessionLocal
from app.memory import postgres_store
from app.utils.audio_utils import wav_to_pcm
from app.voice.barge_in import BargeInDetector
from app.voice.stt import transcribe, full_text
from app.voice.tts import synthesize
from app.voice.turn_detector import TurnDetector, TurnState
from app.voice.vad import VAD, VADEvent

log = structlog.get_logger()
router = APIRouter()

# Piper lessac-medium outputs at 22050 Hz
PIPER_SAMPLE_RATE = 22_050
TTS_CHUNK_MS = 20  # ms per audio frame pushed to LiveKit


# ── WebSocket entry point ──────────────────────────────────────────────────────

@router.websocket("/ws/calls/{call_id}")
async def call_websocket(websocket: WebSocket, call_id: str) -> None:
    """
    Main voice call endpoint.
    call_id == LiveKit room name == Postgres calls.livekit_room_id
    """
    await websocket.accept()
    log.info("call.connected", call_id=call_id)

    # Queues for cross-task communication
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1000)
    event_queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)
    cancel = asyncio.Event()

    # Shared mutable TTS source — created once, reused per turn
    tts_source: rtc.AudioSource | None = None
    lk_room = rtc.Room()

    # Ensure call record exists in Postgres
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await postgres_store.create_call(session, room_id=call_id)
    except Exception:
        pass  # already exists from webhook or concurrent creation

    tasks = []
    try:
        tts_source, tasks = await _start_tasks(
            call_id, lk_room, audio_queue, event_queue, cancel
        )

        # Read browser commands (end_call) while tasks run
        while not cancel.is_set():
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                data = json.loads(raw)
                if data.get("type") == "end_call":
                    break
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        pass
    finally:
        cancel.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await lk_room.disconnect()
        except Exception:
            pass
        log.info("call.disconnected", call_id=call_id)


# ── Task orchestration ────────────────────────────────────────────────────────

async def _start_tasks(
    call_id: str,
    lk_room: rtc.Room,
    audio_queue: asyncio.Queue,
    event_queue: asyncio.Queue,
    cancel: asyncio.Event,
) -> tuple[rtc.AudioSource, list[asyncio.Task]]:
    cfg = get_settings()

    # Create the agent's outbound audio track once
    tts_source = rtc.AudioSource(sample_rate=PIPER_SAMPLE_RATE, num_channels=1)

    lk_task = asyncio.create_task(
        _run_livekit_agent(call_id, lk_room, tts_source, audio_queue, cancel)
    )
    process_task = asyncio.create_task(
        _audio_processing_loop(call_id, audio_queue, event_queue, lk_room, tts_source, cancel)
    )

    return tts_source, [lk_task, process_task]


# ── LiveKit agent participant ──────────────────────────────────────────────────

async def _run_livekit_agent(
    call_id: str,
    room: rtc.Room,
    tts_source: rtc.AudioSource,
    audio_queue: asyncio.Queue,
    cancel: asyncio.Event,
) -> None:
    cfg = get_settings()
    token = generate_agent_token(call_id)

    @room.on("track_subscribed")
    def on_track(track: rtc.Track, pub: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant) -> None:
        if isinstance(track, rtc.RemoteAudioTrack):
            asyncio.ensure_future(_stream_to_queue(track, audio_queue, cancel))
            log.info("livekit.audio_track_subscribed", participant=participant.identity)

    try:
        await room.connect(cfg.livekit_url, token)
        log.info("livekit.agent_connected", room=call_id)

        # Publish the outbound TTS track
        tts_track = rtc.LocalAudioTrack.create_audio_track("agent-voice", tts_source)
        pub_opts = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
        await room.local_participant.publish_track(tts_track, pub_opts)
        log.info("livekit.tts_track_published")

    except Exception as e:
        log.error("livekit.connect_failed", error=str(e))
        cancel.set()
        return

    while not cancel.is_set():
        await asyncio.sleep(0.5)


async def _stream_to_queue(
    track: rtc.RemoteAudioTrack,
    queue: asyncio.Queue,
    cancel: asyncio.Event,
) -> None:
    """Consume LiveKit audio frames and push PCM bytes into the processing queue."""
    stream = rtc.AudioStream(track, sample_rate=16_000, num_channels=1)
    async for event in stream:
        if cancel.is_set():
            break
        pcm = bytes(event.frame.data)
        try:
            queue.put_nowait(pcm)
        except asyncio.QueueFull:
            pass  # drop oldest — latency over correctness


# ── Main audio processing loop ─────────────────────────────────────────────────

async def _audio_processing_loop(
    call_id: str,
    audio_queue: asyncio.Queue,
    event_queue: asyncio.Queue,
    lk_room: rtc.Room,
    tts_source: rtc.AudioSource,
    cancel: asyncio.Event,
) -> None:
    cfg = get_settings()
    vad = VAD(aggressiveness=2)
    barge_in = BargeInDetector()
    turn = TurnDetector(call_id)
    state: AgentState = initial_state(call_id)

    # Wire turn-state callbacks → WebSocket events
    async def on_listening():
        await event_queue.put({"type": "turn_change", "state": "listening"})

    async def on_processing():
        await event_queue.put({"type": "turn_change", "state": "processing"})

    async def on_speaking():
        await event_queue.put({"type": "turn_change", "state": "speaking"})

    turn.on_listening(on_listening)
    turn.on_processing(on_processing)
    turn.on_speaking(on_speaking)

    # Send greeting on call start
    await event_queue.put({"type": "turn_change", "state": "speaking"})
    greeting = "Hello! Thank you for calling. How can I help you today?"
    await _play_tts(greeting, tts_source, barge_in, call_id)
    await event_queue.put({
        "type": "transcript", "speaker": "agent", "text": greeting,
        "emotion": None, "intent": None,
    })
    await turn.tts_ended()

    while not cancel.is_set():
        try:
            pcm = await asyncio.wait_for(audio_queue.get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue

        event, segment = vad.feed(pcm)

        # Barge-in: user speaks while AI is talking
        if event == VADEvent.SPEECH_START and turn.state == TurnState.SPEAKING:
            is_barge_in = await barge_in.check(call_id, speech_detected=True)
            if is_barge_in:
                await event_queue.put({"type": "barge_in"})
                await turn.barge_in()
                vad.reset()
                continue

        if event != VADEvent.SPEECH_END or segment is None:
            continue

        if turn.state != TurnState.LISTENING:
            continue  # ignore speech while processing or speaking

        # ── End of user utterance — run the full pipeline ──────────────────────
        await turn.speech_ended()

        # 1. Transcribe
        try:
            segments = await transcribe(segment.audio)
            user_text = full_text(segments)
        except Exception as e:
            log.error("stt.error", error=str(e))
            await turn.tts_ended()
            continue

        if not user_text.strip():
            await turn.tts_ended()
            continue

        log.info("turn.user_said", call_id=call_id, text=user_text[:80])
        await event_queue.put({
            "type": "transcript", "speaker": "user", "text": user_text,
            "emotion": None, "intent": None,
        })

        # 2. Run LangGraph
        state = {**state, "user_input": user_text}
        try:
            result = await agent_graph.ainvoke(state)
            state = result
        except Exception as e:
            log.error("graph.error", error=str(e))
            result = {**state, "agent_response": "I'm sorry, could you repeat that?", "active_agent": "unknown"}
            state = result

        agent_text = state["agent_response"]
        log.info("turn.agent_responds", call_id=call_id, agent=state["active_agent"], text=agent_text[:80])

        await event_queue.put({
            "type": "transcript", "speaker": "agent", "text": agent_text,
            "emotion": state.get("user_emotion"), "intent": state.get("user_intent"),
        })
        await event_queue.put({
            "type": "agent_route",
            "agent": state.get("active_agent", "unknown"),
            "confidence": state.get("route_confidence", 0.0),
        })

        # 3. Synthesise & play TTS
        await turn.tts_started()
        await _play_tts(agent_text, tts_source, barge_in, call_id)
        await turn.tts_ended()

        # Persist updated transcript turn
        state["transcript"] = state.get("transcript", []) + [
            {"speaker": "user", "text": user_text, "ts": 0.0,
             "emotion": state.get("user_emotion"), "intent": state.get("user_intent")},
            {"speaker": "agent", "text": agent_text, "ts": 0.0,
             "emotion": None, "intent": None},
        ]


# ── TTS playback via LiveKit AudioSource ──────────────────────────────────────

async def _play_tts(
    text: str,
    source: rtc.AudioSource,
    barge_in: BargeInDetector,
    call_id: str,
) -> None:
    """Synthesise text with Piper and stream PCM frames into the LiveKit AudioSource."""
    cfg = get_settings()
    try:
        wav_bytes = await synthesize(text, cfg.piper_model_path)
    except Exception as e:
        log.error("tts.synthesize_failed", error=str(e))
        return

    if not wav_bytes:
        return

    pcm_bytes, sample_rate = wav_to_pcm(wav_bytes)
    chunk_samples = sample_rate * TTS_CHUNK_MS // 1000
    chunk_bytes = chunk_samples * 2  # int16

    await barge_in.set_tts_playing(call_id)

    i = 0
    while i < len(pcm_bytes):
        # Check for barge-in between chunks
        if await barge_in.is_tts_playing(call_id) is False:
            log.info("tts.cancelled_by_barge_in", call_id=call_id)
            break

        chunk = pcm_bytes[i : i + chunk_bytes]
        if len(chunk) < chunk_bytes:
            chunk += b"\x00" * (chunk_bytes - len(chunk))

        frame = rtc.AudioFrame(
            data=chunk,
            sample_rate=sample_rate,
            num_channels=1,
            samples_per_channel=chunk_samples,
        )
        await source.capture_frame(frame)
        i += chunk_bytes

    await barge_in.clear_tts_playing(call_id)
