"""Scoring utilities for multi-signature detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .config import ScoreConfig


@dataclass(frozen=True)
class NormStats:
    rate_p99: float
    fanout_p99: float
    persist_max: float


class ScoreModel:
    def __init__(self, config: ScoreConfig) -> None:
        self.config = config

    def compute_stats(
        self,
        rates: Iterable[float],
        fanouts: Iterable[float],
        persists: Iterable[float],
    ) -> NormStats:
        return NormStats(
            rate_p99=_percentile(rates, 0.99),
            fanout_p99=_percentile(fanouts, 0.99),
            persist_max=max(persists, default=1.0),
        )

    def score(self, rate: float, fanout: float, persist: float, stats: NormStats) -> float:
        nr = _normalize(rate, stats.rate_p99)
        nf = _normalize(fanout, stats.fanout_p99)
        np = _normalize(persist, stats.persist_max)
        return self.config.alpha * nr + self.config.beta * nf + self.config.gamma * np


def _percentile(values: Iterable[float], q: float) -> float:
    items = sorted(values)
    if not items:
        return 1.0
    idx = int(q * (len(items) - 1))
    return items[idx]


def _normalize(value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return min(1.0, value / scale)
