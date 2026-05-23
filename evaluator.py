"""
COUNCIL — Generative Evaluator (Issue #2)

Implements EvaluatorRole: a separate AI role — distinct from the Opposing Role —
that reads the full Session transcript once after SESSION_END and produces a
multi-dimensional Score with generative KeyMoment commentary.

ADR 0001: Evaluator is separate from the Opposing Role, runs cold once per
Session after SESSION_END, reads the full session transcript.

Usage:
    from evaluator import EvaluatorRole
    score = EvaluatorRole().evaluate(transcript)
"""

import json
import os
import re
from dataclasses import dataclass, field

import anthropic

# ── Domain Dataclasses ────────────────────────────────────────────────────────


@dataclass
class KeyMoment:
    """A notable inflection point in the user's argument sequence."""

    turn_number: int   # 1-indexed count of user turns only (not absolute index)
    label: str         # "best_move" | "worst_move" | "deviation_point"
    user_text: str     # Exact user argument text
    commentary: str    # Generative commentary referencing specific content from user_text


@dataclass
class Score:
    """End-of-session scorecard produced by the Evaluator after SESSION_END."""

    legal_soundness: int           # 0–100
    strategic_effectiveness: int   # 0–100
    creativity: int                # 0–100
    key_moments: list[KeyMoment] = field(default_factory=list)  # 3–5 moments


# ── System Prompt ─────────────────────────────────────────────────────────────

_EVALUATOR_SYSTEM_PROMPT = """\
You are the Evaluator for COUNCIL — a "LeetCode for Lawyers" platform where \
users argue real historical court cases against AI opponents.

Your role is strictly post-session: you read the complete session transcript \
once after the session ends and produce a multi-dimensional scorecard. You \
never speak during the case itself and you never inhabit the Opposing Role.

## Scoring Dimensions

Score the user's overall performance on three dimensions, each from 0 to 100:

1. **legal_soundness** (0–100)
   - Are the legal arguments doctrinally correct?
   - Are case citations accurate and relevant?
   - Is the constitutional or statutory reasoning sound?
   - Penalize factual errors (wrong dates, misattributed holdings, invented \
doctrine), irrelevant legal frameworks, and logical non-sequiturs.
   - Reward precise citation of controlling precedent, accurate statement of \
legal standards, and doctrinal coherence across turns.

2. **strategic_effectiveness** (0–100)
   - Does the user respond to the opponent's actual questions and challenges?
   - Do they advance their theory of the case progressively?
   - Do they concede ground wisely, or do they concede unnecessarily?
   - Penalize arguments that ignore the opponent's challenge, pivot without \
addressing the question, or undermine earlier positions.
   - Reward arguments that directly rebut the opponent, build incrementally, \
and demonstrate awareness of the overall theory of the case.

3. **creativity** (0–100)
   - Does the user find novel framings, analogies, or arguments beyond the \
conventional approach?
   - Do they reframe questions effectively?
   - Penalize pure repetition of the same argument, formulaic responses, and \
arguments that add no new angle.
   - Reward novel but legally coherent framings, surprising analogies that \
illuminate rather than obscure, and arguments that reframe the question \
productively.

CRITICAL: Scores must reflect the actual content and quality of the arguments \
in the transcript. Do NOT score based on deviation count, turn count, or any \
metadata. Two sessions with the same number of turns can have very different \
scores if the argument quality differs.

## Key Moments

Identify 3 to 5 key moments from the user's turns. Each key moment must:
- Reference exactly one user turn (numbered 1, 2, 3… counting only user turns \
in order of appearance, NOT absolute transcript line numbers)
- Carry one label: "best_move", "worst_move", or "deviation_point"
- Include the exact user argument text
- Include commentary that is UNIQUE and SPECIFIC to that argument — quote or \
paraphrase actual phrases from the user's text to anchor your commentary. \
Generic filler ("good argument", "could be better") is not acceptable.

Label guidance:
- "best_move": The single strongest argument — most legally sound, most \
strategically effective, or most creative. Quality-based, not positional.
- "worst_move": The weakest argument — legally incorrect, strategically \
counterproductive, or substantively empty. Quality-based, not positional.
- "deviation_point": An argument that departs meaningfully from the historical \
approach, for better or worse (notable whether it works or doesn't).

You may have at most one "best_move" and at most one "worst_move". You may have \
multiple "deviation_point" moments if warranted. Total key moments: 3–5.

## Output Format

Respond with ONLY a JSON object — no preamble, no markdown fences, no \
explanation outside the JSON. Use this exact schema:

{
  "legal_soundness": <integer 0-100>,
  "strategic_effectiveness": <integer 0-100>,
  "creativity": <integer 0-100>,
  "key_moments": [
    {
      "turn_number": <integer, 1-indexed user turn number>,
      "label": <"best_move" | "worst_move" | "deviation_point">,
      "user_text": <exact user argument text as a string>,
      "commentary": <string — specific, generative, references user_text content>
    }
  ]
}

The "key_moments" array must contain between 3 and 5 objects.
"""


# ── Evaluator Role ────────────────────────────────────────────────────────────


