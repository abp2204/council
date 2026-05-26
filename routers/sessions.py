from __future__ import annotations

import session_store
from dependencies import engine_dep
from fastapi import APIRouter, Depends, HTTPException
from session_engine import SessionEngine
from session_store import PersistedSession

router = APIRouter(tags=["sessions"])


@router.post("/sessions", status_code=201)
def create_session(
    body: dict,
    engine: SessionEngine = Depends(engine_dep),
) -> dict:
    case_id = body.get("case_id", "")
    if not case_id:
        raise HTTPException(400, "case_id is required")
    session_id = engine.create_session(case_id)
    opening = engine.get_opening(session_id)
    return {"session_id": session_id, "state": "IN_SESSION", "opening": opening}


@router.post("/sessions/{session_id}/evaluate")
def evaluate_session(
    session_id: str,
    engine: SessionEngine = Depends(engine_dep),
) -> dict:
    score = engine.evaluate(session_id)

    key_moments = [
        {"turn": km.turn, "label": km.label, "user_text": km.user_text, "commentary": km.commentary}
        for km in score.key_moments
    ]

    persisted = PersistedSession(
        case_id=engine.get_case_id(session_id),
        session_id=session_id,
        turns=engine.get_turns(session_id),
        score=score,
    )
    session_store.save_session(persisted)

    return {
        "legal_soundness": score.legal_soundness,
        "strategic_effectiveness": score.strategic_effectiveness,
        "creativity": score.creativity,
        "key_moments": key_moments,
    }


@router.get("/sessions/{session_id}/history")
def session_history(
    session_id: str,
    engine: SessionEngine = Depends(engine_dep),
) -> list[dict]:
    case_id = engine.get_case_id(session_id)
    records = session_store.load_sessions(case_id)
    return [
        {
            "session_id": r.session_id,
            "timestamp": r.timestamp,
            "score": session_store._score_to_dict(r.score) if r.score is not None else None,
        }
        for r in records
    ]
