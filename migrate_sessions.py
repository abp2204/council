"""
migrate_sessions.py — Migrate flat-JSON session files → SQLite (Issue #21)

Reads every  sessions/<case_id>/<timestamp>.json  file and inserts the record
into the new SQLite database.  Safe to run multiple times: existing rows are
left untouched (INSERT OR IGNORE).  Original JSON files are NOT deleted.

Usage:
    python migrate_sessions.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SESSIONS_DIR = Path(__file__).parent / "sessions"
DB_PATH = SESSIONS_DIR / "council.db"


def _ensure_schema(conn: sqlite3.Connection) -> None:
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


def migrate(dry_run: bool = False) -> int:
    """Migrate all flat-JSON files.  Returns the number of records inserted."""
    if not SESSIONS_DIR.exists():
        print("sessions/ directory not found — nothing to migrate.")
        return 0

    json_files = list(SESSIONS_DIR.rglob("*.json"))
    if not json_files:
        print("No JSON session files found.")
        return 0

    if dry_run:
        print(f"[dry-run] Would migrate {len(json_files)} file(s).")
        return 0

    SESSIONS_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    _ensure_schema(conn)

    inserted = 0
    skipped = 0

    with conn:
        for path in sorted(json_files):
            try:
                data = json.loads(path.read_text())
            except Exception as exc:
                print(f"  WARN: could not read {path}: {exc}", file=sys.stderr)
                continue

            session_id = data.get("session_id")
            case_id = data.get("case_id")
            timestamp = data.get("timestamp", path.stem)
            turns = data.get("turns", [])
            score = data.get("score", {})

            if not session_id or not case_id:
                print(f"  WARN: skipping {path} — missing session_id or case_id", file=sys.stderr)
                continue

            cur = conn.execute(
                """
                INSERT OR IGNORE INTO sessions
                    (session_id, case_id, user_id, timestamp, turns, score)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    case_id,
                    None,  # flat-JSON format had no user_id
                    timestamp,
                    json.dumps(turns),
                    json.dumps(score),
                ),
            )
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1

    conn.close()
    print(f"Migration complete: {inserted} inserted, {skipped} already present.")
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate flat-JSON sessions to SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be done without writing")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