class EvaluatorRole:
    """
    Separate AI role that scores a completed Session.

    Runs exactly once per Session, after SESSION_END. Reads the full session
    transcript cold and returns a Score dataclass.

    The transcript is a list of {"speaker": str, "text": str} dicts where
    speaker is typically "opponent" or "user" (or the named roles).
    """

    MODEL = "claude-opus-4-7"

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Export it before running the evaluator."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def _build_transcript_text(self, transcript: list[dict]) -> str:
        """
        Render the transcript as readable text and annotate user turns with
        their 1-indexed user-turn number so the model can reference them.
        """
        lines = []
        user_turn_number = 0
        for entry in transcript:
            speaker = entry.get("speaker", "unknown")
            text = entry.get("text", "")
            # Detect user turns by checking if speaker is not "opponent" / "opposing_role"
            is_user = speaker.lower() not in ("opponent", "opposing_role", "opposing role")
            if is_user:
                user_turn_number += 1
                lines.append(f"[USER TURN {user_turn_number}] {speaker}: {text}")
            else:
                lines.append(f"[OPPONENT] {speaker}: {text}")
        return "\n\n".join(lines)

    def evaluate(self, transcript: list[dict]) -> Score:
        """
        Evaluate a completed Session transcript.

        Args:
            transcript: List of {"speaker": str, "text": str} dicts,
                        alternating between opponent and user turns.

        Returns:
            Score dataclass with legal_soundness, strategic_effectiveness,
            creativity (all 0–100), and key_moments (3–5 KeyMoment objects).
        """
        transcript_text = self._build_transcript_text(transcript)

        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _EVALUATOR_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Please evaluate the following session transcript and return "
                        "your scorecard as a JSON object matching the schema above.\n\n"
                        f"SESSION TRANSCRIPT:\n\n{transcript_text}"
                    ),
                }
            ],
        )

        if not response.content:
            raise RuntimeError("Anthropic API returned an empty content list.")
        raw = response.content[0].text.strip()
        return self._parse_score(raw, transcript)

    def _parse_score(self, raw: str, transcript: list[dict]) -> Score:
        """
        Parse the LLM JSON response into a Score dataclass.
        Handles JSON parse errors gracefully by returning a fallback Score.
        """
        # Strip markdown code fences if the model wrapped the JSON
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Graceful fallback: return a neutral score with an error note
            return Score(
                legal_soundness=50,
                strategic_effectiveness=50,
                creativity=50,
                key_moments=[
                    KeyMoment(
                        turn_number=1,
                        label="deviation_point",
                        user_text="(parse error — see evaluator logs)",
                        commentary=(
                            f"The evaluator could not parse its own response. "
                            f"Raw output starts with: {raw[:120]!r}. "
                            f"JSONDecodeError: {exc}"
                        ),
                    ),
                    KeyMoment(
                        turn_number=1,
                        label="best_move",
                        user_text="(parse error fallback)",
                        commentary="Evaluator parse error; scores are neutral defaults.",
                    ),
                    KeyMoment(
                        turn_number=1,
                        label="worst_move",
                        user_text="(parse error fallback)",
                        commentary="Evaluator parse error; scores are neutral defaults.",
                    ),
                ],
            )

        # Extract scores with bounds clamping; guard against JSON null
        def _safe_score(val, default: int = 50) -> int:
            return max(0, min(100, int(val if val is not None else default)))

        legal_soundness = _safe_score(data.get("legal_soundness"))
        strategic_effectiveness = _safe_score(data.get("strategic_effectiveness"))
        creativity = _safe_score(data.get("creativity"))

        # Build user-turn index for fast lookup (1-indexed)
        user_turns: list[str] = []
        for entry in transcript:
            speaker = entry.get("speaker", "")
            if speaker.lower() not in ("opponent", "opposing_role", "opposing role"):
                user_turns.append(entry.get("text", ""))

        key_moments: list[KeyMoment] = []
        for km in data.get("key_moments", []):
            raw_turn = km.get("turn_number", 1)
            turn_number = int(raw_turn if raw_turn is not None else 1)
            label = km.get("label", "deviation_point")
            user_text = km.get("user_text", "")
            commentary = km.get("commentary", "")

            # If user_text is missing, try to recover from the turn number
            if not user_text and 1 <= turn_number <= len(user_turns):
                user_text = user_turns[turn_number - 1]

            # Clamp turn_number to valid range
            turn_number = max(1, min(turn_number, max(len(user_turns), 1)))

            # Validate label
            if label not in ("best_move", "worst_move", "deviation_point"):
                label = "deviation_point"

            key_moments.append(
                KeyMoment(
                    turn_number=turn_number,
                    label=label,
                    user_text=user_text,
                    commentary=commentary,
                )
            )

        # Enforce 3–5 key moments (trim or pad if needed)
        key_moments = key_moments[:5]
        while len(key_moments) < 3:
            fallback_turn = len(key_moments) + 1
            fallback_text = user_turns[min(fallback_turn - 1, len(user_turns) - 1)]
            key_moments.append(
                KeyMoment(
                    turn_number=fallback_turn,
                    label="deviation_point",
                    user_text=fallback_text,
                    commentary="(Evaluator produced fewer than 3 key moments; this entry was added as a fallback.)",
                )
            )

        return Score(
            legal_soundness=legal_soundness,
            strategic_effectiveness=strategic_effectiveness,
            creativity=creativity,
            key_moments=key_moments,
        )
