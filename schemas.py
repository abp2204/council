from __future__ import annotations

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    case_id: str


class SubmitMoveRequest(BaseModel):
    text: str


class CaseSummary(BaseModel):
    id: str
    title: str
    proceeding_type: str
    practice_area: str
    user_role: str


class SessionCreated(BaseModel):
    session_id: str
    state: str
    opening: str


class MoveResponse(BaseModel):
    response: str
    closes: bool
    deviation: bool
    stream_url: str
    transcription: str | None = None


class KeyMomentResponse(BaseModel):
    turn: int
    label: str
    user_text: str
    commentary: str


class ScoreResponse(BaseModel):
    legal_soundness: int
    strategic_effectiveness: int
    creativity: int
    key_moments: list[KeyMomentResponse]


class SessionHistoryRecord(BaseModel):
    session_id: str
    timestamp: str
    score: ScoreResponse
