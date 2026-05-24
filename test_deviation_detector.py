"""
COUNCIL — Semantic Deviation Detection Tests (sentence-embeddings interface)

Tests the DeviationDetector class which uses sentence-transformers + cosine similarity.
No API key required; no Ollama required.

Run: pytest test_deviation_detector.py -v
"""

from __future__ import annotations

import pytest

from deviation_detector import DeviationDetector, DetectionResult, SIMILARITY_THRESHOLD


@pytest.fixture(scope="module")
def detector() -> DeviationDetector:
    return DeviationDetector()


# ── Return type ───────────────────────────────────────────────────────────────

def test_detect_returns_tuple(detector: DeviationDetector) -> None:
    result = detector.detect("The sky is blue.", 0, ["The sky is blue."])
    assert isinstance(result, tuple)
    assert len(result) == 2
    is_deviation, score = result
    assert isinstance(is_deviation, bool)
    assert isinstance(score, float)
    assert -0.01 <= score <= 1.0


def test_detect_detailed_returns_dataclass(detector: DeviationDetector) -> None:
    result = detector.detect_detailed("The sky is blue.", 0, ["The sky is blue."])
    assert isinstance(result, DetectionResult)
    assert isinstance(result.is_deviation, bool)
    assert isinstance(result.similarity_score, float)


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_turn_index_beyond_record_length(detector: DeviationDetector) -> None:
    is_deviation, score = detector.detect("Some argument.", 5, ["only one entry"])
    assert is_deviation is False
    assert score == 1.0


def test_turn_index_exactly_at_length(detector: DeviationDetector) -> None:
    record = ["entry zero"]
    is_deviation, score = detector.detect("Some argument.", 1, record)
    assert is_deviation is False
    assert score == 1.0


def test_empty_user_text(detector: DeviationDetector) -> None:
    is_deviation, score = detector.detect("", 0, ["Plessy was wrongly decided."])
    assert is_deviation is False
    assert score == 1.0


def test_whitespace_only_user_text(detector: DeviationDetector) -> None:
    is_deviation, score = detector.detect("   \t\n  ", 0, ["Plessy was wrongly decided."])
    assert is_deviation is False
    assert score == 1.0


def test_empty_historical_record(detector: DeviationDetector) -> None:
    is_deviation, score = detector.detect("Some argument.", 0, [])
    assert is_deviation is False
    assert score == 1.0


def test_empty_historical_entry_returns_deviation(detector: DeviationDetector) -> None:
    is_deviation, score = detector.detect("Some argument.", 0, [""])
    assert is_deviation is True
    assert score == 0.0


# ── Semantic similarity ───────────────────────────────────────────────────────

def test_identical_text_not_deviation(detector: DeviationDetector) -> None:
    text = "Racial segregation violates the Equal Protection Clause."
    is_deviation, score = detector.detect(text, 0, [text])
    assert is_deviation is False
    assert score > SIMILARITY_THRESHOLD


def test_semantically_similar_not_deviation(detector: DeviationDetector) -> None:
    user = "Racial segregation in public schools violates the Equal Protection Clause."
    historical = "Racial segregation in public schools violates the Equal Protection Clause."
    is_deviation, score = detector.detect(user, 0, [historical])
    assert is_deviation is False
    assert score > SIMILARITY_THRESHOLD


def test_semantically_different_is_deviation(detector: DeviationDetector) -> None:
    user = "I concede that separate but equal may be constitutional if facilities are truly equal."
    historical = "Plessy was wrongly decided and must be overturned."
    is_deviation, score = detector.detect(user, 0, [historical])
    assert is_deviation is True
    assert score < SIMILARITY_THRESHOLD


def test_unrelated_topics_is_deviation(detector: DeviationDetector) -> None:
    user = "The weather in New York is sunny today."
    historical = "The Equal Protection Clause forbids state-sponsored racial segregation."
    is_deviation, score = detector.detect(user, 0, [historical])
    assert is_deviation is True
    assert score < SIMILARITY_THRESHOLD


# ── Custom threshold ──────────────────────────────────────────────────────────

def test_custom_threshold_strict(detector: DeviationDetector) -> None:
    text = "Racial segregation violates the Equal Protection Clause."
    similar = "Segregation breaches equal protection under the Fourteenth Amendment."
    is_dev_loose, _ = detector.detect(text, 0, [similar], threshold=0.1)
    is_dev_strict, _ = detector.detect(text, 0, [similar], threshold=0.999)
    assert is_dev_loose is False
    assert is_dev_strict is True


# ── Correct turn_index indexing ───────────────────────────────────────────────

def test_correct_turn_index_used(detector: DeviationDetector) -> None:
    user = "Segregation violates the Equal Protection Clause."
    record = [
        "Completely unrelated contract dispute about cheese.",
        "Segregation violates the Equal Protection Clause.",
    ]
    is_dev_turn0, _ = detector.detect(user, 0, record)
    is_dev_turn1, _ = detector.detect(user, 1, record)
    assert is_dev_turn0 is True
    assert is_dev_turn1 is False


# ── Integration: brown.json historical record ─────────────────────────────────

def test_brown_historical_record_spot_check() -> None:
    """Spot-check against the actual Brown v. Board historical record."""
    try:
        import json
        import os
        cases_dir = os.path.join(os.path.dirname(__file__), "cases")
        brown_path = os.path.join(cases_dir, "brown.json")
        with open(brown_path) as f:
            brown = json.load(f)
        record: list[str] = brown.get("historical_record", [])
        if not record:
            pytest.skip("brown.json has no historical_record")
    except FileNotFoundError:
        pytest.skip("brown.json not found")

    detector = DeviationDetector()

    historical_turn_0 = record[0]
    is_dev, score = detector.detect(historical_turn_0, 0, record)
    assert is_dev is False, (
        f"Exact historical text flagged as deviation (score={score:.3f})"
    )

    is_dev_unrelated, _ = detector.detect(
        "The statute of limitations bars this action.", 0, record
    )
    assert is_dev_unrelated is True
