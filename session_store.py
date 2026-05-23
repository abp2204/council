"""
COUNCIL — Session Persistence (Issue #6)

Writes completed Sessions (state=SCORED) to disk as JSON.
One file per session under sessions/<case_id>/<timestamp>.json.
Human-readable format; no running server required.

Public API:
    save_session(session_state) -> Path
    load_sessions(case_id) -> list[dict]
    format_history_summary(case_id) -> str | None
"""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent / "sessions"


def save_session(s) -> Path:
    """
    Persist a SCORED SessionState to disk.

    Returns the path of the written file.
    """
    SESSIONS_DIR.mkdir(exist_ok=True)
    case_dir = SESSIONS_DIR / s.case_id
    case_dir.mkdir(exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = case_dir / f"{ts}.json"

    key_moments = [
        {
            "turn": m.turn,
            "label": m.label,
            "user_text": m.user_text,
            "commentary": m.commentary,
        }
        for m in s.score.get("key_moments", [])
    ]

    record = {
        "case_id": s.case_id,
        "session_id": s.session_id,
        "timestamp": ts,
        "turns": s.turns,
        "score": {
            "legal_soundness": s.score["legal_soundness"],
            "strategic_effectiveness": s.score["strategic_effectiveness"],
            "creativity": s.score["creativity"],
            "key_moments": key_moments,
        },
    }

    with open(path, "w") as f:
        json.dump(record, f, indent=2)

    return path


def load_sessions(case_id: str) -> list[dict]:
    """Return all persisted sessions for a Case, oldest first."""
    case_dir = SESSIONS_DIR / case_id
    if not case_dir.exists():
        return []
    sessions = []
    for path in sorted(case_dir.glob("*.json")):
        with open(path) as f:
            sessions.append(json.load(f))
    return sessions


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
    # Exclude the session just saved (it's the last one); show prior history only.
    prior = sessions[:-1]
    if not prior:
        return None

    scores = [_overall(s["score"]) for s in prior]
    best = max(scores)
    attempts = len(prior)

    # Trend arrow: compare last two prior scores
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
