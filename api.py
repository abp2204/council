from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from case_library import DraftCaseError
from dependencies import set_engine, set_transcriber
from session_engine import (
    InvalidStateError,
    MockEvaluator,
    MockOpposingRole,
    Score,
    KeyMoment,
    SessionEngine,
)


# ── Adapters ──────────────────────────────────────────────────────────────────


class _EvaluatorAdapter:
    """Bridges EvaluatorRole (takes transcript list) to the SessionEngine interface (passes _SessionState)."""

    def __init__(self, real_evaluator: object) -> None:
        self._real = real_evaluator

    def evaluate(self, session_state: object) -> Score:
        transcript = [
            {"speaker": t["role"], "text": t["text"]}
            for t in session_state.turns  # type: ignore[attr-defined]
        ]
        raw = self._real.evaluate(transcript)  # type: ignore[attr-defined]
        # evaluator.KeyMoment uses turn_number; session_engine.KeyMoment uses turn
        moments = [
            KeyMoment(
                turn=km.turn_number,
                label=km.label,
                user_text=km.user_text,
                commentary=km.commentary,
            )
            for km in raw.key_moments
        ]
        return Score(
            legal_soundness=raw.legal_soundness,
            strategic_effectiveness=raw.strategic_effectiveness,
            creativity=raw.creativity,
            key_moments=moments,
        )


@dataclass
class _SaveAdapter:
    """Bridges _SessionState + session_id to session_store.save_session() format."""

    case_id: str
    session_id: str
    turns: list
    score: dict  # pre-serialised dict, not a Score dataclass


# ── Startup ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    testing = os.environ.get("COUNCIL_TESTING") == "1"
    if not testing:
        groq_key = os.environ.get("GROQ_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not groq_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Export it before starting the server."
            )
        if not anthropic_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before starting the server."
            )
        from evaluator import EvaluatorRole
        from opposing_role import OpposingRole

        engine = SessionEngine(
            opposing_role_factory=lambda case: OpposingRole(case["id"]),
            evaluator=_EvaluatorAdapter(EvaluatorRole()),
        )
    else:
        engine = SessionEngine(
            opposing_role_factory=lambda case: MockOpposingRole(
                mock_probes=case["opposing_role"]["mock_probes"],
                mock_close=case["opposing_role"]["mock_close"],
            ),
            evaluator=MockEvaluator(),
        )
        set_transcriber(lambda _audio: "mocked transcription")

    set_engine(engine)
    yield


# ── App ───────────────────────────────────────────────────────────────────────


app = FastAPI(title="COUNCIL API", version="0.1.0", lifespan=lifespan)


# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(KeyError)
async def key_error_handler(request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(IndexError)
async def index_error_handler(request, exc: IndexError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidStateError)
async def invalid_state_handler(request, exc: InvalidStateError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(DraftCaseError)
async def draft_case_handler(request, exc: DraftCaseError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# ── Routers ───────────────────────────────────────────────────────────────────


def _register_routers() -> None:
    try:
        from routers.cases import router as cases_router
        app.include_router(cases_router)
    except ImportError:
        pass
    try:
        from routers.sessions import router as sessions_router
        app.include_router(sessions_router)
    except ImportError:
        pass
    try:
        from routers.moves import router as moves_router
        app.include_router(moves_router)
    except ImportError:
        pass
    try:
        from routers.stream import router as stream_router
        app.include_router(stream_router)
    except ImportError:
        pass
    try:
        from routers.review import router as review_router
        app.include_router(review_router)
    except ImportError:
        pass


_register_routers()
