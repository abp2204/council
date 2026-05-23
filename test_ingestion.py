"""
COUNCIL — End-to-End Test: Transcript Ingestion Pipeline

Run:
    python test_ingestion.py
    pytest test_ingestion.py -v

If ANTHROPIC_API_KEY is not set, the Historical Record (parsing-only) assertions
are verified and the LLM-dependent sections are skipped.

Transcript snippet: Brown v. Board of Education, Dec 9, 1952 (public domain).
"""

import os
import sys
import json
import pprint
from unittest.mock import MagicMock, patch

import pytest

from transcript_ingestion import (
    ingest_transcript,
    extract_historical_record,
    synthesize_system_prompt,
    _parse_turns,
)

# ── Hardcoded transcript snippet ───────────────────────────────────────────────

TRANSCRIPT = """
MR. MARSHALL: May it please the Court, this case is here on certiorari to the United States Court of Appeals for the Fourth Circuit. The question presented is whether the system of racial segregation in the public schools of Topeka, Kansas, which was maintained pursuant to Kansas statute, is in violation of the equal protection clause of the Fourteenth Amendment.

JUSTICE FRANKFURTER: Mr. Marshall, is it your position that all racial classifications by government are unconstitutional?

MR. MARSHALL: No, sir. Our position is narrow. We are attacking specifically the racial classification in public education. The evidence shows that the separation itself generates a feeling of inferiority as to the status of the children in the community that may affect their hearts and minds in a way unlikely ever to be undone.

JUSTICE FRANKFURTER: But did not this Court in the Plessy case establish that separate but equal satisfies the constitutional requirement?

MR. MARSHALL: Plessy involved transportation, not education. And even if we accept Plessy's framework, the evidence in this record demonstrates that separate facilities in education are inherently unequal. The State of Kansas has not even attempted to make them equal. But we say more — we say Plessy was wrong when decided and must be overruled.

JUSTICE DOUGLAS: What would be the practical effect of a ruling in your favor on school systems throughout the South?

MR. MARSHALL: The practical effect, Your Honor, is that children of all races would attend the same schools. We are not asking this Court to order any particular remedy today. We ask for a declaration that enforced segregation violates the Constitution.

JUSTICE FRANKFURTER: Mr. Marshall, assuming we agreed with your constitutional argument, would you have us order immediate desegregation?

MR. MARSHALL: We would, Your Honor, but we recognize this Court has flexibility in fashioning a remedy. The constitutional violation is clear; the remedy can be tailored to practical realities.
"""

LAWYER_NAME = "MR. MARSHALL"
OPPOSING_NAME = "JUSTICE FRANKFURTER"

EXPECTED_MARSHALL_TURNS = [
    "May it please the Court, this case is here on certiorari to the United States Court of Appeals for the Fourth Circuit. The question presented is whether the system of racial segregation in the public schools of Topeka, Kansas, which was maintained pursuant to Kansas statute, is in violation of the equal protection clause of the Fourteenth Amendment.",
    "No, sir. Our position is narrow. We are attacking specifically the racial classification in public education. The evidence shows that the separation itself generates a feeling of inferiority as to the status of the children in the community that may affect their hearts and minds in a way unlikely ever to be undone.",
    "Plessy involved transportation, not education. And even if we accept Plessy's framework, the evidence in this record demonstrates that separate facilities in education are inherently unequal. The State of Kansas has not even attempted to make them equal. But we say more — we say Plessy was wrong when decided and must be overruled.",
    "The practical effect, Your Honor, is that children of all races would attend the same schools. We are not asking this Court to order any particular remedy today. We ask for a declaration that enforced segregation violates the Constitution.",
    "We would, Your Honor, but we recognize this Court has flexibility in fashioning a remedy. The constitutional violation is clear; the remedy can be tailored to practical realities.",
]

PROFILE_FIELDS = [
    "argumentation_patterns",
    "signature_questions_or_objections",
    "rhetorical_habits",
    "tone_and_cadence",
]

SAMPLE_PROFILE = {
    "name": "JUSTICE FRANKFURTER",
    "role": "opposing",
    "argumentation_patterns": "Builds sequential doctrinal chains demanding precise limiting principles before accepting any factual premise.",
    "signature_questions_or_objections": "Demands the exact doctrinal mechanism for overruling precedent; presses for the limiting principle on any harm-based argument.",
    "rhetorical_habits": "Uses Socratic questioning relentlessly; references canonical precedents and historical context; rarely accepts the first answer offered.",
    "tone_and_cadence": "Professorial, probing, and relentless — never hostile but always exacting. Deliberate pace with sharp follow-ups.",
}


