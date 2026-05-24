from __future__ import annotations

from dependencies import engine_dep
from fastapi import APIRouter, Depends
from session_engine import SessionEngine

router = APIRouter(tags=["review"])


@router.get("/sessions/{session_id}/review/{moment_index}")
def get_review(
    session_id: str,
    moment_index: int,
    engine: SessionEngine = Depends(engine_dep),
) -> dict:
    # KeyError → 404, IndexError → 404, InvalidStateError → 409 via app exception handlers
    moment = engine.review(session_id, moment_index)
    return {
        "turn": moment.turn,
        "label": moment.label,
        "user_text": moment.user_text,
        "commentary": moment.commentary,
    }
