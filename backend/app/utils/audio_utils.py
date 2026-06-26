"""PCM / WAV conversion and audio helper utilities."""
import io
import struct
import wave

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit signed
CHANNELS = 1      # mono


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> bytes:
    """Wrap raw int16 mono PCM in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(CHANNELS)
        f.setsampwidth(SAMPLE_WIDTH)
        f.setframerate(sample_rate)
        f.writeframes(pcm_bytes)
    return buf.getvalue()


def wav_to_pcm(wav_bytes: bytes) -> tuple[bytes, int]:
    """Extract raw PCM and sample rate from WAV bytes."""
    with wave.open(io.BytesIO(wav_bytes)) as f:
        return f.readframes(f.getnframes()), f.getframerate()


def chunk_audio(pcm_bytes: bytes, chunk_ms: int = 20, sample_rate: int = SAMPLE_RATE) -> list[bytes]:
    """Split PCM into fixed-size chunks suitable for streaming or VAD."""
    chunk_size = int(sample_rate * chunk_ms / 1000) * SAMPLE_WIDTH
    return [pcm_bytes[i : i + chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]


def calculate_rms(pcm_bytes: bytes) -> float:
    """RMS energy of a PCM frame, normalised to 0.0–1.0."""
    n = len(pcm_bytes) // SAMPLE_WIDTH
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes[: n * SAMPLE_WIDTH])
    rms = (sum(s * s for s in samples) / n) ** 0.5
    return rms / 32768.0


def duration_secs(pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> float:
    """Duration in seconds of a raw PCM buffer."""
    return len(pcm_bytes) / (sample_rate * SAMPLE_WIDTH)
