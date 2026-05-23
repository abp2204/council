"""
COUNCIL — Re-ingest existing cases with synthesized system prompts.

Run this script after setting ANTHROPIC_API_KEY to replace the hand-authored
system prompts in brown.json and gideon.json with LLM-synthesized ones derived
from each case's existing Profile data.

Usage:
    python3 reingest_cases.py

The script reads the existing case JSON, synthesizes a new system_prompt from
the opposing_role data (treated as the Profile), writes the result in-place,
and prints a confirmation.
"""

import json
import os
import sys
from pathlib import Path

from transcript_ingestion import synthesize_system_prompt

CASES_DIR = Path(__file__).parent / "cases"

CASES = [
    "brown",
    "gideon",
]

PROFILE_FIELDS = [
    "argumentation_patterns",
    "signature_questions_or_objections",
    "rhetorical_habits",
    "tone_and_cadence",
]


def _opposing_role_to_profile(opposing_role: dict) -> dict:
    """
    Build a Profile dict from an existing opposing_role block.
    The opposing_role stores the same behavioural fields as the Profile.
    """
    profile = {
        "name": opposing_role["name"],
        "role": "opposing",
    }
    for field in PROFILE_FIELDS:
        profile[field] = opposing_role.get(field, "")
    return profile


def reingest(case_id: str) -> None:
    path = CASES_DIR / f"{case_id}.json"
    with open(path) as f:
        case = json.load(f)

    opposing = case["opposing_role"]
    profile = _opposing_role_to_profile(opposing)

    missing = [f for f in PROFILE_FIELDS if not profile.get(f)]
    if missing:
        print(
            f"WARNING: {case_id}.json opposing_role is missing profile fields: {missing}. "
            "Skipping synthesis — please run the full ingestion pipeline instead.",
            file=sys.stderr,
        )
        return

    print(f"Synthesizing system prompt for {case_id} ({opposing['name']})...")
    system_prompt = synthesize_system_prompt(profile)
    opposing["system_prompt"] = system_prompt
    opposing["system_prompt_source"] = "synthesized"

    with open(path, "w") as f:
        json.dump(case, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Updated: {path}")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ERROR: ANTHROPIC_API_KEY is not set. "
            "Set it and re-run this script to synthesize system prompts.",
            file=sys.stderr,
        )
        sys.exit(1)

    for case_id in CASES:
        reingest(case_id)

    print("\nRe-ingestion complete.")


if __name__ == "__main__":
    main()
