"""
COUNCIL — Transcript Ingestion Pipeline

Converts a raw SCOTUS oral argument transcript into a Case-ready dict
containing a Historical Record (the arguing lawyer's verbatim turns) and
a Profile (a behavioral fingerprint of the opposing role), using pure regex
parsing for the record and Claude claude-sonnet-4-6 for the profile.

Usage (library):
    result = ingest_transcript(raw_text, "MR. MARSHALL", "JUSTICE FRANKFURTER")

Usage (CLI):
    council-ingest <transcript.txt> --lawyer "MR. MARSHALL" --opponent "JUSTICE FRANKFURTER"
    python -m transcript_ingestion <transcript.txt> --lawyer "MR. MARSHALL" --opponent "JUSTICE FRANKFURTER"

Environment:
    ANTHROPIC_API_KEY — required for profile extraction and system prompt synthesis.
"""

import os
import re
import json
import argparse
import sys
from pathlib import Path


# ── Speaker parsing ────────────────────────────────────────────────────────────

# Matches labels like: JUSTICE FRANKFURTER:  MR. MARSHALL:  THE CHIEF JUSTICE:
# Pattern: one or more ALL-CAPS words (allowing dots for MR./MRS./DR.) followed
# by a colon.  We anchor at the start of a line or after a newline.
_SPEAKER_LABEL_RE = re.compile(
    r"(?:^|\n)"                    # start of string or newline
    r"([A-Z][A-Z\s.']+?)"          # speaker label (greedy-shy: stop at colon)
    r":"                           # literal colon
    r"(?=\s|$)",                   # followed by whitespace or end-of-line
    re.MULTILINE,
)


def _parse_turns(raw_text: str) -> list[tuple[str, str]]:
    """
    Parse the transcript into a list of (speaker_label, turn_text) pairs.

    Speaker labels are normalised to stripped uppercase.  Turn text is the
    verbatim content between one label and the next (or end of string),
    with leading/trailing whitespace stripped.
    """
    # Find every speaker-label match and record its span.
    matches = list(_SPEAKER_LABEL_RE.finditer(raw_text))
    if not matches:
        return []

    turns: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        label = match.group(1).strip().upper()
        # Turn text starts after the colon (end of match)
        text_start = match.end()
        # Turn text ends at the start of the next speaker label, or EOF
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        turn_text = raw_text[text_start:text_end].strip()
        turns.append((label, turn_text))

    return turns


def _collect_turns_for(raw_text: str, speaker_name: str) -> list[str]:
    """
    Return, in order, all verbatim turn texts attributed to *speaker_name*.
    Comparison is case-insensitive; both sides are stripped and uppercased.
    """
    target = speaker_name.strip().upper()
    return [text for label, text in _parse_turns(raw_text) if label == target]


# ── Historical Record ──────────────────────────────────────────────────────────

def extract_historical_record(raw_text: str, lawyer_name: str) -> list[str]:
    """
    Pure-parsing extraction — no LLM required.

    Returns the arguing lawyer's turns verbatim, in sequence, stripped of
    leading/trailing whitespace.
    """
    return _collect_turns_for(raw_text, lawyer_name)


# ── Profile extraction (LLM-powered) ──────────────────────────────────────────

_PROFILE_SYSTEM_PROMPT = """\
You are an expert legal analyst specialising in appellate advocacy and judicial
behaviour.  You will be given the verbatim turns of a named participant from a
US federal appellate oral argument.

Your task is to produce a structured behavioural profile that captures how this
participant argues, questions, and reasons — a fingerprint that could be used to
faithfully role-play them in an AI simulation.

Return ONLY a single JSON object (no markdown fences, no preamble) with exactly
these four string fields:

{
  "argumentation_patterns": "<how they build and sequence arguments or questions>",
  "signature_questions_or_objections": "<recurring question types, gotchas, or lines of attack>",
  "rhetorical_habits": "<use of hypotheticals, historical references, interruptions, rhetoric>",
  "tone_and_cadence": "<formal/informal, probing/deferential, quick/deliberate, etc.>"
}

Be specific and grounded in the actual text provided.  Avoid generic descriptions.
Each field must be a non-empty string.
"""

_PROFILE_USER_TEMPLATE = """\
Below are the verbatim turns of {name} in this proceeding.  Produce their
behavioural profile as described in the system instructions.

TURNS:
{turns_block}
"""


