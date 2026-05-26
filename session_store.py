"""
COUNCIL — Session Persistence (Issue #21)

SQLite-backed session store. Replaces the flat-JSON implementation with a
single database file at sessions/council.db.

Schema is kept Postgres-compatible:
  - TEXT primary keys (no AUTOINCREMENT / SERIAL)
  - JSON columns stored as TEXT blobs

Public API:
    save_session(session: PersistedSession) -> None
    load_sessions(case_id, user_id=None) -> list[PersistedSession]
    format_history_summary(case_id) -> str | None
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from domain import KeyMoment, Score, Turn

SESSIONS_DIR = Path(__file__).parent / "sessions"
_DB_NAME = "council.db"


@dataclass
class PersistedSession:
    session_id: str
    case_id: str
    turns: list[Turn]
    score: Score | None
    user_id: str | None = None
    timestamp: str | None = None

    def format_history_summary(self) -> str | None:
        """
        Return a one-line history block for display after session scoring.
        Returns None if this is the first session on the case.
        """
        sessions = load_sessions(self.case_id)
        prior = sessions[:-1]
        if not prior:
            return None

        scores = [_overall_score(s.score) for s in prior if s.score is not None]
        if not scores:
            return None
        best = max(scores)
        attempts = len(prior)

        if len(scores) >= 2:
            delta = scores[-1] - scores[-2]
            trend = f"+{delta}" if delta > 0 else str(delta)
            trend_str = f"  trend: {trend} from last attempt"
        else:
            trend_str = ""

        return (
            f"  Your history on this case: {attempts} prior attempt{'s' if attempts != 1 else ''}  |  "
            f"best: {best}/100{trend_str}"
        )


def _db_path() -> Path:
    return SESSIONS_DIR / _DB_NAME


def _get_conn() -> sqlite3.Connection:
    SESSIONS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id  TEXT PRIMARY KEY,
            case_id     TEXT NOT NULL,
            user_id     TEXT,
            timestamp   TEXT NOT NULL,
            turns       TEXT NOT NULL,
            score       TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _score_to_dict(score: Score) -> dict:
    return {
        "legal_soundness": score.legal_soundness,
        "strategic_effectiveness": score.strategic_effectiveness,
        "creativity": score.creativity,
        "key_moments": [
            {
                "turn": km.turn,
                "label": km.label,
                "user_text": km.user_text,
                "commentary": km.commentary,
            }
            for km in score.key_moments
        ],
    }


def _score_from_dict(d: dict) -> Score:
    return Score(
        legal_soundness=d["legal_soundness"],
        strategic_effectiveness=d["strategic_effectiveness"],
        creativity=d["creativity"],
        key_moments=[
            KeyMoment(
                turn=km["turn"],
                label=km["label"],
                user_text=km["user_text"],
                commentary=km["commentary"],
            )
            for km in d.get("key_moments", [])
        ],
    )


def _turns_to_list(turns: list[Turn]) -> list[dict]:
    return [{"role": t.role, "text": t.text, "deviation": t.deviation} for t in turns]


def _turns_from_list(data: list[dict]) -> list[Turn]:
    return [Turn(role=t["role"], text=t["text"], deviation=t.get("deviation", False)) for t in data]


def save_session(s: PersistedSession) -> None:
    """Persist a scored session to the SQLite database."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    score_blob = _score_to_dict(s.score) if s.score is not None else {}

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions
                (session_id, case_id, user_id, timestamp, turns, score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                s.session_id,
                s.case_id,
                s.user_id,
                ts,
                json.dumps(_turns_to_list(s.turns)),
                json.dumps(score_blob),
            ),
        )


def load_sessions(case_id: str, user_id: str | None = None) -> list[PersistedSession]:
    """Return all persisted sessions for a Case, oldest first.

    Pass ``user_id`` to filter by user.
    """
    try:
        conn = _get_conn()
    except Exception:
        return []

    with conn:
        if user_id is not None:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE case_id = ? AND user_id = ? ORDER BY timestamp ASC",
                (case_id, user_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE case_id = ? ORDER BY timestamp ASC",
                (case_id,),
            ).fetchall()

    return [
        PersistedSession(
            session_id=row["session_id"],
            case_id=row["case_id"],
            user_id=row["user_id"],
            timestamp=row["timestamp"],
            turns=_turns_from_list(json.loads(row["turns"])),
            score=_score_from_dict(json.loads(row["score"])) if row["score"] and row["score"] != "{}" else None,
        )
        for row in rows
    ]


def _overall_score(score: Score) -> int:
    return (
        score.legal_soundness
        + score.strategic_effectiveness
        + score.creativity
    ) // 3


def format_history_summary(case_id: str) -> str | None:
    """
    Return a one-line history block for display after session scoring.
    Returns None if this is the first session on the case.

    Thin wrapper around PersistedSession.format_history_summary() on the
    most-recently-saved session for the given case.
    """
    sessions = load_sessions(case_id)
    if not sessions:
        return None
    return sessions[-1].format_history_summary()
