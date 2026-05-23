"""
Tests for case_library draft/published status feature (Issue #17).
"""

import json
import pytest
from pathlib import Path
import case_library
from case_library import load_case, list_cases, promote_case, DraftCaseError


def _write_case(directory: Path, case_id: str, status: str | None = None) -> None:
    data: dict = {
        "id": case_id,
        "title": f"Test Case {case_id}",
        "proceeding_type": "oral_argument",
        "practice_area": "constitutional_law",
        "user_role": "Counsel",
    }
    if status is not None:
        data["status"] = status
    path = directory / f"{case_id}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@pytest.fixture(autouse=True)
def patch_cases_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(case_library, "CASES_DIR", tmp_path)
    return tmp_path


def test_list_cases_returns_only_published(patch_cases_dir):
    _write_case(patch_cases_dir, "pub", status="published")
    _write_case(patch_cases_dir, "draft_case", status="draft")

    result = list_cases()

    ids = [c["id"] for c in result]
    assert "pub" in ids
    assert "draft_case" not in ids


def test_list_cases_include_drafts_returns_all(patch_cases_dir):
    _write_case(patch_cases_dir, "pub", status="published")
    _write_case(patch_cases_dir, "draft_case", status="draft")

    result = list_cases(include_drafts=True)

    ids = [c["id"] for c in result]
    assert "pub" in ids
    assert "draft_case" in ids


def test_promote_case_sets_published_on_disk(patch_cases_dir):
    _write_case(patch_cases_dir, "draft_case", status="draft")

    promote_case("draft_case")

    path = patch_cases_dir / "draft_case.json"
    with open(path) as f:
        data = json.load(f)
    assert data["status"] == "published"

    result = list_cases()
    assert any(c["id"] == "draft_case" for c in result)


def test_load_draft_as_non_operator_raises(patch_cases_dir):
    _write_case(patch_cases_dir, "draft_case", status="draft")

    with pytest.raises(DraftCaseError):
        load_case("draft_case", operator=False)


def test_load_draft_as_operator_succeeds(patch_cases_dir):
    _write_case(patch_cases_dir, "draft_case", status="draft")

    case = load_case("draft_case", operator=True)

    assert case["id"] == "draft_case"
    assert case["status"] == "draft"


def test_case_without_status_treated_as_published(patch_cases_dir):
    _write_case(patch_cases_dir, "legacy", status=None)

    case = load_case("legacy")
    assert case["id"] == "legacy"

    result = list_cases()
    assert any(c["id"] == "legacy" for c in result)