def extract_profile(
    raw_text: str,
    opposing_role_name: str,
) -> dict:
    """
    LLM-powered profile extraction.

    Collects all turns attributed to *opposing_role_name*, sends them to
    claude-opus-4-7 with a cached system prompt, and returns a profile dict
    with all five required fields.

    Raises:
        EnvironmentError: if ANTHROPIC_API_KEY is not set.
        ValueError: if the LLM response cannot be parsed as valid JSON with
                    the required fields.
    """
    import anthropic  # deferred import so parsing still works without the SDK

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Profile extraction requires a valid Anthropic API key."
        )

    turns = _collect_turns_for(raw_text, opposing_role_name)
    if not turns:
        raise ValueError(
            f"No turns found for '{opposing_role_name}' in the transcript. "
            "Check the speaker name and transcript format."
        )

    turns_block = "\n\n".join(
        f"[Turn {i + 1}]\n{text}" for i, text in enumerate(turns)
    )
    user_content = _PROFILE_USER_TEMPLATE.format(
        name=opposing_role_name.strip().title(),
        turns_block=turns_block,
    )

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _PROFILE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_content},
        ],
    )

    if not message.content or not hasattr(message.content[0], "text"):
        raise ValueError(
            f"Unexpected API response: content is empty or not a text block. "
            f"stop_reason={message.stop_reason!r}"
        )
    raw_response = message.content[0].text.strip()

    # Strip optional markdown code fences if the model emits them despite instructions
    if raw_response.startswith("```"):
        raw_response = re.sub(r"^```[a-z]*\n?", "", raw_response)
        raw_response = re.sub(r"\n?```$", "", raw_response)
        raw_response = raw_response.strip()

    try:
        profile_data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON response: {raw_response[:200]!r}"
        ) from exc

    required_fields = {
        "argumentation_patterns",
        "signature_questions_or_objections",
        "rhetorical_habits",
        "tone_and_cadence",
    }
    missing = required_fields - set(profile_data.keys())
    if missing:
        raise ValueError(
            f"LLM profile response is missing required fields: {missing}. "
            f"Got: {list(profile_data.keys())}"
        )

    for f_name in required_fields:
        if not isinstance(profile_data[f_name], str) or not profile_data[f_name].strip():
            raise ValueError(
                f"Profile field '{f_name}' must be a non-empty string. "
                f"Got: {profile_data[f_name]!r}"
            )

    return {
        "name": opposing_role_name.strip(),
        "role": "opposing",
        "argumentation_patterns": profile_data["argumentation_patterns"],
        "signature_questions_or_objections": profile_data["signature_questions_or_objections"],
        "rhetorical_habits": profile_data["rhetorical_habits"],
        "tone_and_cadence": profile_data["tone_and_cadence"],
    }


# ── System prompt synthesis (LLM-powered) ─────────────────────────────────────

_SYNTHESIS_SYSTEM = """\
You are an expert prompt engineer specialising in AI role-play simulations for
legal training.  Given a behavioural profile of a historical legal participant,
produce a system prompt that will make an AI faithfully embody that participant
during an oral argument simulation.

The generated system prompt MUST include ALL of the following:
1. The persona's name and role (from the profile).
2. Each of the four behavioural fields verbatim or closely paraphrased:
   argumentation_patterns, signature_questions_or_objections,
   rhetorical_habits, tone_and_cadence.
3. The JSON output contract exactly as written:
   {"response": str, "closes": bool}
4. An explicit prohibition: the persona must NEVER score, rate, evaluate,
   or break character during a session.
5. A session-close rule: close after raising all main topics at least once
   AND at least 3 user turns have occurred.

Return ONLY the finished system prompt text — no preamble, no markdown fences,
no meta-commentary about what you have done.
"""

_SYNTHESIS_USER_TEMPLATE = """\
Produce a system prompt for this participant profile:

{profile_json}
"""


def synthesize_system_prompt(profile: dict) -> str:
    """
    Generate a system prompt from a behavioural Profile dict.

    Calls Claude claude-sonnet-4-6 with a cached instruction system prompt,
    passing the profile as JSON in the user message.

    Raises:
        EnvironmentError: if ANTHROPIC_API_KEY is not set.
        ValueError: if the response is empty or does not contain the required
                    output contract string.
    """
    import anthropic  # deferred import so parsing still works without the SDK

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "System prompt synthesis requires a valid Anthropic API key."
        )

    user_content = _SYNTHESIS_USER_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2)
    )

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": _SYNTHESIS_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_content},
        ],
    )

    if not message.content or not hasattr(message.content[0], "text"):
        raise ValueError(
            f"Unexpected API response: content is empty or not a text block. "
            f"stop_reason={message.stop_reason!r}"
        )

    system_prompt = message.content[0].text.strip()

    if not system_prompt:
        raise ValueError("synthesize_system_prompt returned an empty string.")

    if '{"response":' not in system_prompt and '"response":' not in system_prompt:
        raise ValueError(
            "Generated system prompt is missing the required JSON output contract "
            '({"response": str, "closes": bool}).'
        )

    return system_prompt


# ── Public API ─────────────────────────────────────────────────────────────────

