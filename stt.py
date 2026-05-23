"""
COUNCIL — STT Layer (Issue #7)

Voice-to-text transcription as the primary Move input modality.
Uses Groq Whisper for fast transcription — target: <1s per turn.

Primary input path (IN_SESSION):
    1. User presses ENTER → recording starts
    2. User presses ENTER again → recording stops, transcription begins
    3. Plain text flows into the Move pipeline unchanged

Text fallback: "> <text>" syntax in the REPL (always available).
"""

import io
import os
import wave

try:
    import numpy as np
    import sounddevice as sd
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

from groq import Groq

SAMPLE_RATE = 16_000
CHANNELS = 1
_WHISPER_MODEL = "whisper-large-v3-turbo"

_client: "Groq | None" = None


def _get_client() -> "Groq":
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set — cannot transcribe. "
                "Use '> <text>' to type your argument instead."
            )
        _client = Groq(api_key=api_key)
    return _client


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Record from the microphone until the user presses Enter.

    Returns WAV bytes (16-bit mono, 16 kHz) ready for Whisper transcription.
    Raises RuntimeError if sounddevice/numpy are not installed.
    """
    if not VOICE_AVAILABLE:
        raise RuntimeError(
            "sounddevice / numpy not installed. "
            "Run: pip install sounddevice numpy"
        )

    print("  [ Recording… press ENTER to stop ]", flush=True)
    frames: list = []

    def _callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(
        samplerate=sample_rate, channels=CHANNELS, dtype="int16", callback=_callback
    ):
        input()  # blocks main thread; InputStream callback runs in C thread

    if not frames:
        return b""

    audio = np.concatenate(frames, axis=0)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # int16 = 2 bytes/sample
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe WAV bytes via Groq Whisper. Returns plain text."""
    if not audio_bytes:
        return ""

    client = _get_client()
    buf = io.BytesIO(audio_bytes)
    buf.name = "move.wav"  # Groq SDK reads .name for MIME sniffing

    result = client.audio.transcriptions.create(
        file=buf,
        model=_WHISPER_MODEL,
    )
    return result.text.strip()


def record_and_transcribe() -> str:
    """Full voice input pipeline: record → transcribe. Returns plain text."""
    audio_bytes = record_until_enter()
    if not audio_bytes:
        return ""
    print("  [ Transcribing… ]", flush=True)
    return transcribe(audio_bytes)
