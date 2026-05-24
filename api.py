from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from case_library import DraftCaseError
from dependencies import set_engine, set_transcriber
from session_engine import (
    InvalidStateError,
    MockEvaluator,
    MockOpposingRole,
    SessionEngine,
)


# ── Startup ───────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    testing = os.environ.get("COUNCIL_TESTING") == "1"
    if not testing:
        from evaluator import EvaluatorRole
        from opposing_role import OpposingRole

        engine = SessionEngine(
            opposing_role_factory=lambda case: OpposingRole(case["id"]),
            evaluator=EvaluatorRole(),
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
