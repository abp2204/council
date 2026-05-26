from __future__ import annotations

from collections.abc import Callable

from dependencies import engine_dep, transcriber_dep
from fastapi import APIRouter, Depends, HTTPException, Request
from session_engine import SessionEngine

router = APIRouter(tags=["moves"])


@router.post("/sessions/{session_id}/moves")
async def submit_move(
    session_id: str,
    request: Request,
    engine: SessionEngine = Depends(engine_dep),
    transcribe: Callable[[bytes], str] = Depends(transcriber_dep),
) -> dict:
    content_type = request.headers.get("content-type", "")
    transcription: str | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        audio_file = form.get("audio")
        if audio_file is None:
            raise HTTPException(400, "Multipart request missing 'audio' field")
        audio_bytes = await audio_file.read()
        text = transcribe(audio_bytes)
        transcription = text
    else:
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(400, "Request body must be JSON with a 'text' field or multipart with an 'audio' field")
        text = body.get("text", "").strip()
        if not text:
            raise HTTPException(400, "JSON body missing 'text' field")

    # KeyError → 404, InvalidStateError → 409 handled by app exception handlers
    deviation = engine.prepare_move(session_id, text)

    response: dict = {
        "deviation": deviation,
        "stream_url": f"/sessions/{session_id}/stream",
    }
    if transcription is not None:
        response["transcription"] = transcription
    return response
