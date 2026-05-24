"""
COUNCIL — Session Persistence (Issue #21)

SQLite-backed session store. Replaces the flat-JSON implementation with a
single database file at sessions/council.db.

Schema is kept Postgres-compatible:
  - TEXT primary keys (no AUTOINCREMENT / SERIAL)
  - JSON columns stored as TEXT blobs

Public API (unchanged from flat-JSON version):
    save_session(session_state) -> None
    load_sessions(case_id, user_id=None) -> list[dict]
    format_history_summary(case_id) -> str | None
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent / "sessions"
_DB_NAME = "council.db"


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


def save_session(s) -> None:
    """
    Persist a SCORED session to the SQLite database.

    ``s`` must expose:
        s.case_id    str
        s.session_id str
        s.turns      list[dict]
        s.score      dict  — keys: legal_soundness, strategic_effectiveness,
                             creativity, key_moments (list of plain dicts)
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    key_moments = [
        {
            "turn": m["turn"],
            "label": m["label"],
            "user_text": m["user_text"],
            "commentary": m["commentary"],
        }
        for m in s.score.get("key_moments", [])
    ]

    score_blob = {
        "legal_soundness": s.score["legal_soundness"],
        "strategic_effectiveness": s.score["strategic_effectiveness"],
        "creativity": s.score["creativity"],
        "key_moments": key_moments,
    }

    user_id: str | None = getattr(s, "user_id", None)

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
                user_id,
                ts,
                json.dumps(s.turns),
                json.dumps(score_blob),
            ),
        )


def load_sessions(case_id: str, user_id: str | None = None) -> list[dict]:
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
        {
            "session_id": row["session_id"],
            "case_id": row["case_id"],
            "user_id": row["user_id"],
            "timestamp": row["timestamp"],
            "turns": json.loads(row["turns"]),
            "score": json.loads(row["score"]),
        }
        for row in rows
    ]


def _overall(score: dict) -> int:
    return (
        score["legal_soundness"]
        + score["strategic_effectiveness"]
        + score["creativity"]
    ) // 3


def format_history_summary(case_id: str) -> str | None:
    """
    Return a one-line history block for display after session scoring.
    Returns None if this is the first session on the case.
    """
    sessions = load_sessions(case_id)
    prior = sessions[:-1]
    if not prior:
        return None

    scores = [_overall(s["score"]) for s in prior]
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
