from __future__ import annotations

from dataclasses import dataclass

import session_store
from dependencies import engine_dep
from fastapi import APIRouter, Depends, HTTPException
from session_engine import InvalidStateError, SessionEngine

router = APIRouter(tags=["sessions"])


@dataclass
class _SaveAdapter:
    case_id: str
    session_id: str
    turns: list
    score: dict


@router.post("/sessions", status_code=201)
def create_session(
    body: dict,
    engine: SessionEngine = Depends(engine_dep),
) -> dict:
    case_id = body.get("case_id", "")
    if not case_id:
        raise HTTPException(400, "case_id is required")
    # KeyError (unknown case) and DraftCaseError (draft) are caught by app exception handlers
    session_id = engine.create_session(case_id)
    opening = engine._sessions[session_id].turns[0]["text"]
    return {"session_id": session_id, "state": "IN_SESSION", "opening": opening}


@router.post("/sessions/{session_id}/evaluate")
def evaluate_session(
    session_id: str,
    engine: SessionEngine = Depends(engine_dep),
) -> dict:
    # KeyError and InvalidStateError are caught by app exception handlers
    score = engine.evaluate(session_id)

    s = engine._sessions[session_id]
    key_moments = [
        {"turn": km.turn, "label": km.label, "user_text": km.user_text, "commentary": km.commentary}
        for km in score.key_moments
    ]
    adapter = _SaveAdapter(
        case_id=s.case_id,
        session_id=session_id,
        turns=s.turns,
        score={
            "legal_soundness": score.legal_soundness,
            "strategic_effectiveness": score.strategic_effectiveness,
            "creativity": score.creativity,
            "key_moments": key_moments,
        },
    )
    session_store.save_session(adapter)

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
    # KeyError is caught by app exception handler → 404
    case_id = engine._sessions[session_id].case_id
    records = session_store.load_sessions(case_id)
    return [
        {
            "session_id": r["session_id"],
            "timestamp": r["timestamp"],
            "score": r["score"],
        }
        for r in records
    ]
