"""
COUNCIL — Generative Evaluator (Issue #2, #19)

Implements EvaluatorRole: a separate AI role — distinct from the Opposing Role —
that reads the full Session transcript once after SESSION_END and produces a
multi-dimensional Score with generative KeyMoment commentary.

ADR 0001: Evaluator is separate from the Opposing Role, runs cold once per
Session after SESSION_END, reads the full session transcript.

Usage:
    from evaluator import EvaluatorRole
    score = EvaluatorRole().evaluate(turns, historical_record=..., case=...)
"""

from __future__ import annotations

import json
import re

import ollama

from domain import KeyMoment, Score, Turn


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

Arguments are spoken advocacy, not legal briefs — evaluate the register accordingly.

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


# ── Public Parse Function ─────────────────────────────────────────────────────


def parse_score(raw: str, turns: list[Turn]) -> Score:
    """
    Parse an LLM JSON response string into a Score dataclass.

    Takes the raw text returned by the evaluator model and the session's Turn
    list (used to recover missing user_text fields and clamp turn numbers).
    Handles JSON parse errors gracefully by returning a fallback Score.

    Args:
        raw: Raw string from the LLM response (may contain markdown fences).
        turns: The session's Turn list; used to resolve user turn text.

    Returns:
        A fully populated Score with 3–5 KeyMoment objects.
    """
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    user_texts: list[str] = [t.text for t in turns if t.role == "user"]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return Score(
            legal_soundness=50,
            strategic_effectiveness=50,
            creativity=50,
            key_moments=[
                KeyMoment(
                    turn=1,
                    label="deviation_point",
                    user_text="(parse error — see evaluator logs)",
                    commentary=(
                        f"The evaluator could not parse its own response. "
                        f"Raw output starts with: {raw[:120]!r}. "
                        f"JSONDecodeError: {exc}"
                    ),
                ),
                KeyMoment(
                    turn=1,
                    label="best_move",
                    user_text="(parse error fallback)",
                    commentary="Evaluator parse error; scores are neutral defaults.",
                ),
                KeyMoment(
                    turn=1,
                    label="worst_move",
                    user_text="(parse error fallback)",
                    commentary="Evaluator parse error; scores are neutral defaults.",
                ),
            ],
        )

    def _safe_score(val, default: int = 50) -> int:
        return max(0, min(100, int(val if val is not None else default)))

    legal_soundness = _safe_score(data.get("legal_soundness"))
    strategic_effectiveness = _safe_score(data.get("strategic_effectiveness"))
    creativity = _safe_score(data.get("creativity"))

    key_moments: list[KeyMoment] = []
    for km in data.get("key_moments", []):
        raw_turn = km.get("turn_number", 1)
        turn_number = int(raw_turn if raw_turn is not None else 1)
        label = km.get("label", "deviation_point")
        user_text = km.get("user_text", "")
        commentary = km.get("commentary", "")

        if not user_text and 1 <= turn_number <= len(user_texts):
            user_text = user_texts[turn_number - 1]

        turn_number = max(1, min(turn_number, max(len(user_texts), 1)))

        if label not in ("best_move", "worst_move", "deviation_point"):
            label = "deviation_point"

        key_moments.append(
            KeyMoment(
                turn=turn_number,
                label=label,
                user_text=user_text,
                commentary=commentary,
            )
        )

    key_moments = key_moments[:5]
    while len(key_moments) < 3:
        fallback_turn = len(key_moments) + 1
        fallback_text = user_texts[min(fallback_turn - 1, len(user_texts) - 1)] if user_texts else ""
        key_moments.append(
            KeyMoment(
                turn=fallback_turn,
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


# ── Evaluator Role ────────────────────────────────────────────────────────────


class EvaluatorRole:
    """
    Separate AI role that scores a completed Session.

    Runs exactly once per Session, after SESSION_END. Reads the full session
    transcript cold and returns a Score dataclass.
    """

    MODEL = "qwen2.5:14b"

    def __init__(self) -> None:
        pass

    def _build_transcript_text(self, turns: list[Turn]) -> str:
        """
        Render the turn list as readable text, annotating user turns with
        their 1-indexed user-turn number so the model can reference them.
        """
        lines = []
        user_turn_number = 0
        for turn in turns:
            if turn.role == "user":
                user_turn_number += 1
                lines.append(f"[USER TURN {user_turn_number}] user: {turn.text}")
            else:
                lines.append(f"[OPPONENT] opponent: {turn.text}")
        return "\n\n".join(lines)

    def evaluate(
        self,
        turns: list[Turn],
        historical_record: list[str] | None = None,
        case: dict | None = None,
    ) -> Score:
        """
        Evaluate a completed Session.

        Args:
            turns: The session's Turn list from SessionEngine.
            historical_record: Optional list of historical record strings.
            case: Optional case dict for additional context.

        Returns:
            Score with legal_soundness, strategic_effectiveness, creativity
            (all 0–100), and key_moments (3–5 KeyMoment objects).
        """
        transcript_text = self._build_transcript_text(turns)

        historical_text = "\n".join(
            f"{i + 1}. {r}" for i, r in enumerate(historical_record or [])
        )

        user_content = (
            f"HISTORICAL RECORD:\n{historical_text}\n\n"
            f"SESSION TRANSCRIPT:\n\n{transcript_text}\n\n"
            "Please evaluate and return your scorecard as a JSON object."
        )

        response = ollama.chat(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": _EVALUATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )

        raw = response.message.content.strip()
        return parse_score(raw, turns)
