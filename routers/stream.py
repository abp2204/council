from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from stream_queue import consume

router = APIRouter(tags=["stream"])


@router.get("/sessions/{session_id}/stream")
async def stream_response(session_id: str):
    text = consume(session_id)
    if text is None:
        raise HTTPException(
            404,
            f"No pending response for session {session_id!r}. "
            "Call POST /sessions/{session_id}/moves first.",
        )

    async def token_generator():
        for word in text.split():
            yield {"data": word}
            await asyncio.sleep(0.03)
        yield {"data": "[DONE]"}

    return EventSourceResponse(token_generator())
