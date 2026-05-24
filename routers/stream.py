from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["stream"])


def _get_engine():
    from dependencies import get_engine
    return get_engine()


@router.get("/sessions/{session_id}/stream")
async def stream_response(session_id: str):
    engine = _get_engine()
    try:
        opposing_role = engine.get_opposing_role(session_id)
        turns = engine.get_turns(session_id)
    except KeyError:
        raise HTTPException(404, f"No session found for ID {session_id!r}")

    if opposing_role is None:
        raise HTTPException(
            400,
            "Session has no opposing role — call POST /sessions first.",
        )

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _stream_in_thread() -> None:
        gen = opposing_role.respond_stream(turns)
        accumulated: list[str] = []
        try:
            while True:
                token = next(gen)
                accumulated.append(token)
                loop.call_soon_threadsafe(queue.put_nowait, token)
        except StopIteration as exc:
            closes = exc.value if exc.value is not None else False
            full_text = "".join(accumulated)
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"__done__": True, "closes": closes, "text": full_text},
            )

    loop.run_in_executor(None, _stream_in_thread)

    async def token_generator():
        while True:
            item = await queue.get()
            if isinstance(item, dict) and item.get("__done__"):
                engine.commit_response(session_id, item["text"], item["closes"])
                yield {"data": json.dumps({"type": "done", "closes": item["closes"]})}
                break
            yield {"data": item}

    return EventSourceResponse(token_generator())