# ── Parsing-only tests (no API key required) ───────────────────────────────────

def test_parsing_only():
    """Verify Historical Record extraction without touching the API."""
    record = extract_historical_record(TRANSCRIPT, LAWYER_NAME)

    assert len(record) >= 3, (
        f"Expected >= 3 turns for {LAWYER_NAME}, got {len(record)}"
    )
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record, (
            f"Expected turn not found verbatim in historical_record:\n{expected[:120]!r}"
        )


def test_parse_turns_finds_all_speakers():
    """_parse_turns should identify all distinct speakers in the snippet."""
    turns = _parse_turns(TRANSCRIPT)
    speakers = {label for label, _ in turns}
    assert "MR. MARSHALL" in speakers
    assert "JUSTICE FRANKFURTER" in speakers
    assert "JUSTICE DOUGLAS" in speakers


def test_parse_turns_count():
    """Transcript snippet has 9 speaker turns total."""
    turns = _parse_turns(TRANSCRIPT)
    assert len(turns) == 9


# ── System prompt synthesis tests ─────────────────────────────────────────────

def _make_mock_client(response_text: str):
    """Return a mock anthropic.Anthropic client that returns response_text."""
    mock_content = MagicMock()
    mock_content.text = response_text
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_message.stop_reason = "end_turn"
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


MOCK_SYSTEM_PROMPT = """\
You are JUSTICE FRANKFURTER, an opposing counsel in this proceeding.

## Argumentation Patterns
Builds sequential doctrinal chains demanding precise limiting principles before accepting any factual premise.

## Signature Questions or Objections
Demands the exact doctrinal mechanism for overruling precedent; presses for the limiting principle on any harm-based argument.

## Rhetorical Habits
Uses Socratic questioning relentlessly; references canonical precedents and historical context; rarely accepts the first answer offered.

## Tone and Cadence
Professorial, probing, and relentless — never hostile but always exacting. Deliberate pace with sharp follow-ups.

## Rules — Absolute
- You NEVER provide scores, ratings, performance feedback, or meta-commentary about argument quality. You are a sitting Justice during oral argument, not a coach.
- You NEVER break character or acknowledge that this is a simulation.

## Session Close
Close after raising all main topics at least once AND at least 3 user turns have occurred.

## Output Format
Respond with ONLY a valid JSON object:
{"response": str, "closes": bool}
"""


def test_synthesize_system_prompt_contains_fields_mock():
    """
    synthesize_system_prompt produces a prompt containing all four profile fields
    and the JSON output contract.  Uses a mock so no API key is needed.
    """
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value = _make_mock_client(MOCK_SYSTEM_PROMPT)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = synthesize_system_prompt(SAMPLE_PROFILE)

    assert isinstance(result, str) and result.strip(), "Result must be a non-empty string"

    # Each of the four behavioural field values must appear (or be paraphrased —
    # we check key substrings that are in our mock response).
    assert "JUSTICE FRANKFURTER" in result, "Persona name must appear in system prompt"
    assert "opposing" in result.lower(), (
        "Persona role must be reflected in system prompt"
    )

    # Check JSON output contract
    assert '"response"' in result, (
        'System prompt must contain the JSON output contract with "response" key'
    )
    assert '"closes"' in result or "closes" in result, (
        "System prompt must contain the closes field reference"
    )

    # Check no-meta-commentary constraint (ADR 0001)
    lower = result.lower()
    assert any(phrase in lower for phrase in ["never", "not", "no "]), (
        "System prompt must include a prohibition (never score/rate/break character)"
    )


def test_synthesize_system_prompt_contains_profile_values_mock():
    """
    The generated system prompt must incorporate the four profile field values.
    """
    # The mock system prompt includes the actual field content from SAMPLE_PROFILE.
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value = _make_mock_client(MOCK_SYSTEM_PROMPT)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            result = synthesize_system_prompt(SAMPLE_PROFILE)

    # Spot-check distinctive substrings from each profile field.
    assert "doctrinal" in result.lower(), (
        "argumentation_patterns content expected in system prompt"
    )
    assert "limiting principle" in result.lower(), (
        "signature_questions_or_objections content expected in system prompt"
    )
    assert "socratic" in result.lower(), (
        "rhetorical_habits content expected in system prompt"
    )
    assert "professorial" in result.lower(), (
        "tone_and_cadence content expected in system prompt"
    )


