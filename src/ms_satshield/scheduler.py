"""Queue mapping for mitigation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

from .config import QueueConfig


@dataclass
class QueueMapping:
    thresholds: List[float]


class QueueMapper:
    def __init__(self, config: QueueConfig) -> None:
        self.config = config
        self._mapping = QueueMapping(thresholds=[])

    def update(self, scores: Iterable[float]) -> None:
        if self.config.mapping == "quantile":
            self._mapping.thresholds = _quantile_thresholds(
                list(scores), self.config.num_queues
            )
        else:
            self._mapping.thresholds = []

    def map_score(self, score: float) -> int:
        if self.config.mapping == "quantile":
            for idx, thr in enumerate(self._mapping.thresholds):
                if score <= thr:
                    return idx
            return self.config.num_queues - 1
        return _sigmoid_bucket(score, self.config.num_queues)


def _quantile_thresholds(scores: List[float], num_queues: int) -> List[float]:
    if not scores:
        return []
    scores.sort()
    thresholds = []
    for q in range(1, num_queues):
        idx = int(q * len(scores) / num_queues)
        thresholds.append(scores[min(idx, len(scores) - 1)])
    return thresholds


def _sigmoid_bucket(score: float, num_queues: int) -> int:
    k = 6.0
    s = 1.0 / (1.0 + math.exp(-k * (score - 0.5)))
    return min(num_queues - 1, max(0, int(s * (num_queues - 1))))
