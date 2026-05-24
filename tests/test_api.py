"""
HTTP integration tests for the COUNCIL FastAPI layer.
Uses TestClient with MockOpposingRole + MockEvaluator (COUNCIL_TESTING=1).
No real API keys are required.
"""
from __future__ import annotations

import io


# ── Helpers ───────────────────────────────────────────────────────────────────


def _run_session_to_end(client, case_id: str) -> tuple[str, dict]:
    """Submit moves until closes=True. Returns (session_id, final_move_response)."""
    r = client.post("/sessions", json={"case_id": case_id})
    assert r.status_code == 201, r.text
    session_id = r.json()["session_id"]

    for _ in range(15):
        r = client.post(f"/sessions/{session_id}/moves", json={"text": "test argument"})
        assert r.status_code == 200, r.text
        data = r.json()
        if data["closes"]:
            return session_id, data

    raise AssertionError("Session did not close within 15 moves")


# ── Group A: Health + Cases ───────────────────────────────────────────────────


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_cases_returns_list(client):
    r = client.get("/cases")
    assert r.status_code == 200
    cases = r.json()
    assert isinstance(cases, list)
    assert len(cases) > 0


def test_cases_have_required_fields(client):
    r = client.get("/cases")
    for case in r.json():
        assert "id" in case
        assert "title" in case
        assert "proceeding_type" in case
        assert "practice_area" in case
        assert "user_role" in case


def test_cases_excludes_drafts(client):
    import json
    from pathlib import Path

    cases_dir = Path(__file__).parent.parent / "cases"
    draft_ids = {
        json.loads(p.read_text())["id"]
        for p in cases_dir.glob("*.json")
        if json.loads(p.read_text()).get("status") == "draft"
    }

    r = client.get("/cases")
    returned_ids = {c["id"] for c in r.json()}
    assert not (draft_ids & returned_ids), "Draft cases leaked into GET /cases response"


# ── Group B: Session Creation ─────────────────────────────────────────────────


def test_create_session_returns_session_id(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    assert r.status_code == 201
    data = r.json()
    assert "session_id" in data
    assert data["state"] == "IN_SESSION"
    assert data["opening"]


def test_create_session_unknown_case_returns_404(client):
    r = client.post("/sessions", json={"case_id": "nonexistent-case-xyz"})
    assert r.status_code == 404


# ── Group C: Move Submission ───────────────────────────────────────────────────


def test_submit_text_move(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]

    r = client.post(f"/sessions/{session_id}/moves", json={"text": "Opening argument"})
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert isinstance(data["closes"], bool)
    assert isinstance(data["deviation"], bool)
    assert data["stream_url"] == f"/sessions/{session_id}/stream"
    assert data.get("transcription") is None


def test_submit_audio_move(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]

    fake_audio = io.BytesIO(b"\x00" * 100)
    r = client.post(
        f"/sessions/{session_id}/moves",
        files={"audio": ("test.wav", fake_audio, "audio/wav")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["transcription"] == "mocked transcription"
    assert "response" in data


def test_submit_move_unknown_session_returns_404(client):
    r = client.post("/sessions/nonexistent-session-id/moves", json={"text": "hello"})
    assert r.status_code == 404


def test_submit_move_after_session_end_returns_409(client, published_case_id):
    session_id, _ = _run_session_to_end(client, published_case_id)
    r = client.post(f"/sessions/{session_id}/moves", json={"text": "too late"})
    assert r.status_code == 409


# ── Group D: SSE Streaming ────────────────────────────────────────────────────


def test_stream_after_move_contains_done(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]
    client.post(f"/sessions/{session_id}/moves", json={"text": "Argument"})

    r = client.get(f"/sessions/{session_id}/stream")
    assert r.status_code == 200
    assert "[DONE]" in r.text


def test_stream_no_pending_returns_404(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]
    # No move submitted — no pending response
    r = client.get(f"/sessions/{session_id}/stream")
    assert r.status_code == 404


def test_stream_consumed_on_first_get(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]
    client.post(f"/sessions/{session_id}/moves", json={"text": "Argument"})

    client.get(f"/sessions/{session_id}/stream")  # consumes
    r = client.get(f"/sessions/{session_id}/stream")  # second GET → 404
    assert r.status_code == 404


# ── Group E: Evaluate + Review ────────────────────────────────────────────────


def test_evaluate_while_in_session_returns_409(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]
    r = client.post(f"/sessions/{session_id}/evaluate")
    assert r.status_code == 409


def test_evaluate_after_session_end_returns_score(client, published_case_id):
    session_id, _ = _run_session_to_end(client, published_case_id)
    r = client.post(f"/sessions/{session_id}/evaluate")
    assert r.status_code == 200
    data = r.json()
    assert "legal_soundness" in data
    assert "strategic_effectiveness" in data
    assert "creativity" in data
    assert isinstance(data["key_moments"], list)


def test_review_after_evaluate(client, published_case_id):
    session_id, _ = _run_session_to_end(client, published_case_id)
    client.post(f"/sessions/{session_id}/evaluate")

    r = client.get(f"/sessions/{session_id}/review/0")
    assert r.status_code == 200
    data = r.json()
    assert "turn" in data
    assert "label" in data
    assert "user_text" in data
    assert "commentary" in data


def test_review_out_of_range_returns_404(client, published_case_id):
    session_id, _ = _run_session_to_end(client, published_case_id)
    client.post(f"/sessions/{session_id}/evaluate")

    r = client.get(f"/sessions/{session_id}/review/999")
    assert r.status_code == 404


def test_review_before_evaluate_returns_409(client, published_case_id):
    session_id, _ = _run_session_to_end(client, published_case_id)
    # Session is SESSION_END but not yet SCORED
    r = client.get(f"/sessions/{session_id}/review/0")
    assert r.status_code == 409


def test_review_unknown_session_returns_404(client):
    r = client.get("/sessions/nonexistent/review/0")
    assert r.status_code == 404


# ── Group F: History ──────────────────────────────────────────────────────────


def test_history_returns_list(client, published_case_id):
    r = client.post("/sessions", json={"case_id": published_case_id})
    session_id = r.json()["session_id"]

    r = client.get(f"/sessions/{session_id}/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_history_unknown_session_returns_404(client):
    r = client.get("/sessions/nonexistent/history")
    assert r.status_code == 404
