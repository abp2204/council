"""
COUNCIL — Transcript Ingestion Pipeline

Converts a raw SCOTUS oral argument transcript into a Case-ready dict
containing a Historical Record (the arguing lawyer's verbatim turns) and
a Profile (a behavioral fingerprint of the opposing role), using pure regex
parsing for the record and Claude claude-opus-4-7 for the profile.

Usage:
    result = ingest_transcript(raw_text, "MR. MARSHALL", "JUSTICE FRANKFURTER")

Environment:
    ANTHROPIC_API_KEY — required only for profile extraction.
"""

import os
import re
import json


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
        model="claude-opus-4-7",
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
    - Profile extraction calls Claude claude-opus-4-7 and requires ANTHROPIC_API_KEY.
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
