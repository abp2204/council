"""
COUNCIL — Semantic Deviation Detection

Detects whether a user's Move is a Deviation from the historical reference
by asking Claude to classify whether the two legal arguments make the same
substantive point.

A Deviation is when the user argues a meaningfully different point than the
historical lawyer — not just uses different words for the same point.
"""

import json
import os
import re
from dataclasses import dataclass

import anthropic


# ── Data Structures ────────────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """Result of a single deviation detection call."""
    is_deviation: bool
    same_point: bool
    confidence: float
    raw_response: str


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a legal argument classifier for COUNCIL, a legal education platform.

Your task is to determine whether two legal arguments are making the same
substantive point — even if they use different vocabulary, framing, or
rhetorical style.

Focus on the SUBSTANCE of the legal claim, not the surface wording:
- "stare decisis cannot shield a constitutionally infirm decision" and
  "Plessy was wrongly decided" are the SAME point (both argue Plessy
  should be overruled).
- "I concede separate but equal may be constitutional" and "Plessy was
  wrongly decided and must be overturned" are DIFFERENT points (one
  accepts the doctrine, one rejects it).

Rules:
1. If either argument is empty, punctuation-only, or contains no discernible
   legal claim, they cannot be aligned — treat as NOT the same point.
2. Arguments in different languages may still make the same point — evaluate
   the meaning, not the language.
3. A very short argument (e.g., a single word) may or may not align — use
   reasonable inference about its most plausible meaning in the legal context.

Respond ONLY with a JSON object in this exact format:
{"same_point": true, "confidence": 0.9}

Where:
- same_point: true if both arguments make the same substantive legal claim
- confidence: float from 0.0 to 1.0 representing your certainty
"""


# ── Detector ───────────────────────────────────────────────────────────────────

class DeviationDetector:
    """
    Detects whether a user's Move is a Deviation from the historical reference.

    Uses the Claude API with a semantic classification prompt to determine
    whether two legal arguments make the same substantive point, regardless
    of vocabulary differences.

    A Move is a Deviation when same_point == False, or when the confidence
    of same_point being True is below the threshold.
    """

    def __init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY environment variable is not set."
            )
        self._client = anthropic.Anthropic(api_key=api_key)

    def detect(
        self,
        user_move: str,
        historical_reference: str,
        threshold: float = 0.75,
    ) -> bool:
        """
        Returns True if user_move is a Deviation from historical_reference.

        A Deviation occurs when the user is making a meaningfully different
        substantive legal argument — not merely using different vocabulary.

        Args:
            user_move: The user's argument text for this turn.
            historical_reference: The historical lawyer's argument for this turn.
            threshold: Minimum confidence required for same_point=True to be
                       treated as "not a deviation". Default 0.75.

        Returns:
            True if the move is a Deviation, False if it follows the same path.
        """
        result = self._classify(user_move, historical_reference, threshold)
        return result.is_deviation

    def detect_detailed(
        self,
        user_move: str,
        historical_reference: str,
        threshold: float = 0.75,
    ) -> DetectionResult:
        """
        Returns a DetectionResult with full details.

        Useful for debugging and the Evaluator's deviation delta computation.
        """
        return self._classify(user_move, historical_reference, threshold)

    def _is_empty_or_noise(self, text: str) -> bool:
        """Returns True if the text contains no discernible legal claim."""
        if not text or not text.strip():
            return True
        # Only punctuation/whitespace — no alphanumeric content
        stripped = text.strip()
        if not re.search(r"[a-zA-Z0-9À-ɏ一-鿿]", stripped):
            return True
        return False

    def _classify(
        self,
        user_move: str,
        historical_reference: str,
        threshold: float,
    ) -> DetectionResult:
        """
        Calls the Claude API to classify whether the two arguments are the same.

        On any parse or API error, defaults to is_deviation=True (safer).
        """
        # Fast-path: empty/noise inputs cannot be aligned
        if self._is_empty_or_noise(user_move) or self._is_empty_or_noise(
            historical_reference
        ):
            return DetectionResult(
                is_deviation=True,
                same_point=False,
                confidence=1.0,
                raw_response="(fast-path: empty or noise input)",
            )

        user_content = (
            f"Argument A (user's move):\n{user_move}\n\n"
            f"Argument B (historical reference):\n{historical_reference}\n\n"
            "Are these two legal arguments making the same substantive point?"
        )

        try:
            response = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=64,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": user_content},
                ],
            )
            raw = response.content[0].text.strip()
        except Exception as exc:
            # API error — default to is_deviation=True (safer)
            return DetectionResult(
                is_deviation=True,
                same_point=False,
                confidence=0.0,
                raw_response=f"(API error: {exc})",
            )

        return self._parse_response(raw, threshold)

    def _parse_response(
        self, raw: str, threshold: float
    ) -> DetectionResult:
        """
        Parses the JSON classification response.

        On parse failure, defaults to is_deviation=True.
        """
        try:
            # Extract the JSON object from the response regardless of surrounding text
            # Handles: bare JSON, ```json fences, explanatory preludes, uppercase ```JSON
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not json_match:
                raise json.JSONDecodeError("No JSON object found", raw, 0)
            data = json.loads(json_match.group())

            raw_same_point = data.get("same_point", False)
            # Guard against the model returning the string "false"/"true" instead of a bool
            if isinstance(raw_same_point, str):
                same_point = raw_same_point.strip().lower() == "true"
            else:
                same_point = bool(raw_same_point)
            confidence: float = float(data.get("confidence", 0.0))

            # A move is a Deviation when:
            #   - same_point is False, OR
            #   - same_point is True but confidence is below threshold
            if same_point and confidence >= threshold:
                is_deviation = False
            else:
                is_deviation = True

            return DetectionResult(
                is_deviation=is_deviation,
                same_point=same_point,
                confidence=confidence,
                raw_response=raw,
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # Parse error — default to is_deviation=True (safer)
            return DetectionResult(
                is_deviation=True,
                same_point=False,
                confidence=0.0,
                raw_response=raw,
            )
