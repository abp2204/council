from __future__ import annotations

import logging
from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.75
MODEL_NAME = "all-MiniLM-L6-v2"


@dataclass
class DetectionResult:
    is_deviation: bool
    similarity_score: float  # 0.0–1.0


class DeviationDetector:
    def __init__(self) -> None:
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def detect(
        self,
        user_text: str,
        turn_index: int,
        historical_record: list[str],
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> tuple[bool, float]:
        """Returns (is_deviation, similarity_score)."""
        if not user_text or not user_text.strip():
            logger.debug("empty user_text, skipping deviation check")
            return (False, 1.0)
        if turn_index >= len(historical_record):
            logger.debug(
                "turn_index %d beyond historical record length %d",
                turn_index,
                len(historical_record),
            )
            return (False, 1.0)

        historical = historical_record[turn_index]
        if not historical or not historical.strip():
            return (True, 0.0)

        embeddings = self._get_model().encode([user_text, historical])
        score = min(1.0, float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]))
        is_deviation = score < threshold
        logger.debug(
            "deviation check: score=%.3f threshold=%.3f is_deviation=%s",
            score,
            threshold,
            is_deviation,
        )
        return (is_deviation, score)

    def detect_detailed(
        self,
        user_text: str,
        turn_index: int,
        historical_record: list[str],
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> DetectionResult:
        is_deviation, score = self.detect(user_text, turn_index, historical_record, threshold)
        return DetectionResult(is_deviation=is_deviation, similarity_score=score)
