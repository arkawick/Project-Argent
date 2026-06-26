# Voice Pipeline

End-to-end flow for a single conversational turn, from raw microphone audio to agent speech.

---

## 1. Audio ingestion (LiveKit → queue)

The backend agent connects to the LiveKit room as a participant. When the browser joins and publishes its microphone track, LiveKit fires a `track_subscribed` event.

An `AudioStream` object wraps the remote audio track and yields `AudioFrameEvent` objects at the configured sample rate:

```python
stream = rtc.AudioStream(track, sample_rate=16_000, num_channels=1)
async for event in stream:
    pcm = bytes(event.frame.data)   # 16 kHz mono int16 PCM
    audio_queue.put_nowait(pcm)
```

Frames are dropped if the queue is full (1000 frames = ~30 s buffer), trading correctness for latency.

---

## 2. Voice Activity Detection

`VAD` (in `app/voice/vad.py`) wraps Google's `webrtcvad` library. It consumes 30 ms frames and emits two events:

| Event | Meaning |
|-------|---------|
| `SPEECH_START` | First valid speech frame after silence |
| `SPEECH_END` | Silence hangover expired after speech |

Tuning parameters:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Frame size | 30 ms at 16 kHz | Minimum webrtcvad frame size |
| Aggressiveness | 2 | Balanced noise rejection |
| Min speech frames | 4 (120 ms) | Filters click/pop artifacts |
| Silence hangover | 10 frames (300 ms) | Captures sentence-final pauses |

On `SPEECH_END`, the accumulated PCM bytes are returned as a `SpeechSegment`.

---

## 3. STT — Faster-Whisper

`transcribe()` in `app/voice/stt.py`:

```python
async def transcribe(pcm_bytes: bytes, language="en") -> list[TranscriptSegment]:
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    async with gpu_lock("stt"):
        model = load_model()           # singleton, loaded once at startup
        raw_segments, _ = model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,           # Whisper's built-in VAD as a second filter
            word_timestamps=False,
        )
        raw_list = list(raw_segments)  # materialise INSIDE the lock
    return [TranscriptSegment(text=s.text.strip(), start=s.start, end=s.end) for s in raw_list]
```

**Why materialise inside the lock?** Faster-Whisper returns a generator that pulls GPU work lazily. If the generator is consumed outside the lock, another process can claim the GPU mid-transcription.

Model: `faster-whisper small` (~244M parameters, ~500 MB VRAM). For GPUs with ≥ 8 GB VRAM, swap to `medium` or `large-v3` in `config.py`.

---

## 4. LangGraph agent pipeline

After transcription, `agent_graph.ainvoke(state)` runs the full multi-agent pipeline. See [agents.md](agents.md) for the complete graph description.

From the voice pipeline's perspective, the graph is a black box that takes `AgentState` (with `user_input`) and returns an updated state containing `agent_response`.

---

## 5. TTS — Piper

`synthesize()` in `app/voice/tts.py` synthesises the agent's text to speech using Piper's offline neural TTS:

```python
async def synthesize(text: str, model_path: str) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _synthesize_sync, text, model_path)

def _synthesize_sync(text: str, model_path: str) -> bytes:
    voice = PiperVoice.load(model_path)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        voice.synthesize(text, wav)
    return buf.getvalue()
```

`run_in_executor` offloads the blocking C++ call to a thread pool, keeping the FastAPI event loop responsive.

Piper runs on **CPU only** — no GPU lock is needed. This means TTS synthesis can overlap with the next STT call (on a second hypothetical turn) without resource contention.

**Model:** `en_US-lessac-medium` — 22050 Hz, natural-sounding American English, ~60 MB on disk.

---

## 6. Audio playback (LiveKit AudioSource)

The synthesised WAV is converted to raw PCM and streamed back into the LiveKit room through the agent's published audio track:

```python
async def _play_tts(text, source, barge_in, call_id):
    wav_bytes = await synthesize(text, model_path)
    pcm_bytes, sample_rate = wav_to_pcm(wav_bytes)   # strips WAV header

    chunk_samples = sample_rate * 20 // 1000   # 20 ms chunks
    chunk_bytes = chunk_samples * 2            # int16

    await barge_in.set_tts_playing(call_id)

    for i in range(0, len(pcm_bytes), chunk_bytes):
        if not await barge_in.is_tts_playing(call_id):
            break                              # user interrupted

        chunk = pcm_bytes[i : i + chunk_bytes].ljust(chunk_bytes, b"\x00")
        await source.capture_frame(
            rtc.AudioFrame(data=chunk, sample_rate=sample_rate,
                           num_channels=1, samples_per_channel=chunk_samples)
        )

    await barge_in.clear_tts_playing(call_id)
```

Each `capture_frame` call hands 20 ms of audio to the LiveKit SDK, which transmits it to the browser via WebRTC. The browser's `RoomAudioRenderer` component plays it through the speaker.

---

## Latency budget

On a GTX 1050 Ti at ~75% GPU utilisation:

| Stage | Typical time |
|-------|-------------|
| VAD (hangover wait) | 300 ms |
| STT (Whisper small, ~5 s utterance) | 400–700 ms |
| GPU lock contention (worst case) | 0–200 ms |
| Emotion classifier (Qwen3:4b) | 300–600 ms |
| Intent router (Qwen3:4b) | 200–400 ms |
| Sub-agent LLM (Qwen3:4b) | 600–1200 ms |
| Piper TTS synthesis (~20 words) | 150–300 ms |
| **Total (typical)** | **~2–3 s** |

The dominant cost is the sequential GPU operations. To reduce latency: use a faster Ollama model (e.g., `qwen3:1.7b`) or upgrade to a GPU with enough VRAM to run STT and LLM concurrently.
