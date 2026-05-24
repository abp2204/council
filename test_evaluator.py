"""
COUNCIL — Evaluator Tests (Issue #19)

Integration tests for EvaluatorRole using Claude Sonnet.
All tests requiring the API are skipped when ANTHROPIC_API_KEY is not set.

Non-API tests (parse logic) always run.
"""

from __future__ import annotations

import os
import pytest

_needs_api_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)


# ── Mock Transcripts ──────────────────────────────────────────────────────────

WEAK_SESSION: list[dict] = [
    {
        "speaker": "opponent",
        "text": (
            "Mr. Marshall, suppose we agree that segregation causes psychological harm — "
            "does that mean any state classification by race is per se unconstitutional, "
            "or only this one?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The Fifth Amendment's due process clause explicitly prohibits racial "
            "segregation in public schools — this Court held as much in Marbury v. Madison."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "But Plessy v. Ferguson is on the books. You're asking us to overrule a "
            "56-year-old precedent. On what authority do we do that short of a "
            "constitutional amendment?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "Plessy v. Ferguson was decided in 1920 and has been widely criticized by "
            "every subsequent court. The Brown precedent itself supports our position."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "You're telling me the intent of the Framers of the Fourteenth Amendment "
            "was to desegregate public schools — but the Congress that ratified the "
            "amendment also funded segregated schools in the District of Columbia. "
            "How do you reconcile that?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The framers of the Fourteenth Amendment specifically debated school "
            "segregation in the congressional record and voted to prohibit it by "
            "a margin of thirty to two."
        ),
    },
]

STRONG_SESSION: list[dict] = [
    {
        "speaker": "opponent",
        "text": (
            "Mr. Marshall, suppose we agree that segregation causes psychological harm — "
            "does that mean any state classification by race is per se unconstitutional, "
            "or only this one?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The evidence before this Court includes the work of Dr. Kenneth Clark, "
            "whose studies show that Black children in segregated schools internalize "
            "a sense of inferiority. That is not conjecture — it is documented "
            "psychological harm caused directly by state action. And under the Equal "
            "Protection Clause, the state may not impose a badge of inferiority on any "
            "class of citizens."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "But Plessy v. Ferguson is on the books. You're asking us to overrule a "
            "56-year-old precedent. On what authority do we do that short of a "
            "constitutional amendment?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "This Court has previously held that separate facilities are inherently "
            "unequal in the context of graduate education — McLaurin v. Oklahoma and "
            "Sweatt v. Painter. The principle does not stop at graduate school. The "
            "Equal Protection Clause applies wherever the state segregates, and Plessy "
            "cannot survive that reading. Longevity does not cure a constitutional error."
        ),
    },
    {
        "speaker": "opponent",
        "text": (
            "You're telling me the intent of the Framers of the Fourteenth Amendment "
            "was to desegregate public schools — but the Congress that ratified the "
            "amendment also funded segregated schools in the District of Columbia. "
            "How do you reconcile that?"
        ),
    },
    {
        "speaker": "user",
        "text": (
            "The DC argument only reinforces our position: if Congress itself violated "
            "the Fourteenth Amendment by funding segregated schools, this Court should "
            "say so — and say so clearly — rather than use that constitutional failure "
            "to justify more of the same. The Amendment's text controls, not the "
            "practice of those who fell short of its guarantee."
        ),
    },
]

HISTORICAL_RECORD = [
    "Brown v. Board of Education (1954) was argued by Thurgood Marshall for the NAACP.",
    "The case consolidated appeals from Kansas, South Carolina, Virginia, and Delaware.",
    "Dr. Kenneth Clark's doll studies showed Black children preferred white dolls, demonstrating internalized inferiority.",
    "Plessy v. Ferguson (1896) established the 'separate but equal' doctrine.",
    "McLaurin v. Oklahoma State Regents (1950) found that restrictions on a Black graduate student violated Equal Protection.",
    "Sweatt v. Painter (1950) required the University of Texas Law School to admit a Black applicant.",
]

MINIMAL_TRANSCRIPT: list[dict] = [
    {"speaker": "opponent", "text": "What is your central argument here?"},
    {"speaker": "user", "text": "The Equal Protection Clause prohibits state-enforced racial segregation in public schools."},
    {"speaker": "opponent", "text": "How do you distinguish Plessy v. Ferguson?"},
    {"speaker": "user", "text": "Plessy relied on a fiction of equality that the record before this Court disproves."},
    {"speaker": "opponent", "text": "What remedy do you seek?"},
    {"speaker": "user", "text": "We seek a declaration that segregated schools are unconstitutional and an order to desegregate."},
]


# ── Integration Tests ─────────────────────────────────────────────────────────


@_needs_api_key
def test_evaluate_returns_score_with_all_fields():
    from evaluator import EvaluatorRole, Score

    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT, historical_record=HISTORICAL_RECORD)

    assert isinstance(score, Score)
    assert 0 <= score.legal_soundness <= 100
    assert 0 <= score.strategic_effectiveness <= 100
    assert 0 <= score.creativity <= 100


