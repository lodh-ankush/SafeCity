# core/alerts.py
import time
from typing import List, Deque, Tuple
from collections import deque
from core.schemas import Incident
from core.config import ALERT_MIN, DEDUP_TIME_WINDOW_SEC, SUPPRESS_REPEAT_SEC
from core.utils import jaccard


class AlertQueue:
    """
    Maintains a ranked list of incidents and suppresses duplicates/repeats.
    """

    def __init__(self):
        self.queue: Deque[Incident] = deque(maxlen=500)
        self.last_alert_time_by_type = {}  # type -> unix time

    def is_duplicate(self, inc: Incident) -> bool:
        now = time.time()
        for prev in reversed(self.queue):
            tdiff = now - time.mktime(
                time.strptime(prev.timestamp, "%Y-%m-%d %H:%M:%S")
            )
            if tdiff > DEDUP_TIME_WINDOW_SEC:
                break
            if prev.type == inc.type:
                if prev.raw_text and inc.raw_text:
                    if jaccard(" ".join(prev.raw_text), " ".join(inc.raw_text)) > 0.5:
                        return True
                else:
                    return True
        return False

    def is_suppressed(self, inc: Incident) -> bool:
        now = time.time()
        last = self.last_alert_time_by_type.get(inc.type, 0)
        return (now - last) < SUPPRESS_REPEAT_SEC

    def push(self, inc: Incident) -> Tuple[bool, str]:
        """Returns (accepted, reason)."""
        if inc.fused_score < ALERT_MIN:
            return (False, f"below_threshold:{inc.fused_score:.2f}")
        if self.is_duplicate(inc):
            return (False, "duplicate")
        if self.is_suppressed(inc):
            return (False, "suppressed")
        self.queue.append(inc)
        self.last_alert_time_by_type[inc.type] = time.time()
        return (True, "accepted")

    def topk(self, k=5) -> List[Incident]:
        return sorted(list(self.queue), key=lambda x: x.fused_score, reverse=True)[:k]
