"""
COUNCIL — STT Layer (Issue #7)

Voice-to-text transcription as the primary Move input modality.
Uses local OpenAI Whisper (runs on-device, no API key required).

Primary input path (IN_SESSION):
    1. User presses ENTER → recording starts
    2. User presses ENTER again → recording stops, transcription begins
    3. Plain text flows into the Move pipeline unchanged

Text fallback: "> <text>" syntax in the REPL (always available).
"""

import io
import os
import tempfile
import wave

try:
    import numpy as np
    import sounddevice as sd
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

try:
    import whisper as _whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

SAMPLE_RATE = 16_000
CHANNELS = 1
_WHISPER_MODEL_NAME = "base"

_whisper_model = None


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        if not WHISPER_AVAILABLE:
            raise RuntimeError(
                "openai-whisper not installed. Run: pip install openai-whisper"
            )
        _whisper_model = _whisper.load_model(_WHISPER_MODEL_NAME)
    return _whisper_model


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
    """Transcribe WAV bytes via local Whisper. Returns plain text."""
    if not audio_bytes:
        return ""

    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)


def record_and_transcribe() -> str:
    """Full voice input pipeline: record → transcribe. Returns plain text."""
    audio_bytes = record_until_enter()
    if not audio_bytes:
        return ""
    print("  [ Transcribing… ]", flush=True)
    return transcribe(audio_bytes)
