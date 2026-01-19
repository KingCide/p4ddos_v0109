"""Top-k flow detector inspired by SatShield."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from .config import TopKConfig


@dataclass
class FlowRecord:
    key: int
    count: int


@dataclass
class AuxEntry:
    key: int
    r_cnt: int
    v_cnt: int


class TopKFilter:
    """Simplified Top-k filter with auxiliary table.

    This keeps the structure for future P4-aligned logic, while allowing
    a simulator to run end-to-end experiments.
    """

    def __init__(self, config: TopKConfig, seed: int = 0) -> None:
        self.config = config
        self._seed = seed
        self._tables: List[List[Optional[FlowRecord]]] = [
            [None for _ in range(config.buckets_per_stage)]
            for _ in range(config.stages)
        ]
        self._aux: List[Optional[AuxEntry]] = [
            None for _ in range(config.buckets_per_stage)
        ]
        self._min_count = 0

    def update(self, key: int, size: int) -> None:
        record = FlowRecord(key=key, count=size)
        for stage in range(self.config.stages):
            idx = self._hash(key, stage) % self.config.buckets_per_stage
            bucket = self._tables[stage][idx]
            if bucket is None:
                self._tables[stage][idx] = record
                return
            if bucket.key == record.key:
                bucket.count += record.count
                return
            if bucket.count < record.count:
                self._tables[stage][idx], record = record, bucket
        self._aux_update(record)

    def snapshot(self) -> List[FlowRecord]:
        records: List[FlowRecord] = []
        min_count = None
        for stage in range(self.config.stages):
            for bucket in self._tables[stage]:
                if bucket is None:
                    continue
                records.append(bucket)
                if min_count is None or bucket.count < min_count:
                    min_count = bucket.count
        self._min_count = min_count or 0
        return [
            rec for rec in records
            if rec.count >= self.config.heavy_threshold_bytes
        ]

    def reset(self) -> None:
        for stage in range(self.config.stages):
            for idx in range(self.config.buckets_per_stage):
                self._tables[stage][idx] = None
        for idx in range(self.config.buckets_per_stage):
            self._aux[idx] = None
        self._min_count = 0

    def _aux_update(self, record: FlowRecord) -> None:
        idx = self._hash(record.key, self.config.stages) % self.config.buckets_per_stage
        entry = self._aux[idx]
        if entry is None:
            self._aux[idx] = AuxEntry(key=record.key, r_cnt=record.count, v_cnt=record.count)
            return
        if entry.key == record.key:
            entry.r_cnt += record.count
            entry.v_cnt += record.count
        else:
            entry.v_cnt -= record.count
            if entry.v_cnt <= 0:
                entry.key = record.key
                entry.r_cnt = record.count
                entry.v_cnt = record.count

    @staticmethod
    def _hash(key: int, seed: int) -> int:
        return hash((key, seed)) & 0xFFFFFFFF


class FlowDetector:
    """Wraps TopKFilter for epoch-based heavy-key reporting."""

    def __init__(self, config: TopKConfig) -> None:
        self.config = config
        self._filter = TopKFilter(config=config)

    def on_packet(self, key: int, size: int) -> None:
        self._filter.update(key, size)

    def end_epoch(self) -> List[FlowRecord]:
        return self._filter.snapshot()

    def reset(self) -> None:
        self._filter.reset()