@_needs_api_key
def test_evaluate_returns_3_to_5_key_moments():
    from evaluator import EvaluatorRole

    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT, historical_record=HISTORICAL_RECORD)

    assert 3 <= len(score.key_moments) <= 5


@_needs_api_key
def test_key_moment_user_text_is_substring_of_user_turn():
    from evaluator import EvaluatorRole

    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT, historical_record=HISTORICAL_RECORD)

    user_texts = [t["text"] for t in MINIMAL_TRANSCRIPT if t["speaker"] == "user"]

    for km in score.key_moments:
        assert km.user_text, f"key_moment.user_text is empty for turn {km.turn_number}"
        matched = any(
            km.user_text in user_text or user_text in km.user_text
            for user_text in user_texts
        )
        assert matched, (
            f"key_moment.user_text not found in any user turn.\n"
            f"  user_text: {km.user_text!r}\n"
            f"  user turns: {user_texts}"
        )


@_needs_api_key
def test_key_moment_commentary_is_non_empty():
    from evaluator import EvaluatorRole

    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT, historical_record=HISTORICAL_RECORD)

    for km in score.key_moments:
        assert isinstance(km.commentary, str) and km.commentary.strip(), (
            f"key_moment commentary is empty for turn {km.turn_number}"
        )


@_needs_api_key
def test_strong_session_scores_higher_than_weak():
    from evaluator import EvaluatorRole

    evaluator = EvaluatorRole()
    weak_score = evaluator.evaluate(WEAK_SESSION, historical_record=HISTORICAL_RECORD)
    strong_score = evaluator.evaluate(STRONG_SESSION, historical_record=HISTORICAL_RECORD)

    assert strong_score.legal_soundness > weak_score.legal_soundness, (
        f"strong_session.legal_soundness ({strong_score.legal_soundness}) "
        f"should be > weak_session.legal_soundness ({weak_score.legal_soundness})"
    )


@_needs_api_key
def test_all_key_moment_commentaries_are_unique():
    from evaluator import EvaluatorRole

    evaluator = EvaluatorRole()
    weak_score = evaluator.evaluate(WEAK_SESSION, historical_record=HISTORICAL_RECORD)
    strong_score = evaluator.evaluate(STRONG_SESSION, historical_record=HISTORICAL_RECORD)

    all_commentaries = (
        [km.commentary for km in weak_score.key_moments]
        + [km.commentary for km in strong_score.key_moments]
    )
    assert len(all_commentaries) == len(set(all_commentaries)), (
        "Duplicate commentary strings found across sessions"
    )


@_needs_api_key
def test_evaluate_with_no_historical_record():
    from evaluator import EvaluatorRole, Score

    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT)

    assert isinstance(score, Score)
    assert 3 <= len(score.key_moments) <= 5


@_needs_api_key
def test_evaluate_with_case_context():
    from evaluator import EvaluatorRole, Score

    case = {"id": "brown-v-board", "title": "Brown v. Board of Education", "historical_record": HISTORICAL_RECORD}
    evaluator = EvaluatorRole()
    score = evaluator.evaluate(MINIMAL_TRANSCRIPT, historical_record=HISTORICAL_RECORD, case=case)

    assert isinstance(score, Score)
    assert 0 <= score.legal_soundness <= 100


# ── Non-API Tests (always run) ────────────────────────────────────────────────

class TestParseScore:
    """Tests for _parse_score that don't require an API key."""

    def test_parse_score_clamps_out_of_range(self):
        import importlib
        import sys

        # Temporarily set a fake key so EvaluatorRole can be instantiated
        os.environ["ANTHROPIC_API_KEY"] = "sk-fake-key-for-parse-test"
        try:
            # Re-import to pick up the env var
            if "evaluator" in sys.modules:
                del sys.modules["evaluator"]
            from evaluator import EvaluatorRole

            evaluator = EvaluatorRole.__new__(EvaluatorRole)

            transcript = [
                {"speaker": "user", "text": "My argument about equal protection."},
                {"speaker": "user", "text": "Furthermore, Plessy must be overruled."},
                {"speaker": "user", "text": "The Constitution demands desegregation."},
            ]

            raw_json = """{
                "legal_soundness": 150,
                "strategic_effectiveness": -5,
                "creativity": 80,
                "key_moments": [
                    {"turn_number": 1, "label": "best_move", "user_text": "My argument about equal protection.", "commentary": "Strong opening."},
                    {"turn_number": 2, "label": "worst_move", "user_text": "Furthermore, Plessy must be overruled.", "commentary": "Weak claim."},
                    {"turn_number": 3, "label": "deviation_point", "user_text": "The Constitution demands desegregation.", "commentary": "Novel framing."}
                ]
            }"""

            score = evaluator._parse_score(raw_json, transcript)

            assert score.legal_soundness == 100
            assert score.strategic_effectiveness == 0
            assert score.creativity == 80
        finally:
            del os.environ["ANTHROPIC_API_KEY"]
