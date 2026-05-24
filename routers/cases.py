from __future__ import annotations

from fastapi import APIRouter

from case_library import list_cases

router = APIRouter(tags=["cases"])


@router.get("/cases")
def get_cases() -> list[dict]:
    cases = list_cases(include_drafts=False)
    return [
        {
            "id": c["id"],
            "title": c["title"],
            "proceeding_type": c["proceeding_type"],
            "practice_area": c["practice_area"],
            "user_role": c["user_role"],
        }
        for c in cases
    ]
