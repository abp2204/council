"""
COUNCIL — End-to-End Test: Transcript Ingestion Pipeline

Run:
    python test_ingestion.py

If ANTHROPIC_API_KEY is not set, the Historical Record (parsing-only) assertions
are verified and the profile extraction section is skipped with a notice.

Transcript snippet: Brown v. Board of Education, Dec 9, 1952 (public domain).
"""

import os
import sys
import json
import pprint

from transcript_ingestion import ingest_transcript, extract_historical_record

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


def test_parsing_only():
    """Verify Historical Record extraction without touching the API."""
    print("=" * 60)
    print("PART 1 — Historical Record (parsing only, no LLM)")
    print("=" * 60)

    record = extract_historical_record(TRANSCRIPT, LAWYER_NAME)

    print(f"\nExtracted {len(record)} turn(s) for '{LAWYER_NAME}':")
    for i, turn in enumerate(record, 1):
        print(f"\n  [Turn {i}] {turn[:80]}{'...' if len(turn) > 80 else ''}")

    # Assertion 1: at least 3 turns
    assert len(record) >= 3, (
        f"Expected >= 3 turns for {LAWYER_NAME}, got {len(record)}"
    )
    print(f"\n[PASS] Historical Record has {len(record)} turn(s) (>= 3 required)")

    # Assertion 2: verbatim — each expected turn must appear in the record
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record, (
            f"Expected turn not found verbatim in historical_record:\n{expected[:120]!r}"
        )
    print(f"[PASS] All {len(EXPECTED_MARSHALL_TURNS)} expected turns appear verbatim in historical_record")

    return record


def test_full_ingestion():
    """Run the full pipeline (parsing + LLM profile extraction)."""
    print("\n" + "=" * 60)
    print("PART 2 — Full ingestion (parsing + LLM profile)")
    print("=" * 60)

    result = ingest_transcript(TRANSCRIPT, LAWYER_NAME, OPPOSING_NAME)

    print("\nFull result:")
    pprint.pprint(result, width=80, sort_dicts=False)

    # Assertion 1: historical record length
    record = result["historical_record"]
    assert len(record) >= 3, (
        f"Expected >= 3 turns for {LAWYER_NAME}, got {len(record)}"
    )
    print(f"\n[PASS] historical_record has {len(record)} turn(s) (>= 3 required)")

    # Assertion 2: verbatim turns
    for expected in EXPECTED_MARSHALL_TURNS:
        assert expected in record, (
            f"Turn not found verbatim in historical_record:\n{expected[:120]!r}"
        )
    print(f"[PASS] All {len(EXPECTED_MARSHALL_TURNS)} expected Marshall turns appear verbatim")

    # Assertion 3: all 5 profile fields present and non-empty for Frankfurter
    profile = result["profile"]
    assert profile.get("name"), "profile['name'] must be a non-empty string"
    assert profile.get("role"), "profile['role'] must be a non-empty string"
    for field_name in PROFILE_FIELDS:
        value = profile.get(field_name)
        assert isinstance(value, str) and value.strip(), (
            f"profile['{field_name}'] must be a non-empty string, got: {value!r}"
        )
    print(f"[PASS] All 5 profile fields are non-empty strings for '{OPPOSING_NAME}'")

    return result


def main():
    # Always run the parsing-only test
    test_parsing_only()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "\n[SKIP] ANTHROPIC_API_KEY is not set — skipping LLM profile extraction test.\n"
            "       Set the environment variable and re-run to test the full pipeline."
        )
        print("\nAll parsing assertions PASSED.")
        sys.exit(0)

    # Run full ingestion if key is available
    test_full_ingestion()

    print("\nAll assertions PASSED.")


if __name__ == "__main__":
    main()