def ingest_transcript(
    raw_text: str,
    lawyer_name: str,
    opposing_role_name: str,
) -> dict:
    """
    Ingest a raw SCOTUS oral argument transcript and return a Case-ready dict.

    Parameters
    ----------
    raw_text : str
        The full verbatim transcript text.  Speaker turns must be labelled with
        ALL-CAPS names followed by a colon (e.g. ``JUSTICE FRANKFURTER:``).
    lawyer_name : str
        The speaker label of the arguing lawyer whose turns form the Historical
        Record (e.g. ``"MR. MARSHALL"``).  Case-insensitive.
    opposing_role_name : str
        The speaker label of the opposing participant whose turns are profiled
        by the LLM (e.g. ``"JUSTICE FRANKFURTER"``).  Case-insensitive.

    Returns
    -------
    dict
        {
            "historical_record": ["turn text 1", "turn text 2", ...],
            "profile": {
                "name": str,
                "role": str,
                "argumentation_patterns": str,
                "signature_questions_or_objections": str,
                "rhetorical_habits": str,
                "tone_and_cadence": str,
            }
        }

    Notes
    -----
    - Historical Record extraction is pure parsing; no API key required.
    - Profile extraction calls Claude claude-sonnet-4-6 and requires ANTHROPIC_API_KEY.
    """
    historical_record = extract_historical_record(raw_text, lawyer_name)
    if not historical_record:
        raise ValueError(
            f"No turns found for lawyer '{lawyer_name}' in the transcript. "
            "Check the speaker name and transcript format."
        )
    profile = extract_profile(raw_text, opposing_role_name)

    return {
        "historical_record": historical_record,
        "profile": profile,
    }


# ── Case JSON schema validation ────────────────────────────────────────────────

_REQUIRED_CASE_FIELDS = ["id", "title", "historical_record"]
_REQUIRED_OPPOSING_FIELDS = ["name", "system_prompt", "mock_probes", "mock_close"]


def _validate_case(case: dict) -> None:
    """
    Validate a Case dict against the required schema.

    Raises:
        SystemExit: with a descriptive error message and exit code 1 if any
                    required field is missing.
    """
    missing_top = [f for f in _REQUIRED_CASE_FIELDS if f not in case]
    if missing_top:
        print(
            f"ERROR: Case JSON is missing required top-level fields: {missing_top}",
            file=sys.stderr,
        )
        sys.exit(1)

    opposing = case.get("opposing_role", {})
    missing_opp = [f for f in _REQUIRED_OPPOSING_FIELDS if f not in opposing]
    if missing_opp:
        print(
            f"ERROR: opposing_role is missing required fields: {missing_opp}",
            file=sys.stderr,
        )
        sys.exit(1)


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="council-ingest",
        description=(
            "Ingest a SCOTUS oral argument transcript and produce a Case JSON file."
        ),
    )
    parser.add_argument("transcript_file", help="Path to the raw transcript .txt file")
    parser.add_argument(
        "--lawyer",
        required=True,
        metavar="NAME",
        help='Speaker label for the arguing lawyer, e.g. "MR. MARSHALL"',
    )
    parser.add_argument(
        "--opponent",
        metavar="NAME",
        help='Speaker label for a single opposing participant, e.g. "JUSTICE FRANKFURTER"',
    )
    parser.add_argument(
        "--all-opponents",
        action="store_true",
        help=(
            "Extract a Profile for every named participant who is not the lawyer. "
            "When set, --opponent is ignored and the first extracted profile is used "
            "for the output Case."
        ),
    )
    parser.add_argument(
        "--case-id",
        metavar="ID",
        help=(
            "Identifier for the output case (used as filename). "
            "Defaults to the transcript filename stem."
        ),
    )
    parser.add_argument(
        "--title",
        metavar="TITLE",
        help="Human-readable case title. Defaults to the case ID.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Case JSON to stdout without writing to disk.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    transcript_path = Path(args.transcript_file)
    if not transcript_path.exists():
        print(f"ERROR: Transcript file not found: {transcript_path}", file=sys.stderr)
        sys.exit(1)

    raw_text = transcript_path.read_text(encoding="utf-8")
    case_id = args.case_id or transcript_path.stem
    title = args.title or case_id

    if args.all_opponents:
        turns = _parse_turns(raw_text)
        lawyer_upper = args.lawyer.strip().upper()
        seen: dict[str, bool] = {}
        opponents = []
        for label, _ in turns:
            if label != lawyer_upper and label not in seen:
                seen[label] = True
                opponents.append(label)
        if not opponents:
            print(
                f"ERROR: No opponent speakers found in transcript (lawyer={args.lawyer!r}).",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Found {len(opponents)} opponent(s): {', '.join(opponents)}")
        profiles = {}
        for opp in opponents:
            print(f"Extracting profile for: {opp}")
            profiles[opp] = extract_profile(raw_text, opp)
        primary_opp = opponents[0]
        profile = profiles[primary_opp]
    else:
        if not args.opponent:
            print(
                "ERROR: --opponent NAME is required unless --all-opponents is set.",
                file=sys.stderr,
            )
            sys.exit(1)
        profile = extract_profile(raw_text, args.opponent)

    historical_record = extract_historical_record(raw_text, args.lawyer)
    if not historical_record:
        print(
            f"ERROR: No turns found for lawyer '{args.lawyer}' in the transcript.",
            file=sys.stderr,
        )
        sys.exit(1)

    system_prompt = synthesize_system_prompt(profile)

    case = {
        "id": case_id,
        "title": title,
        "historical_record": historical_record,
        "opposing_role": {
            "name": profile["name"],
            "system_prompt": system_prompt,
            "mock_probes": [],
            "mock_close": "",
        },
    }

    _validate_case(case)

    output = json.dumps(case, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(output)
        return

    out_path = Path(__file__).parent / "cases" / f"{case_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
