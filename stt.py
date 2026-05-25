"""
COUNCIL — STT Layer

Voice-to-text transcription using faster-whisper (local inference).
Model runs on CPU by default; set WHISPER_DEVICE=cuda for GPU acceleration.
"""

import io
import wave

try:
    import numpy as np
    import sounddevice as sd
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

SAMPLE_RATE = 16_000
CHANNELS = 1

_model = None


def _get_model():
    global _model
    if _model is None:
        import os
        from faster_whisper import WhisperModel

        model_size = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
        device = os.environ.get("WHISPER_DEVICE", "cpu")
        compute_type = "float16" if device == "cuda" else "int8"
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Record from the microphone until the user presses Enter. Returns WAV bytes."""
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
        input()

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
    """Transcribe audio bytes via faster-whisper (local). Returns plain text."""
    if not audio_bytes:
        return ""

    import io as _io
    model = _get_model()
    audio_file = _io.BytesIO(audio_bytes)
    segments, _ = model.transcribe(audio_file, beam_size=5)
    return " ".join(seg.text for seg in segments).strip()


def record_and_transcribe() -> str:
    """Full voice input pipeline: record → transcribe. Returns plain text."""
    audio_bytes = record_until_enter()
    if not audio_bytes:
        return ""
    print("  [ Transcribing… ]", flush=True)
    return transcribe(audio_bytes)
