from __future__ import annotations

from collections.abc import Callable

from session_engine import SessionEngine

_engine: SessionEngine | None = None
_transcribe_fn: Callable[[bytes], str] | None = None


def set_engine(engine: SessionEngine) -> None:
    global _engine
    _engine = engine


def get_engine() -> SessionEngine:
    if _engine is None:
        raise RuntimeError("SessionEngine has not been initialised. Call set_engine() first.")
    return _engine


def set_transcriber(fn: Callable[[bytes], str]) -> None:
    global _transcribe_fn
    _transcribe_fn = fn


def get_transcriber() -> Callable[[bytes], str]:
    if _transcribe_fn is None:
        from stt import transcribe
        return transcribe
    return _transcribe_fn


def engine_dep() -> SessionEngine:
    return get_engine()


def transcriber_dep() -> Callable[[bytes], str]:
    return get_transcriber()