def test_synthesize_system_prompt_missing_key_raises():
    """
    If the API returns a response without the JSON contract, raise ValueError.
    """
    bad_response = "You are Justice Frankfurter. Ask hard questions."
    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value = _make_mock_client(bad_response)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with pytest.raises(ValueError, match="JSON output contract"):
                synthesize_system_prompt(SAMPLE_PROFILE)


def test_synthesize_system_prompt_no_api_key():
    """synthesize_system_prompt raises EnvironmentError when key is absent."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY"):
            synthesize_system_prompt(SAMPLE_PROFILE)


# ── Live tests (require ANTHROPIC_API_KEY) ─────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="needs ANTHROPIC_API_KEY",
)
def test_full_ingestion_live():
    """Run the full pipeline (parsing + LLM profile extraction)."""
    result = ingest_transcript(TRANSCRIPT, LAWYER_NAME, OPPOSING_NAME)

    record = result["historical_record"]
    assert len(record) >= 3
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record

    profile = result["profile"]
    assert profile.get("name")
    assert profile.get("role")
    for field_name in PROFILE_FIELDS:
        value = profile.get(field_name)
        assert isinstance(value, str) and value.strip(), (
            f"profile['{field_name}'] must be a non-empty string, got: {value!r}"
        )


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="needs ANTHROPIC_API_KEY",
)
def test_synthesize_system_prompt_synthesis_live():
    """
    Live synthesis test: generated prompt contains profile field values and
    the JSON output contract.
    """
    result = synthesize_system_prompt(SAMPLE_PROFILE)

    assert isinstance(result, str) and result.strip()
    assert '"response"' in result, (
        'Generated system prompt must contain JSON output contract with "response"'
    )
    assert "JUSTICE FRANKFURTER" in result or "Frankfurter" in result, (
        "Generated system prompt must reference the persona name"
    )
    for field in PROFILE_FIELDS:
        # Each field value was passed to the LLM — some substring should appear
        field_value = SAMPLE_PROFILE[field]
        # We check a 20-char substring to tolerate minor paraphrasing
        snippet = field_value[:20]
        assert snippet in result or field_value.split()[0] in result, (
            f"Profile field '{field}' value not reflected in generated system prompt"
        )


# ── Legacy standalone runner (kept for backwards compatibility) ─────────────────

def _run_legacy():
    """Run parsing-only test then optionally the full ingestion."""
    print("=" * 60)
    print("PART 1 — Historical Record (parsing only, no LLM)")
    print("=" * 60)

    record = extract_historical_record(TRANSCRIPT, LAWYER_NAME)

    print(f"\nExtracted {len(record)} turn(s) for '{LAWYER_NAME}':")
    for i, turn in enumerate(record, 1):
        print(f"\n  [Turn {i}] {turn[:80]}{'...' if len(turn) > 80 else ''}")

    assert len(record) >= 3
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record
    print(f"[PASS] Historical Record has {len(record)} turn(s) (>= 3 required)")
    print(f"[PASS] All {len(EXPECTED_MARSHALL_TURNS)} expected turns appear verbatim")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "\n[SKIP] ANTHROPIC_API_KEY is not set — skipping LLM tests.\n"
            "       Set the environment variable and re-run to test the full pipeline."
        )
        print("\nAll parsing assertions PASSED.")
        sys.exit(0)

    print("\n" + "=" * 60)
    print("PART 2 — Full ingestion (parsing + LLM profile)")
    print("=" * 60)

    result = ingest_transcript(TRANSCRIPT, LAWYER_NAME, OPPOSING_NAME)
    pprint.pprint(result, width=80, sort_dicts=False)

    record = result["historical_record"]
    assert len(record) >= 3
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record
    profile = result["profile"]
    assert profile.get("name")
    assert profile.get("role")
    for field_name in PROFILE_FIELDS:
        value = profile.get(field_name)
        assert isinstance(value, str) and value.strip()
    print(f"[PASS] All 5 profile fields are non-empty strings for '{OPPOSING_NAME}'")

    print("\nAll assertions PASSED.")


if __name__ == "__main__":
    _run_legacy()
