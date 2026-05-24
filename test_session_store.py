"""
test_session_store.py — Unit tests for the SQLite session store (Issue #21)

All tests run in an isolated temporary database; the production
sessions/council.db file is never touched.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

import session_store as ss


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@dataclass
class _FakeSession:
    case_id: str
    session_id: str
    turns: list
    score: dict
    user_id: str | None = None


def _make_score(
    legal: int = 70,
    strategic: int = 65,
    creativity: int = 60,
    key_moments: list | None = None,
) -> dict:
    return {
        "legal_soundness": legal,
        "strategic_effectiveness": strategic,
        "creativity": creativity,
        "key_moments": key_moments or [],
    }


def _make_session(
    case_id: str = "brown",
    session_id: str = "sess-001",
    user_id: str | None = None,
    **score_kwargs,
) -> _FakeSession:
    return _FakeSession(
        case_id=case_id,
        session_id=session_id,
        turns=[{"role": "user", "text": "arg1"}],
        score=_make_score(**score_kwargs),
        user_id=user_id,
    )


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect SESSIONS_DIR to a fresh temp directory for every test."""
    monkeypatch.setattr(ss, "SESSIONS_DIR", tmp_path)
    yield tmp_path


# ---------------------------------------------------------------------------
# save_session / load_sessions round-trip
# ---------------------------------------------------------------------------


def test_save_and_load_basic():
    s = _make_session()
    ss.save_session(s)

    records = ss.load_sessions("brown")
    assert len(records) == 1
    r = records[0]
    assert r["session_id"] == "sess-001"
    assert r["case_id"] == "brown"
    assert r["score"]["legal_soundness"] == 70


def test_load_returns_empty_for_unknown_case():
    records = ss.load_sessions("nonexistent-case")
    assert records == []


def test_multiple_sessions_ordered_oldest_first():
    for i, sid in enumerate(["s1", "s2", "s3"]):
        ss.save_session(_make_session(session_id=sid, legal=60 + i * 5))

    records = ss.load_sessions("brown")
    assert [r["session_id"] for r in records] == ["s1", "s2", "s3"]


def test_save_session_no_flat_json_written():
    """SQLite store must NOT write any flat .json files."""
    ss.save_session(_make_session())
    # Check the redirected SESSIONS_DIR (set by isolated_db fixture) — not tmp_path
    # which may differ if the fixture were using a separate path.
    assert list(ss.SESSIONS_DIR.rglob("*.json")) == []


# ---------------------------------------------------------------------------
# user_id filtering
# ---------------------------------------------------------------------------


def test_load_sessions_filters_by_user_id():
    ss.save_session(_make_session(session_id="u1-s1", user_id="user-1"))
    ss.save_session(_make_session(session_id="u2-s1", user_id="user-2"))
    ss.save_session(_make_session(session_id="u1-s2", user_id="user-1"))

    user1 = ss.load_sessions("brown", user_id="user-1")
    assert {r["session_id"] for r in user1} == {"u1-s1", "u1-s2"}

    user2 = ss.load_sessions("brown", user_id="user-2")
    assert {r["session_id"] for r in user2} == {"u2-s1"}


def test_load_sessions_no_filter_returns_all_users():
    ss.save_session(_make_session(session_id="a", user_id="alice"))
    ss.save_session(_make_session(session_id="b", user_id="bob"))

    all_records = ss.load_sessions("brown")
    assert len(all_records) == 2


# ---------------------------------------------------------------------------
# key_moments stored and retrieved correctly
# ---------------------------------------------------------------------------


def test_key_moments_round_trip():
    km = {"turn": 2, "label": "best_move", "user_text": "great arg", "commentary": "solid"}
    s = _make_session(key_moments=[km])
    ss.save_session(s)

    records = ss.load_sessions("brown")
    assert records[0]["score"]["key_moments"] == [km]


# ---------------------------------------------------------------------------
# INSERT OR REPLACE (upsert) behaviour
# ---------------------------------------------------------------------------


def test_save_session_upserts_on_duplicate_session_id():
    ss.save_session(_make_session(session_id="dup", legal=50))
    ss.save_session(_make_session(session_id="dup", legal=99))

    records = ss.load_sessions("brown")
    assert len(records) == 1
    assert records[0]["score"]["legal_soundness"] == 99


# ---------------------------------------------------------------------------
# format_history_summary
# ---------------------------------------------------------------------------


def test_format_history_summary_none_on_first_session():
    ss.save_session(_make_session(session_id="only"))
    assert ss.format_history_summary("brown") is None


def test_format_history_summary_shows_best_and_attempts():
    ss.save_session(_make_session(session_id="s1", legal=60, strategic=60, creativity=60))
    ss.save_session(_make_session(session_id="s2", legal=90, strategic=90, creativity=90))
    ss.save_session(_make_session(session_id="s3", legal=70, strategic=70, creativity=70))

    summary = ss.format_history_summary("brown")
    assert summary is not None
    assert "2 prior attempts" in summary
    assert "best: 90/100" in summary


def test_format_history_summary_trend_positive():
    ss.save_session(_make_session(session_id="a", legal=60, strategic=60, creativity=60))
    ss.save_session(_make_session(session_id="b", legal=90, strategic=90, creativity=90))
    ss.save_session(_make_session(session_id="c"))  # current session (excluded)

    summary = ss.format_history_summary("brown")
    assert summary is not None
    assert "trend:" in summary
