from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from session_engine import InvalidStateError, SessionEngine

router = APIRouter(tags=["moves"])


def _get_engine() -> SessionEngine:
    from dependencies import get_engine
    return get_engine()


def _get_transcriber():
    from dependencies import get_transcriber
    return get_transcriber()


@router.post("/sessions/{session_id}/moves")
async def submit_move(session_id: str, request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    transcription: str | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("audio")
        if audio_file is None:
            raise HTTPException(400, "Multipart request missing 'audio' field")
        audio_bytes = await audio_file.read()
        text = _get_transcriber()(audio_bytes)
        transcription = text
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "Request body must be JSON with a 'text' field or multipart with an 'audio' field")
        text = body.get("text", "").strip()
        if not text:
            raise HTTPException(400, "JSON body missing 'text' field")

    engine = _get_engine()
    # KeyError → 404, InvalidStateError → 409 handled by app exception handlers
    result = engine.submit_move(session_id, text)

    from stream_queue import enqueue
    enqueue(session_id, result.response)

    response: dict = {
        "response": result.response,
        "closes": result.closes,
        "deviation": result.deviation,
        "stream_url": f"/sessions/{session_id}/stream",
    }
    if transcription is not None:
        response["transcription"] = transcription
    return response
