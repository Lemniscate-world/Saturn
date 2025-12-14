from dataclasses import dataclass
from datetime import date
from enum import Enum


class Feedback(Enum):
    FORGOT = "FORGOT"
    FUZZY = "FUZZY"
    MASTERED = "MASTERED"


@dataclass
class MemoryItem:
    id: str
    source: str
    note_path: str
    block_ref: str | None

    interval: float = 1.0
    ease: float = 2.5
    confidence: float = 0.5
    repetitions: int = 0

    last_review: date | None = None
    next_review: date | None = None
