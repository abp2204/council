"""
COUNCIL — Re-ingest existing cases with synthesized system prompts.

Run this script to replace the hand-authored system prompts in brown.json
and gideon.json with LLM-synthesized ones derived from each case's existing
Profile data. Uses local Ollama (gemma4) — no API key required.

Usage:
    python3 reingest_cases.py

Requires Ollama running locally: ollama serve
"""

import json
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
    for case_id in CASES:
        reingest(case_id)
    print("\nRe-ingestion complete.")


if __name__ == "__main__":
    main()
