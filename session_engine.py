"""
COUNCIL — Session Engine (Issue #15)

Production-ready state machine extracted from the prototype REPL.
All external dependencies (OpposingRole, Evaluator) are injected via
constructor so callers can swap in mocks without any API keys.

Public API:
    engine = SessionEngine(opposing_role_factory=..., evaluator=...)
    session_id = engine.create_session(case_id)
    result     = engine.submit_move(session_id, text)   -> MoveResult
    score      = engine.evaluate(session_id)            -> Score
    moment     = engine.review(session_id, moment_index) -> KeyMoment
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from case_library import load_case
from deviation_detector import DeviationDetector

logger = logging.getLogger(__name__)


# ── State Machine ─────────────────────────────────────────────────────────────

class State(Enum):
    CASE_SELECT  = auto()
    IN_SESSION   = auto()
    SESSION_END  = auto()
    EVALUATING   = auto()
    SCORED       = auto()
    REVIEW       = auto()


class InvalidStateError(Exception):
    pass


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class KeyMoment:
    turn: int
    label: str   # "best_move" | "worst_move" | "deviation_point"
    user_text: str
    commentary: str


@dataclass
class Score:
    legal_soundness: int
    strategic_effectiveness: int
    creativity: int
    key_moments: list[KeyMoment] = field(default_factory=list)


@dataclass
class MoveResult:
    response: str
    closes: bool
    deviation: bool


# ── Internal session state ────────────────────────────────────────────────────

@dataclass
class _SessionState:
    state: State = State.IN_SESSION
    case_id: str = ""
    turns: list[dict] = field(default_factory=list)
    deviation_count: int = 0
    score: Score | None = None
    case: dict = field(default_factory=dict)
    opposing_role: object = field(default=None, repr=False)


# ── Mock stubs (injected for tests) ──────────────────────────────────────────

class MockOpposingRole:
    """
    Offline opponent for tests — no API key required.

    Cycles through mock_probes in round-robin order and closes once all
    probes have been delivered at least once and the caller has submitted
    at least 3 user turns. Instance is per-session; do not share across sessions.
    """

    def __init__(self, mock_probes: list[str], mock_close: str) -> None:
        if not mock_probes:
            raise ValueError("mock_probes must be a non-empty list")
        self._probes = mock_probes
        self._close = mock_close
        self._probe_index = 0
        self._probes_completed = False

    def respond(self, user_text: str, turns: list[dict]) -> dict:
        user_turns = [t for t in turns if t.get("role") == "user"]
        n = len(user_turns)

        if not self._probes_completed and self._probe_index >= len(self._probes):
            self._probes_completed = True

        if self._probes_completed and n >= 3:
            return {"response": self._close, "closes": True}

        response = self._probes[self._probe_index % len(self._probes)]
        self._probe_index += 1

        if self._probe_index >= len(self._probes):
            self._probes_completed = True

        closes = self._probes_completed and n >= 3
        return {"response": response, "closes": closes}


class MockEvaluator:
    """
    Offline evaluator for tests — returns fixed scores with key moments
    derived from the actual session turns.
    """

    def evaluate(self, session_state: _SessionState) -> Score:
        user_turns = [(i, t) for i, t in enumerate(session_state.turns) if t["role"] == "user"]
        moments: list[KeyMoment] = []

        if user_turns:
            best_idx, best_turn = user_turns[0]
            moments.append(KeyMoment(
                turn=best_idx + 1,
                label="best_move",
                user_text=best_turn["text"],
                commentary="Strong opening framing.",
            ))

        deviation_turns = [(i, t) for i, t in enumerate(session_state.turns)
                           if t["role"] == "user" and t.get("deviation")]
        if deviation_turns:
            worst_idx, worst_turn = deviation_turns[-1]
            moments.append(KeyMoment(
                turn=worst_idx + 1,
                label="deviation_point",
                user_text=worst_turn["text"],
                commentary="This diverged from the historical record.",
            ))

        if len(user_turns) >= 2:
            last_idx, last_turn = user_turns[-1]
            moments.append(KeyMoment(
                turn=last_idx + 1,
                label="worst_move",
                user_text=last_turn["text"],
                commentary="Closing without addressing the DC schools counterargument.",
            ))

        return Score(
            legal_soundness=75,
            strategic_effectiveness=70,
            creativity=65,
            key_moments=moments,
        )


# ── Session Engine ────────────────────────────────────────────────────────────

class SessionEngine:
    """
    Owns the session lifecycle: create → move loop → evaluate → review.

    opposing_role_factory receives the loaded case dict and returns a fresh
    role instance per session — this prevents probe state from leaking across
    sessions. evaluator is shared (stateless).
    """

    def __init__(
        self,
        opposing_role_factory: Callable[[dict], object],
        evaluator: object,
    ) -> None:
        if opposing_role_factory is None:
            raise ValueError("opposing_role_factory is required")
        if evaluator is None:
            raise ValueError("evaluator is required")
        self._opposing_role_factory = opposing_role_factory
        self._evaluator = evaluator
        self._sessions: dict[str, _SessionState] = {}
        self._detector = DeviationDetector()

    def create_session(self, case_id: str) -> str:
        """
        Load case, build initial state, get opening probe.

        Session is only inserted into _sessions after the opening probe
        succeeds so a failed call leaves no dangling state.
        """
        case = load_case(case_id)
        opposing_role = self._opposing_role_factory(case)

        first_response = opposing_role.respond("", [])

        session_id = str(uuid.uuid4())
        s = _SessionState(
            state=State.IN_SESSION,
            case_id=case_id,
            case=case,
        )
        s.turns.append({"role": "opponent", "text": first_response["response"]})
        s.opposing_role = opposing_role
        self._sessions[session_id] = s

        return session_id

    def submit_move(self, session_id: str, text: str) -> MoveResult:
        s = self._get_session(session_id)
        if s.state != State.IN_SESSION:
            raise InvalidStateError(
                f"submit_move requires state IN_SESSION, but session is {s.state.name}"
            )

        turn_index = len([t for t in s.turns if t["role"] == "user"])
        deviation, sim_score = self._detector.detect(text, turn_index, s.case.get("historical_record", []))
        logger.debug("submit_move turn=%d sim_score=%.3f deviation=%s", turn_index, sim_score, deviation)
        if deviation:
            s.deviation_count += 1

        s.turns.append({"role": "user", "text": text, "deviation": deviation})

        opp_result = s.opposing_role.respond(text, s.turns)
        s.turns.append({"role": "opponent", "text": opp_result["response"]})

        if opp_result["closes"]:
            s.state = State.SESSION_END

        return MoveResult(
            response=opp_result["response"],
            closes=opp_result["closes"],
            deviation=deviation,
        )

    def evaluate(self, session_id: str) -> Score:
        s = self._get_session(session_id)
        if s.state != State.SESSION_END:
            raise InvalidStateError(
                f"evaluate requires state SESSION_END, but session is {s.state.name}"
            )

        s.state = State.EVALUATING
        try:
            score = self._evaluator.evaluate(s)
        except Exception:
            s.state = State.SESSION_END
            raise
        s.score = score
        s.state = State.SCORED
        return score

    def review(self, session_id: str, moment_index: int) -> KeyMoment:
        s = self._get_session(session_id)
        if s.state not in (State.SCORED, State.REVIEW):
            raise InvalidStateError(
                f"review requires state SCORED or REVIEW, but session is {s.state.name}"
            )
        if s.score is None:
            raise InvalidStateError("No score available — call evaluate() first")

        moments = s.score.key_moments
        if not moments:
            raise IndexError("no key moments available for this session")
        if moment_index < 0 or moment_index >= len(moments):
            raise IndexError(
                f"moment_index {moment_index} out of range (0–{len(moments) - 1})"
            )

        s.state = State.REVIEW
        return moments[moment_index]

    def _get_session(self, session_id: str) -> _SessionState:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError(f"No session found for ID {session_id!r}")
        return s
