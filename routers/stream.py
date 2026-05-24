from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from stream_queue import consume_tokens

router = APIRouter(tags=["stream"])


@router.get("/sessions/{session_id}/stream")
async def stream_response(session_id: str):
    tokens = consume_tokens(session_id)
    if tokens is None:
        raise HTTPException(
            404,
            f"No pending response for session {session_id!r}. "
            "Call POST /sessions/{session_id}/moves first.",
        )

    async def token_generator():
        for token in tokens:
            yield {"data": token}
        yield {"data": "[DONE]"}

    return EventSourceResponse(token_generator())
