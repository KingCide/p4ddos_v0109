"""Experiment runner skeleton."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Iterable, Iterator, List, Tuple

from ms_satshield.epoch import EpochManager
from .flow import Packet
from .traffic import TrafficSource


@dataclass(frozen=True)
class ExperimentConfig:
    epoch_ms: int


class ExperimentRunner:
    def __init__(self, detector: EpochManager, config: ExperimentConfig) -> None:
        self.detector = detector
        self.config = config

    def run(self, sources: Iterable[TrafficSource]) -> List[object]:
        events: List[object] = []
        current_epoch_ms = 0.0
        for packet in _merge_sources(sources):
            while packet.ts_ms >= current_epoch_ms + self.config.epoch_ms:
                events.append(self.detector.end_epoch())
                current_epoch_ms += self.config.epoch_ms
            self.detector.on_packet(packet.src, packet.dst, packet.size)
        events.append(self.detector.end_epoch())
        return events


def _merge_sources(sources: Iterable[TrafficSource]) -> Iterator[Packet]:
    heap: List[Tuple[float, int, Packet]] = []
    iterators: List[Iterator[Packet]] = []
    for idx, source in enumerate(sources):
        iterator = iter(source.packets())
        iterators.append(iterator)
        try:
            packet = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (packet.ts_ms, idx, packet))

    while heap:
        _, idx, packet = heapq.heappop(heap)
        yield packet
        iterator = iterators[idx]
        try:
            next_packet = next(iterator)
        except StopIteration:
            continue
        heapq.heappush(heap, (next_packet.ts_ms, idx, next_packet))
