"""
COUNCIL — Case Library (Issue #8)

Loads Cases from JSON files in the cases/ directory. Adding a new Case
requires only running the ingestion pipeline and dropping a JSON file
in cases/ — no code changes needed.

Case JSON schema (all fields required):
    id, title, status,
    proceeding_type, practice_area,
    user_role, user_role_context, historical_opening,
    historical_record  (list[str]),
    opposing_role.name, opposing_role.system_prompt,
    opposing_role.mock_probes (list[str]),
    opposing_role.mock_close (str)
"""

import json
import os
import tempfile
from pathlib import Path

CASES_DIR = Path(__file__).parent / "cases"


class DraftCaseError(Exception):
    def __init__(self, case_id: str) -> None:
        super().__init__(
            f"Case '{case_id}' is in draft status and cannot be loaded by non-operators."
        )


def load_case(case_id: str, operator: bool = False) -> dict:
    """Load a Case record by ID. Raises KeyError if not found.
    Raises DraftCaseError if the case is a draft and operator=False."""
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        available = [p.stem for p in sorted(CASES_DIR.glob("*.json"))]
        raise KeyError(
            f"No case found for ID {case_id!r}. "
            f"Available: {', '.join(available) or '(none)'}"
        )
    with open(path) as f:
        case = json.load(f)
    if case.get("status") == "draft" and not operator:
        raise DraftCaseError(case_id)
    return case


def list_cases(include_drafts: bool = False) -> list[dict]:
    """Return summary dicts for all cases, sorted by ID.
    Excludes draft cases unless include_drafts=True.
    Cases without a status field are treated as published.
    Cases with unrecognised status values (e.g. 'archived') are excluded."""
    summaries = []
    for path in sorted(CASES_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        status = data.get("status")
        is_published = status == "published" or status is None
        is_draft = status == "draft"
        if not is_published and not is_draft:
            continue
        if is_draft and not include_drafts:
            continue
        summaries.append({
            "id": data["id"],
            "title": data["title"],
            "proceeding_type": data.get("proceeding_type", ""),
            "practice_area": data.get("practice_area", ""),
            "user_role": data.get("user_role", ""),
        })
    return summaries


def promote_case(case_id: str) -> None:
    """Set a case's status to 'published' and write back to disk."""
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        available = [p.stem for p in sorted(CASES_DIR.glob("*.json"))]
        raise KeyError(
            f"No case found for ID {case_id!r}. "
            f"Available: {', '.join(available) or '(none)'}"
        )
    with open(path) as f:
        case = json.load(f)
    case["status"] = "published"
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(case, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise
