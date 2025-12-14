from datetime import date, timedelta
from models import MemoryItem, Feedback


MIN_EASE = 1.3
MIN_CONFIDENCE = 0.2
MAX_CONFIDENCE = 1.0


def review(item: MemoryItem, feedback: Feedback, today: date) -> MemoryItem:
    if feedback == Feedback.FORGOT:
        item.repetitions = 0
        item.ease = max(MIN_EASE, item.ease - 0.2)
        item.confidence = max(MIN_CONFIDENCE, item.confidence - 0.2)
        item.interval = 1.0

    elif feedback == Feedback.FUZZY:
        item.repetitions += 1
        item.ease -= 0.05
        item.confidence = min(MAX_CONFIDENCE, item.confidence + 0.05)
        item.interval = max(1.0, item.interval * 1.2)

    elif feedback == Feedback.MASTERED:
        item.repetitions += 1
        item.ease += 0.1
        item.confidence = min(MAX_CONFIDENCE, item.confidence + 0.1)
        item.interval = item.interval * item.ease

    item.last_review = today
    item.next_review = today + timedelta(days=round(item.interval))

    return item
