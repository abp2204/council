# NOTE: not safe for multi-worker deployments — single uvicorn worker only
_pending: dict[str, str] = {}


def enqueue(session_id: str, text: str) -> None:
    _pending[session_id] = text


def consume(session_id: str) -> str | None:
    return _pending.pop(session_id, None)
