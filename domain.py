from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str  # "user" | "opponent"
    text: str
    deviation: bool = False


@dataclass
class KeyMoment:
    turn: int
    label: str   # "best_move" | "worst_move" | "deviation_point"
    user_text: str
    commentary: str


@dataclass
class Score:
    legal_soundness: int
    strategic_effectiveness: int
    creativity: int
    key_moments: list[KeyMoment] = field(default_factory=list)


@dataclass
class MoveResult:
    response: str
    closes: bool
    deviation: bool
