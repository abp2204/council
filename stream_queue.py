from __future__ import annotations

# NOTE: not safe for multi-worker deployments — single uvicorn worker only
_pending: dict[str, list[str]] = {}


def reset_tokens(session_id: str) -> None:
    """Clear any previously pending tokens for a session before enqueueing new ones."""
    _pending.pop(session_id, None)


def enqueue_token(session_id: str, token: str) -> None:
    """Append a single token to the pending token list for a session."""
    if session_id not in _pending:
        _pending[session_id] = []
    _pending[session_id].append(token)


def consume_tokens(session_id: str) -> list[str] | None:
    """Remove and return all pending tokens for a session, or None if none."""
    return _pending.pop(session_id, None)


# ── Backward-compatible single-string API ────────────────────────────────────

def enqueue(session_id: str, text: str) -> None:
    """Store full text as a single-element token list (backward compat)."""
    _pending[session_id] = [text]


def consume(session_id: str) -> str | None:
    """Remove and return joined tokens as a string (backward compat)."""
    tokens = _pending.pop(session_id, None)
    return "".join(tokens) if tokens else None
